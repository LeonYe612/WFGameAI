import json
import os

# 完全抑制日志输出
import logging
import sys
import warnings

warnings.filterwarnings("ignore")
logging.getLogger(__name__).setLevel(logging.ERROR)
logging.getLogger().setLevel(logging.ERROR)

# 修复编码问题
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
            sys.stderr.reconfigure(encoding="utf-8", errors="ignore")
    except:
        pass
import configparser
from pathlib import Path
import logging
import glob
import glob
import shutil


from dataclasses import dataclass
from typing import Optional


# 减少日志输出，只在ERROR级别输出
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class ConfigManager:
    """
    统一配置管理类，用于处理config.ini中的所有路径配置
    """
    _instance = None
    _config = None
    _config_path = os.path.join(Path.cwd().parent, "config.ini")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件"""
        self._config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        self._config_path = self._find_config_file()
        if self._config_path and os.path.exists(self._config_path):
            self._config.read(self._config_path, encoding='utf-8')
            logger.warning(f"ConfigManager 已加载配置文件: {self._config_path}")
        else:
            raise FileNotFoundError(f"无法找到 {self._config_path} 配置文件")

    def _find_config_file(self):
        """查找配置文件"""
        try:
            # 优先使用环境变量中的配置路径
            if "WFGAMEAI_CONFIG" in os.environ:
                return os.environ["WFGAMEAI_CONFIG"]

            # 根据 AI_ENV 选择配置文件
            ai_env = os.environ.get("AI_ENV", "").strip().lower()
            base_dir = Path.cwd().parent
            if ai_env:
                if ai_env == "prod":
                    # 生产环境固定使用 config.ini
                    return os.path.join(base_dir, "config.ini")
                else:
                    # 其它环境使用 config_{env}.ini（例如 dev -> config_dev.ini）
                    return os.path.join(base_dir, f"config_{ai_env}.ini")

            # 默认回退到 config.ini
            return self._config_path
        except Exception as e:
            logger.error(f"查找配置文件时出错，使用默认 config.ini: {e}")
            return self._config_path

    def get_path(self, key, create_if_missing=True):
        """
        获取配置文件中的路径

        Args:
            key: 路径配置项名称 (如 'project_root', 'server_dir' 等)
            create_if_missing: 如果目录不存在是否创建

        Returns:
            str: 标准化的路径字符串
        """
        try:
            path = self._config.get('paths', key)
            path = os.path.normpath(path)

            # 如果是目录且不存在，则创建
            if create_if_missing and key.endswith('_dir') and not os.path.exists(path):
                os.makedirs(path, exist_ok=True)

            return path
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logger.error(f"配置文件中找不到路径: {key}, 错误: {e}")
            return None

    def get(self, section, key, fallback=None):
        """获取一般配置项"""
        return self._config.get(section, key, fallback=fallback)

    def getint(self, section, key, fallback=None):
        """获取整数配置项"""
        return self._config.getint(section, key, fallback=fallback)

    def getboolean(self, section, key, fallback=None):
        """获取布尔配置项"""
        return self._config.getboolean(section, key, fallback=fallback)

    def get_file_path(self, base_dir_key, *rel_paths):
        """
        根据基础目录和相对路径，构建完整的文件路径

        Args:
            base_dir_key: 基础目录的配置键名
            *rel_paths: 相对路径部分

        Returns:
            str: 完整的文件路径
        """
        base_dir = self.get_path(base_dir_key)
        if not base_dir:
            return None
        return os.path.normpath(os.path.join(base_dir, *rel_paths))

# 提供全局单例实例
config = ConfigManager()

def load_yolo_model(model_path=None, device="auto", base_dir=None, model_class=None, specific_model=None, exit_on_failure=True):
    """
    加载YOLO模型的通用函数 - 支持多种调用方式，兼容已有代码

    兼容两种调用模式:
    1. load_yolo_model(model_path=None, device="auto") - 基本模式
    2. load_yolo_model(base_dir, model_class, specific_model, exit_on_failure, device) - 扩展模式
    """
    # 导入必要的模块
    import sys
    from importlib import import_module
    try:
        from ultralytics import YOLO
        yolo_imported = True
    except ImportError:
        yolo_imported = False

    # 检测是否为扩展模式调用 (传入base_dir和model_class)
    extended_mode = base_dir is not None and model_class is not None

    if extended_mode:
        # 扩展模式 - 兼容旧版load_yolo_model函数
        logger.info(f"使用扩展模式加载模型, base_dir: {base_dir}")

        # 搜索模型文件
        model_found = False
        model_path = None

        # 路径搜索优先级列表
        search_paths = []

        # 1. 首先尝试指定的模型文件
        if specific_model:
            if os.path.isabs(specific_model):
                search_paths.append(specific_model)
            else:
                # 相对路径，在几个可能的位置尝试
                search_paths.append(os.path.join(base_dir, specific_model))
                search_paths.append(os.path.join(base_dir, "models", specific_model))
                search_paths.append(os.path.join(os.path.dirname(base_dir), "models", specific_model))

        # 2. 尝试weights目录中的模型文件
        weights_dir = os.path.join(base_dir, "datasets", "train", "weights")
        search_paths.append(os.path.join(weights_dir, "best.pt"))

        # 3. 尝试常见的默认位置
        search_paths.append(os.path.join(get_project_root(), "models", "best.pt"))
        search_paths.append(os.path.join(get_project_root(), "datasets", "train", "weights", "best.pt"))
        search_paths.append(os.path.join(os.path.dirname(base_dir), "models", "best.pt"))

        # 搜索可用的模型文件
        for path in search_paths:
            if os.path.exists(path):
                model_path = path
                model_found = True
                logger.info(f"找到模型文件: {model_path}")
                break

        if not model_found:
            error_msg = "未找到可用的模型文件，请检查模型路径"
            logger.error(error_msg)
            if exit_on_failure:
                logger.error("由于找不到模型文件，程序将退出")
                sys.exit(1)
            else:
                raise FileNotFoundError(error_msg)
    else:
        # 基本模式
        if model_path is None:
            model_path = get_weights_path()

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

    # 根据设备类型自动选择运行设备
    if device == "auto" or device is None:
        if os.name == "nt":  # Windows系统
            # 屏蔽nvidia-smi输出，仅检测是否可用
            try:
                import subprocess
                result = subprocess.run(["nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                device = "cuda" if result.returncode == 0 else "cpu"
            except Exception:
                device = "cpu"
        elif sys.platform == "darwin":  # macOS系统
            device = "mps"
        else:  # Linux等其他系统
            try:
                import subprocess
                result = subprocess.run(["nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                device = "cuda" if result.returncode == 0 else "cpu"
            except Exception:
                device = "cpu"

    # 确保存在YOLO类
    if not yolo_imported and model_class is None:
        raise ImportError("未导入ultralytics.YOLO，无法加载模型")

    # 确定使用哪个模型类
    ModelClass = model_class if model_class is not None else YOLO

    logger.info(f"使用设备 {device} 加载模型: {model_path}")
    try:
        model = ModelClass(model_path)
        model.to(device)
        return model
    except Exception as e:
        error_msg = f"模型加载失败: {e}"
        logger.error(error_msg)
        if extended_mode and exit_on_failure:
            logger.error("由于模型加载失败，程序将退出")
            sys.exit(1)
        else:
            raise Exception(error_msg)

def update_best_model(project_root):
    """更新最佳模型文件，从旧版utils.py保留的功能"""
    # 找到最新的实验目录
    train_dir = os.path.join(project_root, "train_results", "train")
    if not os.path.exists(train_dir):
        return {"success": False, "message": "训练目录不存在"}

    exp_dirs = sorted([d for d in os.listdir(train_dir) if os.path.isdir(os.path.join(train_dir, d))])
    if not exp_dirs:
        return {"success": False, "message": "没有找到实验目录"}

    latest_exp = exp_dirs[-1]
    weights_dir = os.path.join(train_dir, latest_exp, "weights")
    if not os.path.exists(weights_dir):
        return {"success": False, "message": f"权重目录不存在: {weights_dir}"}

    # 找到best.pt文件
    best_pt = os.path.join(weights_dir, "best.pt")
    if not os.path.exists(best_pt):
        return {"success": False, "message": f"未找到best.pt文件: {best_pt}"}

    # 复制到models目录
    models_dir = os.path.join(project_root, "models")
    os.makedirs(models_dir, exist_ok=True)
    target_path = os.path.join(models_dir, "best.pt")

    try:
        shutil.copy2(best_pt, target_path)
        return {
            "success": True,
            "message": f"已更新best.pt文件",
            "source": best_pt,
            "target": target_path
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"更新best.pt文件失败: {str(e)}"
        }

# 常用路径访问函数
def get_project_root():
    return config.get_path('project_root')

def get_server_dir():
    return config.get_path('server_dir')

def get_scripts_dir():
    return config.get_path('scripts_dir')

def get_testcase_dir():
    return config.get_path('testcase_dir')

def get_reports_dir():
    return config.get_path('reports_dir')

def get_ui_reports_dir():
    return config.get_path('ui_reports_dir')

def get_datasets_dir():
    return config.get_path('datasets_dir')

def get_weights_dir():
    return config.get_path('weights_dir')

def get_train_results_dir():
    return config.get_path('train_results_dir')

def get_weights_path():
    """获取模型文件路径"""
    weights_dir = get_weights_dir()
    if weights_dir and os.path.exists(weights_dir):
        # 查找最新的best.pt文件
        best_files = sorted(glob.glob(os.path.join(weights_dir, "best*.pt")), key=os.path.getmtime, reverse=True)
        if best_files:
            return best_files[0]

    # 如果在weights_dir中找不到，则尝试在项目根目录的models文件夹中查找
    models_dir = os.path.join(get_project_root(), "models")
    if os.path.exists(models_dir):
        best_pt = os.path.join(models_dir, "best.pt")
        if os.path.exists(best_pt):
            return best_pt

    # 如果都找不到，返回None
    logger.warning("找不到模型文件 best.pt")
    return None

def get_model_path():
    """获取模型文件路径"""
    weights_path = get_weights_path()
    if weights_path:
        return weights_path

    # 如果无法获取权重路径，返回默认模型路径
    project_root = get_project_root()
    if project_root:
        default_model_path = os.path.join(project_root, "models", "best.pt")
        if os.path.exists(default_model_path):
            return default_model_path

    # 如果所有尝试都失败，返回None
    logger.warning("无法找到有效的模型路径")
    return None

@dataclass
class RedisConfigObj:
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    db: int = 0
    redis_url: str = ""
    # 连接池配置
    max_connections: int = 20
    socket_connect_timeout: int = 5
    socket_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30

def get_redis_conn(config_type="redis") -> RedisConfigObj:
    host = config.get(config_type, 'host', fallback='localhost')
    port = config.getint(config_type, 'port', fallback=6379)
    username = config.get(config_type, 'username', fallback="")
    password = config.get(config_type, 'password', fallback="")
    db = config.getint(config_type, 'db', fallback=0)
    # 连接池配置
    max_connections = config.getint(config_type, 'max_connections', fallback=20)
    socket_connect_timeout = config.getint(config_type, 'socket_connect_timeout', fallback=5)
    socket_timeout = config.getint(config_type, 'socket_timeout', fallback=5)
    retry_on_timeout = config.getboolean(config_type, 'retry_on_timeout', fallback=True)
    health_check_interval = config.getint(config_type, 'health_check_interval', fallback=30)

    # 构建 Redis URL：仅在有用户名和密码时才包含认证信息
    if username and password:
        redis_url = f'redis://{username}:{password}@{host}:{port}/{db}'
    else:
        redis_url = f'redis://{host}:{port}/{db}'
    
    return RedisConfigObj(
        host=host,
        port=port,
        username=username if username else None,
        password=password if password else None,
        db=db,
        redis_url=redis_url,
        max_connections=max_connections,
        socket_connect_timeout=socket_connect_timeout,
        socket_timeout=socket_timeout,
        retry_on_timeout=retry_on_timeout,
        health_check_interval=health_check_interval
    )

