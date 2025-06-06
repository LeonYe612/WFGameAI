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
import cv2  # 添加cv2支持
import h5py  # 添加h5py支持
import argparse  # 添加argparse支持
from utils import update_best_model  # 导入update_best_model函数

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 在文件开头添加环境变量设置
import os

# 优化CUDA内存分配，防止内存碎片并启用expandable_segments
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'

# 异步CUDA操作，减少同步开销
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'

# 开启新的cuDNN API，可能提高性能
os.environ['TORCH_CUDNN_V8_API_ENABLED'] = '1'

# 设置多进程启动方法为spawn，避免Windows上的fork问题
# 这是为了解决Windows上使用多进程数据加载器时出现的内存错误
os.environ['PYTHONWARNINGS'] = 'ignore:semaphore_tracker:UserWarning'

# 添加UI特有数据增强配置 - 优化UI元素识别的增强参数
UI_AUGMENTATION = {
	'mosaic': 0.3,            # 降低马赛克增强概率
	'mixup': 0.0,             # 禁用混合增强以节省内存
	'copy_paste': 0.0,        # 禁用复制粘贴增强以节省内存
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
    # 新增增强参数，针对UI界面特点
    'blur': 0.01,             # 轻微模糊，模拟低质量截图
    'contrast': 0.1,          # 对比度调整
    'brightness': 0.1,        # 亮度调整
    'noise': 0.05,            # 添加噪点，提高模型鲁棒性
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

	# 使用新的基于日期时间的目录处理逻辑
	# 按创建时间排序，直接保留最新的keep_latest_exps个目录
	# 按创建时间排序实验目录(最新优先)
	exp_dirs.sort(key=lambda x: os.path.getctime(os.path.join(train_dir, x)), reverse=True)
	exp_dirs_to_keep = exp_dirs[:keep_latest_exps]

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



# 新增数据集质量评估函数
def evaluate_dataset_quality(data_yaml_path):
    """
    评估数据集质量，检查分布平衡性和标注质量

    Args:
        data_yaml_path: 数据集配置文件路径

    Returns:
        质量评估结果
    """
    import yaml
    try:
        with open(data_yaml_path, 'r') as f:
            data_config = yaml.safe_load(f)

        # 检查训练集和验证集路径
        train_path = data_config.get('train', '')
        val_path = data_config.get('val', '')

        # 检查类别分布
        from collections import Counter
        import glob
        from pathlib import Path

        # 获取标签文件
        train_labels = glob.glob(str(Path(train_path).parent / 'labels' / '*.txt'))

        # 统计各类别数量
        class_counts = Counter()
        total_objects = 0

        for label_file in train_labels:
            try:
                with open(label_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            class_id = int(parts[0])
                            class_counts[class_id] += 1
                            total_objects += 1
            except Exception as e:
                logger.warning(f"读取标签文件 {label_file} 时出错: {str(e)}")

        # 输出类别分布情况
        logger.info(f"数据集包含 {len(train_labels)} 张训练图像，{total_objects} 个标注对象")

        if total_objects > 0:
            # 计算类别不平衡程度
            max_count = max(class_counts.values()) if class_counts else 0
            min_count = min(class_counts.values()) if class_counts else 0

            if max_count > 0 and min_count > 0:
                imbalance_ratio = max_count / min_count
                logger.info(f"类别不平衡比例: {imbalance_ratio:.2f}:1")

                if imbalance_ratio > 10:
                    logger.warning("类别严重不平衡，建议增加数据增强或平衡采样")
                    return False, "类别严重不平衡"

            # 输出类别详情
            classes = data_config.get('names', {})
            for class_id, count in sorted(class_counts.items()):
                class_name = classes.get(class_id, f"类别 {class_id}")
                percentage = 100 * count / total_objects
                logger.info(f"  - {class_name}: {count} 个对象 ({percentage:.1f}%)")

                # 检查数量太少的类别
                if count < 50:
                    logger.warning(f"  类别 '{class_name}' 样本数量过少，可能影响识别性能")

        return True, "数据集质量检查通过"

    except Exception as e:
        logger.error(f"评估数据集质量时出错: {str(e)}")
        return False, f"评估失败: {str(e)}"


# 新增周期性学习率调整回调函数
def cosine_annealing_callback(epoch, max_epochs, base_lr=0.01, min_lr=0.001):
    """
    余弦退火学习率调整

    Args:
        epoch: 当前轮次
        max_epochs: 最大轮次
        base_lr: 基础学习率
        min_lr: 最小学习率

    Returns:
        当前轮次的学习率
    """
    return min_lr + 0.5 * (base_lr - min_lr) * (1 + math.cos(math.pi * epoch / max_epochs))


def add_memory_monitoring(model_train_args):
    """
    此函数已废弃，改为使用callbacks实现内存监控
    保留此函数是为了确保向后兼容

    Args:
        model_train_args: 模型训练参数

    Returns:
        原始训练参数
    """
    logger.warning("add_memory_monitoring已废弃，使用callbacks代替")
    return model_train_args


# 更新RTX 4090优化函数，确保只使用有效的优化方法
def optimize_for_rtx4090():
    """
    对RTX 4090进行专门的优化设置，防止OOM错误

    Returns:
        bool: 是否成功应用优化
    """
    logger.info("应用RTX 4090优化设置")

    # 清理当前GPU缓存
    torch.cuda.empty_cache()
    gc.collect()

    # 限制内存使用
    try:
        torch.cuda.set_per_process_memory_fraction(0.85)  # 使用85%显存
        logger.info("已限制GPU内存使用为85%")
    except:
        logger.warning("无法设置内存使用限制")

    # 启用TensorFloat-32
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    logger.info("已启用TensorFloat-32")

    # 添加显存优化选项
    torch.backends.cudnn.benchmark = True  # 寻找最优卷积算法
    logger.info("已启用cuDNN benchmark模式")

    # 启用pytorch的内置分析器减少内存碎片
    try:
        # 仅在PyTorch 2.0+版本中可用
        if hasattr(torch, 'profiler') and hasattr(torch.profiler, 'profile'):
            torch._C._jit_set_profiling_mode(False)
            torch._C._jit_set_profiling_executor(False)
            logger.info("已禁用JIT分析器")
    except:
        pass

    # 使用更激进的垃圾回收
    gc.set_threshold(100, 5, 5)
    logger.info("已调整垃圾回收阈值")

    # 返回成功
    return True


# 添加新的数据集预处理函数
def preprocess_dataset(data_yaml_path, output_dir=None, image_size=640, cache_type='disk'):
    """
    预处理数据集，将图像转换为HDF5格式以加速训练

    Args:
        data_yaml_path: 数据集配置文件路径
        output_dir: 输出目录，默认为数据集同级目录下的preprocessed子目录
        image_size: 预处理后的图像尺寸
        cache_type: 缓存类型，可选'disk'或'hdf5'

    Returns:
        预处理完成的数据路径
    """
    import yaml
    import time
    from pathlib import Path

    logger.info(f"开始预处理数据集: {data_yaml_path}")
    start_time = time.time()

    try:
        # 读取数据集配置
        with open(data_yaml_path, 'r') as f:
            data_config = yaml.safe_load(f)

        # 确定输出目录
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(data_yaml_path), "preprocessed")

        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"预处理数据将保存到: {output_dir}")

        # 获取训练集和验证集路径
        train_path = data_config.get('train', '')
        val_path = data_config.get('val', '')

        if cache_type == 'disk':
            # 使用YOLO内置的disk缓存机制
            # 创建临时模型实例并加载数据集进行缓存
            logger.info("使用YOLO disk缓存模式进行预处理...")
            model = YOLO('yolo11n.pt')  # 使用小模型加速处理

            # 模拟训练加载过程，让YOLO生成缓存
            try:
                # 只运行1个epoch但开启缓存，会生成缓存文件
                model.train(
                    data=data_yaml_path,
                    epochs=1,
                    imgsz=image_size,
                    cache='disk',  # 强制使用disk缓存
                    device='0' if torch.cuda.is_available() else 'cpu',
                    close_mosaic=0,  # 禁用mosaic增强以减少内存使用
                    batch=4,  # 小batch_size减少内存压力
                    exist_ok=True,  # 允许覆盖已有目录
                    project=output_dir,
                    name='cache_gen',  # 使用特殊名称标记为缓存生成
                    verbose=False,  # 减少输出
                    val=False,  # 不进行验证
                    save=False,  # 不保存模型
                    plots=False  # 不生成图表
                )
                # 中断训练
                logger.info("已生成数据集缓存")
            except Exception as e:
                logger.warning(f"缓存生成过程中断，但缓存可能已经创建: {str(e)}")

            # 返回原始数据集路径，因为缓存已在原路径关联
            preprocessed_data_path = data_yaml_path

        elif cache_type == 'hdf5':
            # 自定义HDF5格式处理
            logger.info("使用HDF5格式进行数据集预处理...")

            # 创建HDF5文件
            train_h5_path = os.path.join(output_dir, "train_dataset.h5")
            val_h5_path = os.path.join(output_dir, "val_dataset.h5")

            # 处理训练集
            if train_path:
                logger.info(f"处理训练集: {train_path}")
                process_images_to_hdf5(train_path, train_h5_path, image_size)

            # 处理验证集
            if val_path:
                logger.info(f"处理验证集: {val_path}")
                process_images_to_hdf5(val_path, val_h5_path, image_size)

            # 创建新的yaml配置文件
            new_data_config = data_config.copy()
            new_data_config['train'] = train_h5_path if train_path else ''
            new_data_config['val'] = val_h5_path if val_path else ''
            new_data_config['hdf5'] = True  # 标记为HDF5格式

            # 保存新的配置文件
            new_yaml_path = os.path.join(output_dir, "data.yaml")
            with open(new_yaml_path, 'w') as f:
                yaml.dump(new_data_config, f)

            preprocessed_data_path = new_yaml_path

        elapsed_time = time.time() - start_time
        logger.info(f"数据集预处理完成，耗时: {elapsed_time:.2f}秒")
        return preprocessed_data_path

    except Exception as e:
        logger.error(f"数据集预处理失败: {str(e)}", exc_info=True)
        return data_yaml_path  # 失败时返回原始路径

def process_images_to_hdf5(image_dir, output_h5_path, image_size):
    """
    将图像处理并保存为HDF5格式

    Args:
        image_dir: 图像目录
        output_h5_path: 输出HDF5文件路径
        image_size: 图像尺寸
    """
    import glob
    from tqdm import tqdm
    from pathlib import Path

    # 获取所有图像文件
    image_files = glob.glob(os.path.join(image_dir, "**", "*.jpg"), recursive=True)
    image_files.extend(glob.glob(os.path.join(image_dir, "**", "*.jpeg"), recursive=True))
    image_files.extend(glob.glob(os.path.join(image_dir, "**", "*.png"), recursive=True))

    logger.info(f"找到 {len(image_files)} 张图像")

    # 创建HDF5文件
    with h5py.File(output_h5_path, 'w') as h5f:
        # 创建数据集
        images_dataset = h5f.create_dataset(
            'images',
            shape=(len(image_files), image_size, image_size, 3),
            dtype=np.uint8,
            chunks=True,  # 启用分块存储以支持随机访问
            compression="gzip",  # 使用gzip压缩
            compression_opts=4  # 压缩级别(1-9)，平衡速度和大小
        )

        # 创建路径数据集
        paths_dataset = h5f.create_dataset(
            'paths',
            shape=(len(image_files),),
            dtype=h5py.special_dtype(vlen=str)
        )

        # 处理图像
        for i, image_path in enumerate(tqdm(image_files, desc="处理图像")):
            try:
                # 读取图像
                img = cv2.imread(image_path)
                if img is None:
                    logger.warning(f"无法读取图像: {image_path}")
                    continue

                # 转换为RGB
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                # 调整大小
                img_resized = cv2.resize(img, (image_size, image_size))

                # 保存到HDF5
                images_dataset[i] = img_resized
                paths_dataset[i] = image_path

            except Exception as e:
                logger.warning(f"处理图像 {image_path} 时出错: {str(e)}")

    logger.info(f"HDF5文件已保存: {output_h5_path}")

def main():
	# 检查环境
	import sys
	import subprocess

	# 确保在Windows上使用正确的多进程启动方法
	if platform.system() == 'Windows':
		# 在Windows上显式设置多进程启动方法为'spawn'而非默认的'fork'
		# 这可以解决多进程数据加载时的内存错误问题
		multiprocessing.set_start_method('spawn', force=True)
		logger.info("已设置Windows多进程启动方法为'spawn'")

	# 检查Python版本
	python_version = sys.version.split()[0]
	logger.info(f"当前Python版本: {python_version}")

	# 检查是否在conda环境中
	try:
		# 尝试获取当前conda环境名称
		result = subprocess.run(
			"conda info --envs",
			shell=True,
			capture_output=True,
			text=True
		)
		conda_output = result.stdout

		# 检查当前活动的环境
		active_env = None
		for line in conda_output.split('\n'):
			if '*' in line:  # 活动环境会有星号标记
				parts = line.split()
				active_env = parts[-1]  # 获取环境路径或名称
				# 如果是路径，提取环境名称
				if os.path.sep in active_env:
					active_env = os.path.basename(active_env)
				break

		logger.info(f"当前Conda环境: {active_env}")

		# 检查是否为所需环境
		if active_env != "py39_yolov10":
			logger.warning(f"""
			警告: 当前不在推荐的conda环境中运行!
			当前环境: {active_env}
			推荐环境: py39_yolov10

			请按以下步骤操作:
			1. 终止当前程序
			2. 在命令行中运行: conda activate py39_yolov10
			3. 然后重新运行: python train_model.py

			不在正确环境中运行可能导致CUDA和依赖库问题!
			""")
			# 等待用户确认是否继续
			response = input("是否仍要继续? (y/n): ")
			if response.lower() != 'y':
				logger.info("用户选择终止程序。请在正确的环境中重新运行。")
				sys.exit(0)
			else:
				logger.warning("用户选择在非推荐环境中继续运行，可能会出现兼容性问题。")
	except Exception as e:
		logger.warning(f"无法确定Conda环境: {e}")
		logger.warning("请确保在py39_yolov10环境中运行以避免兼容性问题。")

	# CUDA验证
	if not torch.cuda.is_available():
		raise RuntimeError("""
        CUDA不可用! 请按以下步骤操作:
        1. 确保已安装NVIDIA驱动
        2. 确保在正确的conda环境中运行: conda activate py39_yolov10
        3. 如果问题仍然存在，尝试重新安装PyTorch CUDA版本:
           pip uninstall torch torchvision torchaudio
           pip install torch==2.5.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
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

		# RTX 4090特别优化参数
		if "4090" in gpu_name:
			# 批处理大小设置
			batch_size = 16  # 降低到8以避免内存不足
			                  # 较大的batch size可以提高GPU利用率和训练速度，但过大会导致OOM错误

			# 数据加载优化
			num_workers = min(12, os.cpu_count() or 1)  # 减少到6个工作线程以降低内存压力
			                                            # 线程过多会导致CPU瓶颈和线程调度开销

			# 梯度累积模拟
			nominal_batch_size = 32  # 降低标称批量大小，用于学习率计算
			                         # 允许模拟更大批量训练效果而不增加显存占用

			# 验证阶段优化
			val_batch_size = 1  # 验证阶段使用更小的batch size以减少显存使用
			                    # 验证不需要计算梯度，可以分批进行以节省显存

			logger.info("检测到RTX 4090，使用优化配置")
			logger.info(f"使用batch size: {batch_size}，标称batch size: {nominal_batch_size}")

			# 应用RTX 4090专用优化
			optimize_for_rtx4090()
		else:
			# 其他GPU型号的保守默认配置
			batch_size = 4   # 保守值，适用于多种GPU型号
			val_batch_size = 2
			num_workers = min(2, os.cpu_count() or 1)  # 非常保守的工作线程数

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
		model = YOLO("yolo11m.pt").to(device)
	logger.info("模型加载完成")

	# 数据集路径
	# data_yaml = os.path.join(PROJECT_ROOT, "datasets", "yolov11-card2", "data.yaml")
	data_yaml = os.path.join(PROJECT_ROOT, "datasets", "My First Project.v7i.yolov11", "data.yaml")

	if not os.path.exists(data_yaml):
		raise FileNotFoundError(f"数据集配置文件不存在: {data_yaml}")

	# 数据预处理(如果开启)
	if args.preprocess:
		logger.info("开始预处理数据集...")
		preprocessed_data_path = preprocess_dataset(
			data_yaml,
			output_dir=os.path.join(PROJECT_ROOT, "datasets", "preprocessed"),
			image_size=640,
			cache_type=args.cache_type
		)
		# 使用预处理后的数据路径
		data_yaml = preprocessed_data_path
		logger.info(f"将使用预处理后的数据集: {data_yaml}")

    # 评估数据集质量
	logger.info("开始评估数据集质量...")
	dataset_quality_passed, quality_message = evaluate_dataset_quality(data_yaml)
	logger.info(f"数据集质量评估结果: {quality_message}")

	# 开始训练
	logger.info("开始训练")
	try:
		# 在训练前主动清理一次GPU缓存
		torch.cuda.empty_cache()
		gc.collect()

		# 设置在训练前限制显存使用
		if torch.cuda.is_available():
			try:
				torch.cuda.set_per_process_memory_fraction(0.8)  # 限制使用80%显存
				logger.info("已限制GPU内存使用为80%")
			except:
				logger.warning("无法设置内存使用限制")

		# 使用日期时间格式化实验名称，防止exp_pt2这样的命名方式导致重复目录
		# 格式为: exp_YYYYMMDD_HHMMSS，例如: exp_20230415_143022
		# 使用此命名方式的优点:
		# 1. 确保每次训练的实验目录名称唯一，不会发生覆盖
		# 2. 按照创建时间自然排序，便于管理和查找
		# 3. 通过时间戳可以快速识别实验的创建时间
		# 4. 结合clean_all_experiment_folders函数，可以自动清理旧实验，只保留最新的几个
		current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
		exp_name = f"exp_{current_time}"
		logger.info(f"实验名称: {exp_name}")

		# 训练参数优化
		train_args = {
			'data': data_yaml,
			'epochs': 100,
			'batch': batch_size,
			'workers': num_workers,
			'device': device,
			'imgsz': 640,
			'patience': 30,
			'amp': True,
			'save_period': 10,
			'project': os.path.join(PROJECT_ROOT, "train_results", "train"),
			'name': exp_name,
			'exist_ok': False,
			'cache': "disk",  # 强制使用磁盘缓存而非RAM缓存，以便在多次训练间保留缓存
			'val': True,  # 启用验证以监控训练进度
			'conf': 0.001,
			'iou': 0.6,
			'half': True,
			'plots': True,
			'rect': False,
			'multi_scale': False,  # 禁用多尺度训练以减少内存波动
			'close_mosaic': 10,
			'overlap_mask': True,
			'single_cls': False,
			'optimizer': "AdamW",
			'lr0': 0.001,
			'lrf': 0.01,
			'momentum': 0.937,
			'weight_decay': 0.0005,
			'warmup_epochs': 3.0,  # 缩短预热时间
			'warmup_momentum': 0.8,
			'warmup_bias_lr': 0.1,
			'box': 7.5,
			'cls': 0.5,
			'dfl': 1.5,
			'nbs': nominal_batch_size if "4090" in gpu_name else 64,
			'augment': True,
			'verbose': True,
			'deterministic': False,
			'mosaic': UI_AUGMENTATION['mosaic'],
			'mixup': UI_AUGMENTATION['mixup'],
			'copy_paste': UI_AUGMENTATION['copy_paste'],
			'degrees': UI_AUGMENTATION['degrees'],
			'translate': UI_AUGMENTATION['translate'],
			'scale': UI_AUGMENTATION['scale'],
			'shear': UI_AUGMENTATION['shear'],
			'perspective': UI_AUGMENTATION['perspective'],
			'fliplr': UI_AUGMENTATION['fliplr'],
			'flipud': UI_AUGMENTATION['flipud'],
			'hsv_h': UI_AUGMENTATION['hsv_h'],
			'hsv_s': UI_AUGMENTATION['hsv_s'],
			'hsv_v': UI_AUGMENTATION['hsv_v'],
			'cos_lr': True,
			'freeze': [0, 1, 2, 3],  # 冻结更多骨干网络层，减少内存使用并加快收敛
		}

		# 定义手动内存清理函数
		def manual_memory_cleanup():
			"""在训练循环外部手动清理内存"""
			torch.cuda.empty_cache()
			gc.collect()

			# 尝试释放更多内存
			if torch.cuda.is_available():
				# 强制释放所有未使用的缓存
				if hasattr(torch.cuda, 'memory_summary'):
					logger.info(f"GPU内存使用情况:\n{torch.cuda.memory_summary()}")
				if "4090" in gpu_name and torch.cuda.memory_allocated() > 8 * 1024 * 1024 * 1024:  # 超过8GB释放更多
					# 强制执行cuda同步
					torch.cuda.synchronize()
					gc.collect()
					torch.cuda.empty_cache()
					logger.info("执行强制内存释放")

		# 训练前先清理内存
		manual_memory_cleanup()

		# 使用callbacks参数代替batch_callback
		class MemoryCleanupCallback:
			"""训练过程中定期清理内存的回调函数"""
			def __init__(self):
				self.batch_counter = 0
				self.max_allocated = 0
				self.last_cleanup = 0

			def on_train_batch_end(self, trainer):
				self.batch_counter += 1

				# 获取当前内存使用情况
				current_allocated = torch.cuda.memory_allocated()
				self.max_allocated = max(self.max_allocated, current_allocated)

				# 如果内存使用率高于90%或者每15个批次清理一次
				if (current_allocated > 0.9 * torch.cuda.get_device_properties(0).total_memory) or \
				   (self.batch_counter - self.last_cleanup >= 15):
					torch.cuda.empty_cache()
					self.last_cleanup = self.batch_counter

					# 如果内存使用率极高，执行更彻底的清理
					if current_allocated > 0.95 * torch.cuda.get_device_properties(0).total_memory:
						torch.cuda.synchronize()
						gc.collect()
						logger.warning(f"内存使用极高: {current_allocated / (1024**3):.2f} GB，执行彻底清理")

			def on_train_epoch_end(self, trainer):
				# 每个epoch结束清理一次
				torch.cuda.empty_cache()
				gc.collect()
				logger.info(f"Epoch结束，最大内存使用: {self.max_allocated / (1024**3):.2f} GB")
				self.max_allocated = 0

		# 创建回调函数实例
		memory_callback = MemoryCleanupCallback()

		# 将回调函数添加到模型的callbacks中
		if hasattr(model, 'add_callback'):
			model.add_callback('on_train_batch_end', memory_callback.on_train_batch_end)
			model.add_callback('on_train_epoch_end', memory_callback.on_train_epoch_end)
		else:
			logger.warning("模型不支持add_callback方法，将使用内置内存管理")

		# 直接训练模型
		model.train(**train_args)

		# 训练后再次清理内存
		manual_memory_cleanup()

		# 清理权重文件，只保留最新的和最重要的
		weights_dir = os.path.join(PROJECT_ROOT, "train_results", "train", exp_name, "weights")

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
		output_path = os.path.join(PROJECT_ROOT, "datasets", "train", "weights", f"best_{current_time}.pt")
		os.makedirs(os.path.dirname(output_path), exist_ok=True)

		# 直接从训练目录获取最佳模型路径
		train_dir = os.path.join(PROJECT_ROOT, "train_results", "train")
		best_model_path = os.path.join(train_dir, exp_name, "weights", "best.pt")

		if os.path.exists(best_model_path):
			shutil.copy(best_model_path, output_path)
			logger.info(f"模型已保存到: {output_path}")

			# 更新best.pt模型（将最新的模型自动设置为best.pt）
			logger.info("更新best.pt模型...")
			best_result = update_best_model(PROJECT_ROOT)
			if best_result:
				logger.info(f"已更新best.pt模型: {best_result}")
			else:
				logger.warning("更新best.pt模型失败")

			# 导出模型为ONNX格式以提高推理速度
			try:
				logger.info("导出模型为ONNX格式...")
				onnx_output_path = os.path.join(PROJECT_ROOT, "datasets", "train", "weights", f"best_{current_time}.onnx")
				model = YOLO(best_model_path)
				# 使用与训练相同的图像尺寸进行导出
				model.export(format="onnx", imgsz=384, simplify=True, opset=12, half=True)
				logger.info(f"ONNX模型已保存: {onnx_output_path}")
			except Exception as e:
				logger.warning(f"ONNX导出失败，仅使用PT模型: {str(e)}")
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

					# 更新best.pt模型（将最新的模型自动设置为best.pt）
					logger.info("更新best.pt模型...")
					best_result = update_best_model(PROJECT_ROOT)
					if best_result:
						logger.info(f"已更新best.pt模型: {best_result}")
					else:
						logger.warning("更新best.pt模型失败")
				else:
					# 尝试last.pt模型
					latest_last_model = os.path.join(train_dir, latest_exp_dir, "weights", "last.pt")
					if os.path.exists(latest_last_model):
						shutil.copy(latest_last_model, output_path)
						logger.info(f"找到并保存了最新模型到: {output_path}")

						# 更新best.pt模型（将最新的模型自动设置为best.pt）
						logger.info("更新best.pt模型...")
						best_result = update_best_model(PROJECT_ROOT)
						if best_result:
							logger.info(f"已更新best.pt模型: {best_result}")
						else:
							logger.warning("更新best.pt模型失败")
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

	# 显式设置PyTorch多进程，解决Windows上的内存问题
	if platform.system() == 'Windows':
		# 这将强制PyTorch使用'spawn'而非'fork'，避免内存共享问题
		torch.multiprocessing.set_start_method('spawn', force=True)

	# 获取当前目录作为项目根目录
	PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

	# 解析命令行参数
	parser = argparse.ArgumentParser(description='YOLO模型训练与清理工具')
	parser.add_argument('--clean-only', action='store_true', help='只执行清理操作，不进行训练')
	parser.add_argument('--clean-git', action='store_true', help='清理Git仓库中的大文件')
	parser.add_argument('--preprocess', action='store_true', help='在训练前预处理数据集')
	parser.add_argument('--cache-type', type=str, choices=['disk', 'hdf5'], default='disk', help='缓存类型: disk(使用YOLO的磁盘缓存) 或 hdf5(转换为HDF5格式)')
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
	elif args.preprocess and not args.clean_only and not args.clean_git:
		# 只执行数据预处理，不训练
		logger.info("仅执行数据预处理...")
		data_yaml = os.path.join(PROJECT_ROOT, "datasets", "My First Project.v7i.yolov11", "data.yaml")
		preprocess_dataset(
			data_yaml,
			output_dir=os.path.join(PROJECT_ROOT, "datasets", "preprocessed"),
			image_size=640,
			cache_type=args.cache_type
		)
		logger.info("数据预处理完成")
	else:
		# 执行正常训练流程
		main()

# 功能亮点
"""
1. 预处理数据集功能
   - 支持独立运行预处理步骤
   - 提供两种缓存/预处理模式选择
   - 可以在训练前自动预处理或单独预处理

2. 磁盘缓存模式
   - 利用YOLO内置的disk缓存机制
   - 通过模拟短训练过程强制生成缓存文件
   - 后续训练可以直接使用此缓存

3. HDF5转换模式
   - 将图像数据转换为高效的HDF5格式
   - 支持图像压缩以节省磁盘空间
   - 支持随机访问以加速训练
"""
# 使用指南
"""
1. 只进行数据预处理
   python train_model.py --preprocess --cache-type disk
   python train_model.py --preprocess --cache-type hdf5

2. 预处理并训练
   python train_model.py --preprocess --cache-type disk

3. 普通训练(现在默认使用磁盘缓存)
   python train_model.py
"""
# 关键实现
"""
1. 预处理函数设计
   - 支持多种预处理模式
   - 使用YOLO的内部缓存机制
   - 实现HDF5格式转换

2. 缓存参数修改
   - train_args中的'cache'参数固定为"disk"
   - 不再根据系统内存动态选择

3. 命令行参数扩展
   - 添加--preprocess参数用于开启预处理
   - 添加--cache-type参数选择缓存类型
"""
# 处理流程
"""
1. 如果指定了--preprocess参数:
   a. 先执行数据预处理
   b. 生成缓存或HDF5文件
   c. 更新数据路径

2. 使用磁盘缓存方式进行训练
   a. 'cache': "disk" 强制使用磁盘缓存
   b. 后续训练将利用缓存文件加速

3. 为独立预处理增加单独执行模式
   a. 可以单独执行预处理而不训练
   b. 便于数据准备和调试
"""