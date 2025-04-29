# /Users/helloppx/PycharmProjects/GameAI/train_model.py
from ultralytics import YOLO
import torch
import logging
import os
import platform
import psutil
import multiprocessing
import gc
import shutil
import datetime
import glob
import re
import subprocess
import math  # 添加math模块支持
import numpy as np  # 添加numpy支持

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 在文件开头添加环境变量设置
import os

os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:256,expandable_segments:True'

# 添加UI特有数据增强配置
UI_AUGMENTATION = {
	'mosaic': 0.5,            # 马赛克增强
	'mixup': 0.1,             # 混合增强
	'copy_paste': 0.1,        # 复制粘贴增强
	'degrees': 0.0,           # UI界面不需要大角度旋转
	'translate': 0.1,         # 轻微平移
	'scale': 0.1,             # 轻微缩放
	'shear': 0.0,             # UI不需要剪切
	'perspective': 0.0,       # UI不需要透视
	'hsv_h': 0.015,           # 色调轻微变化
	'hsv_s': 0.2,             # 饱和度变化
	'hsv_v': 0.2,             # 亮度变化
	'fliplr': 0.01,           # UI界面很少需要翻转
	'flipud': 0.0,            # UI不需要上下翻转
}

# 添加Focal Loss难例挖掘实现
class FocalLoss(torch.nn.Module):
	"""实现Focal Loss以关注难例
	
	Focal Loss用于处理类别不平衡问题，特别关注难以分类的样本。
	公式: FL(pt) = -alpha * (1 - pt)^gamma * log(pt)
	
	Args:
		alpha: 权重因子，用于平衡正负样本
		gamma: 聚焦参数，降低易分类样本的损失权重
		reduction: 损失计算方式 ('mean', 'sum' 或 'none')
	"""
	def __init__(self, alpha=0.25, gamma=2.0, reduction='mean'):
		super(FocalLoss, self).__init__()
		self.alpha = alpha
		self.gamma = gamma
		self.reduction = reduction
		
	def forward(self, inputs, targets):
		"""计算Focal Loss
		
		Args:
			inputs: 模型预测的logits
			targets: 真实标签
			
		Returns:
			计算得到的focal loss
		"""
		# 计算交叉熵损失
		ce_loss = torch.nn.functional.cross_entropy(
			inputs, targets, reduction='none'
		)
		
		# 计算预测概率
		pt = torch.exp(-ce_loss)
		
		# 应用focal loss公式
		focal_loss = self.alpha * (1 - pt) ** self.gamma * ce_loss
		
		# 根据reduction方式返回结果
		if self.reduction == 'mean':
			return focal_loss.mean()
		elif self.reduction == 'sum':
			return focal_loss.sum()
		else:
			return focal_loss

# 添加难例挖掘工具函数
def hard_example_mining(loss_values, keep_ratio=0.7):
	"""保留损失较大的难例样本
	
	Args:
		loss_values: 每个样本的损失值
		keep_ratio: 保留的样本比例
		
	Returns:
		难例样本的掩码
	"""
	# 确定保留的样本数量
	k = int(len(loss_values) * keep_ratio)
	
	# 对损失值进行排序获取索引
	_, indices = torch.sort(loss_values, descending=True)
	
	# 创建掩码，标记保留的难例
	mask = torch.zeros_like(loss_values, dtype=torch.bool)
	mask[indices[:k]] = True
	
	return mask


def clean_model_files(weights_dir, keep_num=3):
	"""
	清理单个权重目录中的模型文件，只保留最新的几个文件
	
	Args:
		weights_dir: 模型权重文件目录
		keep_num: 要保留的最新模型文件数量
		
	Returns:
		删除的文件数量
	"""
	if not os.path.exists(weights_dir):
		logger.warning(f"权重目录不存在: {weights_dir}")
		return 0
	
	# 始终保留best.pt和last.pt
	essential_files = ['best.pt', 'last.pt']
	
	# 获取所有epoch模型文件
	epoch_files = glob.glob(os.path.join(weights_dir, 'epoch*.pt'))
	
	# 如果文件数量少于等于要保留的数量，不需要删除
	if len(epoch_files) <= keep_num:
		logger.info(f"模型文件数量({len(epoch_files)})小于等于保留数量({keep_num})，不需要清理")
		return 0
	
	# 按文件创建时间排序(最新优先)
	epoch_files.sort(key=lambda x: os.path.getctime(x), reverse=True)
	
	# 保留最新的keep_num个文件，删除其余文件
	files_to_delete = epoch_files[keep_num:]
	deleted_count = 0
	
	for file_path in files_to_delete:
		try:
			os.remove(file_path)
			logger.info(f"已删除旧模型文件: {os.path.basename(file_path)}")
			deleted_count += 1
		except Exception as e:
			logger.error(f"删除文件 {file_path} 时出错: {str(e)}")
	
	logger.info(f"清理完成，共删除 {deleted_count} 个旧模型文件")
	return deleted_count


def clean_all_experiment_folders(project_root, keep_latest_exps=3, keep_models_per_exp=3):
	"""
	清理所有实验文件夹，只保留最新的几个实验目录和每个实验中最新的几个模型文件
	
	Args:
		project_root: 项目根目录
		keep_latest_exps: 要保留的最新实验目录数量
		keep_models_per_exp: 每个实验目录中要保留的最新模型文件数量
		
	Returns:
		删除的文件夹数量和文件数量
	"""
	train_dir = os.path.join(project_root, "train_results", "train")
	if not os.path.exists(train_dir):
		logger.warning(f"训练结果目录不存在: {train_dir}")
		return 0, 0
	
	# 获取所有实验目录
	exp_dirs = [
		d for d in os.listdir(train_dir) 
		if os.path.isdir(os.path.join(train_dir, d)) and 
		d.startswith("exp_")
	]
	
	# 如果实验目录数量少于等于要保留的数量，只清理每个目录中的模型文件
	if len(exp_dirs) <= keep_latest_exps:
		logger.info(f"实验目录数量({len(exp_dirs)})小于等于保留数量({keep_latest_exps})，只清理模型文件")
		deleted_files = 0
		for exp_dir in exp_dirs:
			weights_dir = os.path.join(train_dir, exp_dir, "weights")
			if os.path.exists(weights_dir):
				deleted_files += clean_model_files(weights_dir, keep_models_per_exp)
		return 0, deleted_files
	
	# 按创建时间排序实验目录(最新优先)
	exp_dirs.sort(key=lambda x: os.path.getctime(os.path.join(train_dir, x)), reverse=True)
	
	# 处理重复目录 (如 exp_pt2 和 exp_pt22)
	exp_dirs_to_keep = []
	exp_name_pattern = re.compile(r'exp_([^_]+)')
	exp_names_seen = set()
	
	for exp_dir in exp_dirs[:keep_latest_exps]:
		match = exp_name_pattern.match(exp_dir)
		if match:
			base_name = match.group(1)
			if base_name not in exp_names_seen:
				exp_names_seen.add(base_name)
				exp_dirs_to_keep.append(exp_dir)
		else:
			exp_dirs_to_keep.append(exp_dir)
	
	# 确保保留至少keep_latest_exps个目录
	if len(exp_dirs_to_keep) < keep_latest_exps:
		# 添加更多目录直到达到keep_latest_exps
		for exp_dir in exp_dirs:
			if exp_dir not in exp_dirs_to_keep:
				exp_dirs_to_keep.append(exp_dir)
				if len(exp_dirs_to_keep) >= keep_latest_exps:
					break
	
	# 清理要保留的目录中的模型文件
	deleted_files = 0
	for exp_dir in exp_dirs_to_keep:
		weights_dir = os.path.join(train_dir, exp_dir, "weights")
		if os.path.exists(weights_dir):
			deleted_files += clean_model_files(weights_dir, keep_models_per_exp)
	
	# 删除其余实验目录
	dirs_to_delete = [d for d in exp_dirs if d not in exp_dirs_to_keep]
	deleted_dirs = 0
	
	for exp_dir in dirs_to_delete:
		try:
			exp_path = os.path.join(train_dir, exp_dir)
			shutil.rmtree(exp_path)
			logger.info(f"已删除旧实验目录: {exp_dir}")
			deleted_dirs += 1
		except Exception as e:
			logger.error(f"删除目录 {exp_dir} 时出错: {str(e)}")
	
	logger.info(f"清理完成，共删除 {deleted_dirs} 个旧实验目录和 {deleted_files} 个模型文件")
	return deleted_dirs, deleted_files


def cleanup_git_repository():
	"""
	清理Git仓库中的大文件，以减少仓库大小
	
	Returns:
		清理是否成功
	"""
	try:
		# 确保LFS已初始化
		subprocess.run(["git", "lfs", "install"], check=True)
		
		# 查找大于100MB的文件列表
		logger.info("查找仓库中的大文件...")
		large_files_cmd = "git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | awk '/^blob/ {if ($3 > 104857600) print $0}' | sort -k3nr | head -n 10"
		
		if platform.system() == "Windows":
			large_files_result = subprocess.run(["powershell", "-Command", large_files_cmd], capture_output=True, text=True)
		else:
			large_files_result = subprocess.run(large_files_cmd, shell=True, capture_output=True, text=True)
		
		large_files = large_files_result.stdout.strip()
		if large_files:
			logger.info(f"发现大文件:\n{large_files}")
			logger.info("请确保所有.pt文件已由Git LFS跟踪")
		
		logger.info("清理完成")
		return True
	except Exception as e:
		logger.error(f"清理Git仓库时出错: {str(e)}")
		return False


def main():
	# CUDA验证
	if not torch.cuda.is_available():
		raise RuntimeError("""
        CUDA不可用! 请按以下步骤操作:
        1. 确保已安装NVIDIA驱动
        2. 卸载当前PyTorch: pip uninstall torch torchvision torchaudio
        3. 安装CUDA版PyTorch: pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
        4. 在NVIDIA控制面板中将Python设置为使用独立显卡
        """)
	
	# 获取当前目录作为项目根目录
	PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
	
	# 在训练开始前清理旧的实验目录，只保留最新的3个实验目录和每个实验中最新的3个模型文件
	logger.info("开始清理旧的实验目录和模型文件...")
	clean_all_experiment_folders(PROJECT_ROOT, keep_latest_exps=3, keep_models_per_exp=3)
	
	# 启用CUDA优化
	if torch.cuda.is_available():
		# 启用TensorFloat-32
		torch.backends.cuda.matmul.allow_tf32 = True
		torch.backends.cudnn.allow_tf32 = True
		# 启用cuDNN自动调优
		torch.backends.cudnn.benchmark = True
	
	# 检查系统和设备
	logger.info(f"操作系统: {platform.system()}")
	logger.info(f"PyTorch版本: {torch.__version__}")
	logger.info(f"CUDA是否可用: {torch.cuda.is_available()}")
	if torch.cuda.is_available():
		logger.info(f"使用GPU: {torch.cuda.get_device_name(0)}")
		logger.info(f"显存总量: {torch.cuda.get_device_properties(0).total_memory / 1024 ** 3:.1f} GB")
	
	# 获取系统内存信息
	system_ram = psutil.virtual_memory().total / (1024 ** 3)  # GB
	logger.info(f"系统内存: {system_ram:.2f} GB")
	
	# 强制使用CUDA设备
	device = "cuda:0" if torch.cuda.is_available() else "cpu"
	logger.info(f"使用设备: {device}")
	
	# 计算最佳batch_size和workers数量
	if torch.cuda.is_available():
		gpu_name = torch.cuda.get_device_name(0).lower()
		gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3  # 转换为GB
		
		# 为RTX 4090特别优化
		if "4090" in gpu_name:
			batch_size = 24  # 使用中间值，既利用GPU又避免OOM
			num_workers = min(16, os.cpu_count() or 1)  # 工作线程数
			# accumulate不是有效参数，使用nbs实现类似效果
			nominal_batch_size = 64  # 标称批量大小，用于计算学习率
			val_batch_size = 2  # 验证阶段使用更小的batch size
			logger.info("检测到RTX 4090，使用优化配置")
			logger.info(f"使用batch size: {batch_size}，标称batch size: {nominal_batch_size}")
			# 启用CUDA优化
			torch.backends.cudnn.benchmark = True
			torch.backends.cuda.matmul.allow_tf32 = True
			torch.backends.cudnn.enabled = True
			# 清理GPU缓存
			torch.cuda.empty_cache()
			gc.collect()
			# 限制torch缓存分配
			torch.cuda.memory._set_allocator_settings('max_split_size_mb:128')
			
			# 添加定期清理显存的函数
			def clean_gpu_cache(epoch):
				if epoch % 2 == 0:  # 每2个epoch清理一次
					torch.cuda.empty_cache()
					gc.collect()
		else:
			# 其他GPU的默认配置
			batch_size = 4
			val_batch_size = 2
			num_workers = min(4, os.cpu_count() or 1)
	
	logger.info(f"Batch size: {batch_size}")
	logger.info(f"Number of workers: {num_workers}")
	
	# 加载模型
	logger.info("开始加载模型")
	model_path = os.path.join(PROJECT_ROOT, "models", "yolo11m.pt")
	datasets_model_path = os.path.join(PROJECT_ROOT, "datasets", "models", "yolo11m.pt")

	# 首先检查主目录，然后检查datasets/models目录
	if os.path.exists(model_path):
		logger.info(f"使用主目录模型文件: {model_path}")
		model = YOLO(model_path).to(device)
	elif os.path.exists(datasets_model_path):
		logger.info(f"使用datasets/models目录模型文件: {datasets_model_path}")
		model = YOLO(datasets_model_path).to(device)
	else:
		logger.warning(f"本地模型文件不存在: {model_path}，将从官方下载")
		model = YOLO("yolov8m.pt").to(device)
	logger.info("模型加载完成")
	
	# 数据集路径
	data_yaml = os.path.join(PROJECT_ROOT, "datasets", "yolov11-card2", "data.yaml")
	if not os.path.exists(data_yaml):
		raise FileNotFoundError(f"数据集配置文件不存在: {data_yaml}")
	
	# 开始训练
	logger.info("开始训练")
	try:
		# 在训练前主动清理一次GPU缓存
		torch.cuda.empty_cache()
		gc.collect()
		
		# 使用日期时间格式化实验名称，防止exp_pt2这样的命名方式导致重复目录
		current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
		exp_name = f"exp_{current_time}"
		logger.info(f"实验名称: {exp_name}")
		
		model.train(
			data=data_yaml,  # 数据集配置文件
			epochs=100,  # 训练轮次
			batch=batch_size,  # 设置的批次大小
			workers=num_workers,  # 工作线程数
			device=device,  # 设备
			imgsz=640,  # 图像大小
			patience=20,  # 早停耐心
			amp=True,  # 使用自动混合精度
			save_period=10,  # 每10个epoch保存一次（减少保存频率，降低磁盘占用）
			project=os.path.join(PROJECT_ROOT, "train_results", "train"),  # 保存训练结果的目录
			name=exp_name,  # 实验名称，使用日期时间格式
			exist_ok=False,  # 如果目录存在则覆盖
			cache="ram" if system_ram > 24 else "disk",  # 系统内存充足时使用RAM缓存，否则磁盘缓存
			val=True,  # 启用验证
			conf=0.001,  # 验证时的置信度阈值
			iou=0.6,  # 验证时的IoU阈值
			half=True,  # 使用半精度训练
			plots=True,  # 绘制训练图表
			rect=False,  # 不使用矩形训练
			multi_scale=False,  # 关闭多尺度训练
			close_mosaic=10,  # 最后10个epoch关闭mosaic增强
			# 内存优化设置
			overlap_mask=True,  # 启用mask重叠
			single_cls=False,  # 不使用单类别训练
			optimizer="AdamW",  # 使用AdamW优化器
			lr0=0.001,  # 初始学习率
			lrf=0.01,  # 最终学习率比例
			momentum=0.937,  # 动量
			weight_decay=0.0005,  # 权重衰减
			warmup_epochs=3.0,  # 预热轮次
			warmup_momentum=0.8,  # 预热动量
			warmup_bias_lr=0.1,  # 预热偏置学习率
			box=7.5,  # 边界框损失权重
			cls=0.5,  # 分类损失权重
			dfl=1.5,  # DFL损失权重
			nbs=nominal_batch_size if "4090" in gpu_name else 64,  # 标称batch size
			# 新增选项:
			augment=True,  # 使用增强
			verbose=False,  # 减少日志输出
			deterministic=False  # 关闭确定性模式以提高性能
		)
		logger.info("训练完成")
		
		# 清理权重文件，只保留最新的和最重要的
		weights_dir = os.path.join(PROJECT_ROOT, "train_results", "train", exp_name, "weights")
		cleanup_model_files(weights_dir, save_period)
		
		# 验证模型性能
		logger.info("开始验证模型")
		# 使用与训练相同的实验名称进行验证
		val_results = model.val(name=exp_name)
		logger.info("验证完成")
		
		# 清理权重文件，只保留最新的3个
		weights_dir = os.path.join(PROJECT_ROOT, "train_results", "train", exp_name, "weights")
		if os.path.exists(weights_dir):
			logger.info("开始清理权重文件，只保留最新的3个")
			clean_model_files(weights_dir, keep_num=3)
		
		# 导出最佳模型
		logger.info("导出最佳模型")
		output_path = os.path.join(PROJECT_ROOT, "outputs", "weights", f"best_{current_time}.pt")
		os.makedirs(os.path.dirname(output_path), exist_ok=True)
		
		# 直接从训练目录获取最佳模型路径
		train_dir = os.path.join(PROJECT_ROOT, "train_results", "train")
		best_model_path = os.path.join(train_dir, exp_name, "weights", "best.pt")
		
		if os.path.exists(best_model_path):
			shutil.copy(best_model_path, output_path)
			logger.info(f"模型已保存到: {output_path}")
		else:
			# 如果确切路径不存在，尝试查找可能的模型文件
			logger.warning(f"未找到预期路径的模型: {best_model_path}")
			
			# 列出train目录下的所有实验文件夹
			possible_exp_dirs = []
			if os.path.exists(train_dir):
				possible_exp_dirs = [
					d for d in os.listdir(train_dir) 
					if os.path.isdir(os.path.join(train_dir, d)) and 
					d.startswith("exp_")
				]
			
			if possible_exp_dirs:
				# 按创建时间排序，最新的优先
				latest_exp_dir = max(
					possible_exp_dirs,
					key=lambda x: os.path.getmtime(os.path.join(train_dir, x))
				)
				logger.info(f"尝试使用最新的实验目录: {latest_exp_dir}")
				
				# 尝试查找最佳模型
				latest_best_model = os.path.join(train_dir, latest_exp_dir, "weights", "best.pt")
				if os.path.exists(latest_best_model):
					shutil.copy(latest_best_model, output_path)
					logger.info(f"找到并保存了最佳模型到: {output_path}")
				else:
					# 尝试last.pt模型
					latest_last_model = os.path.join(train_dir, latest_exp_dir, "weights", "last.pt")
					if os.path.exists(latest_last_model):
						shutil.copy(latest_last_model, output_path)
						logger.info(f"找到并保存了最新模型到: {output_path}")
					else:
						logger.error(f"在实验目录 {latest_exp_dir} 中未找到任何模型文件")
			else:
				logger.error("没有找到任何训练结果目录")
		
		# 训练结束后再次清理所有实验目录
		logger.info("训练结束，开始最终清理所有实验目录...")
		clean_all_experiment_folders(PROJECT_ROOT, keep_latest_exps=3, keep_models_per_exp=3)
	
	# 如果需要其他格式，可以使用有效的格式如下
	# 可选：导出为其他格式
	# model.export(format="onnx", save_dir=os.path.dirname(output_path))
	
	except Exception as e:
		logger.error(f"训练过程中出现错误: {str(e)}", exc_info=True)
		raise


if __name__ == '__main__':
	# Windows系统需要这个
	multiprocessing.freeze_support()
	
	# 获取当前目录作为项目根目录
	PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
	
	# 解析命令行参数
	import argparse
	parser = argparse.ArgumentParser(description='YOLO模型训练与清理工具')
	parser.add_argument('--clean-only', action='store_true', help='只执行清理操作，不进行训练')
	parser.add_argument('--clean-git', action='store_true', help='清理Git仓库中的大文件')
	args = parser.parse_args()
	
	if args.clean_only:
		# 只执行清理操作
		logger.info("开始清理操作...")
		clean_all_experiment_folders(PROJECT_ROOT, keep_latest_exps=3, keep_models_per_exp=3)
		logger.info("清理操作完成")
	elif args.clean_git:
		# 清理Git仓库
		logger.info("开始清理Git仓库...")
		cleanup_git_repository()
		logger.info("Git仓库清理完成")
	else:
		# 执行正常训练流程
		main()

# 为不同UI元素定义自适应阈值配置
UI_ADAPTIVE_THRESHOLDS = {
	# 按钮元素
	'button': {
		'base_conf': 0.25,          # 基础置信度阈值
		'min_conf': 0.20,           # 最小置信度阈值
		'adaptive_factor': 0.05,    # 自适应调整因子
	},
	# 文本元素
	'text': {
		'base_conf': 0.30,
		'min_conf': 0.25, 
		'adaptive_factor': 0.03,
	},
	# 图标元素
	'icon': {
		'base_conf': 0.35,
		'min_conf': 0.30,
		'adaptive_factor': 0.04,
	},
	# 菜单元素
	'menu': {
		'base_conf': 0.40,
		'min_conf': 0.30,
		'adaptive_factor': 0.05,
	},
	# 对话框元素
	'dialog': {
		'base_conf': 0.45,
		'min_conf': 0.35,
		'adaptive_factor': 0.05,
	},
	# 默认值(用于未指定的元素类型)
	'default': {
		'base_conf': 0.30,
		'min_conf': 0.25,
		'adaptive_factor': 0.04,
	}
}

def get_adaptive_threshold(element_type, image_quality=1.0):
	"""
	根据UI元素类型和图像质量获取自适应阈值
	
	Args:
		element_type: UI元素类型 ('button', 'text', 'icon', 'menu', 'dialog')
		image_quality: 图像质量因子(0.0-1.0)，值越小表示图像质量越差
		
	Returns:
		适合该元素类型的检测阈值
	"""
	# 如果元素类型不在配置中，使用默认值
	if element_type not in UI_ADAPTIVE_THRESHOLDS:
		element_type = 'default'
	
	# 获取该元素类型的阈值配置    
	threshold_config = UI_ADAPTIVE_THRESHOLDS[element_type]
	
	# 根据图像质量调整阈值
	quality_factor = max(0.0, min(1.0, image_quality))  # 确保在0-1范围内
	quality_adjustment = threshold_config['adaptive_factor'] * (1.0 - quality_factor)
	
	# 计算最终阈值 (质量越低，阈值越低)
	final_threshold = threshold_config['base_conf'] - quality_adjustment
	
	# 确保不低于最小阈值
	final_threshold = max(final_threshold, threshold_config['min_conf'])
	
	return final_threshold
