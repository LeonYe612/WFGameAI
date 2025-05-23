# Web服务+本地轻量组件混合模式详细设计（最终版）

## 1. 问题与补充内容

### 1.1 模型分发与管理机制

```python
class ModelManager:
    def __init__(self, config):
        self.config = config
        self.model_path = self.config.get('Paths', 'model_file', fallback='models/best.pt')
        self.model_version = self._get_model_version()
        self.hardware_profile = {}

    def _get_model_version(self):
        """获取当前模型版本信息"""
        if not os.path.exists(self.model_path):
            return None
        try:
            # 读取模型元数据或文件属性
            return {"path": self.model_path, "mtime": os.path.getmtime(self.model_path)}
        except Exception as e:
            logging.error(f"无法读取模型信息: {e}")
            return None

    def check_updates(self, server_api):
        """检查服务器是否有更新版本"""
        if not server_api.is_connected():
            return False

        try:
            latest_version = server_api.get("/api/v1/models/latest_version")
            if latest_version > self.model_version.get("version", 0):
                return True
        except:
            return False
        return False

    def download_model(self, server_api):
        """从服务器下载最新模型"""
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, "best.pt.download")

            # 下载模型
            server_api.download("/api/v1/models/latest", temp_file)

            # 验证模型完整性
            if self._verify_model(temp_file):
                # 替换当前模型
                shutil.move(temp_file, self.model_path)
                self.model_version = self._get_model_version()
                return True
        except Exception as e:
            logging.error(f"模型下载失败: {e}")
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        return False
```

### 1.2 自动设备挂载与权限管理

```python
class DeviceAuthorization:
    """设备授权与权限管理"""

    @staticmethod
    def verify_adb_access():
        """验证ADB访问权限"""
        try:
            subprocess.check_output(["adb", "devices"])
            return True
        except:
            return False

    @staticmethod
    def setup_usb_rules(platform):
        """创建必要的USB规则文件"""
        if platform == "Windows":
            # Windows设备驱动检查
            return DeviceAuthorization._setup_windows_drivers()
        elif platform == "Darwin":  # macOS
            return DeviceAuthorization._setup_mac_rules()
        elif platform == "Linux":
            return DeviceAuthorization._setup_linux_rules()
        return False

    @staticmethod
    def _setup_windows_drivers():
        """设置Windows USB驱动"""
        # 检查通用ADB驱动是否安装
        # 如缺失则提示安装
        return True  # 简化版本
```

### 1.3 配置文件统一管理

```python
class ConfigManager:
    """统一配置管理器"""

    def __init__(self, config_path=None):
        self.config = configparser.ConfigParser()
        self.config_path = config_path or self._find_config()
        self.load()

    def _find_config(self):
        """查找配置文件路径"""
        # 搜索顺序:
        # 1. 当前目录
        # 2. 程序所在目录
        # 3. 用户主目录

        search_paths = [
            os.path.join(os.getcwd(), 'config.ini'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'),
            os.path.join(os.path.expanduser('~'), '.wfgameai', 'config.ini')
        ]

        for path in search_paths:
            if os.path.exists(path):
                return path

        # 如果找不到，返回默认路径用于创建
        return search_paths[0]

    def load(self):
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                self.config.read(self.config_path, encoding='utf-8')
                return True
            except Exception as e:
                logging.error(f"配置文件加载失败: {e}")
        return self._create_default_config()

    def _create_default_config(self):
        """创建默认配置文件"""
        # 设置基本配置节
        self.config['Paths'] = {
            'server_dir': os.path.join(os.getcwd(), 'wfgame-ai-server'),
            'scripts_dir': os.path.join(os.getcwd(), 'wfgame-ai-server', 'apps', 'scripts'),
            'testcase_dir': os.path.join(os.getcwd(), 'wfgame-ai-server', 'testcase'),
            'reports_dir': os.path.join(os.getcwd(), 'wfgame-ai-server', 'outputs', 'WFGameAI-reports'),
            'ui_reports_dir': os.path.join(os.getcwd(), 'wfgame-ai-server', 'outputs', 'WFGameAI-reports', 'ui_reports'),
            'datasets_dir': os.path.join(os.getcwd(), 'datasets'),
            'model_file': os.path.join(os.getcwd(), 'models', 'best.pt')
        }

        # 确保目录存在
        for key, path in self.config['Paths'].items():
            if 'dir' in key and not os.path.exists(path):
                os.makedirs(path, exist_ok=True)

        # 保存配置
        return self.save()

    def save(self):
        """保存配置文件"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
            return True
        except Exception as e:
            logging.error(f"配置文件保存失败: {e}")
            return False

    def get_path(self, key):
        """获取路径配置"""
        try:
            return self.config.get('Paths', key)
        except:
            return None
```

### 1.4 网络连接状态管理

```python
class NetworkManager:
    """网络连接管理"""

    def __init__(self, server_url):
        self.server_url = server_url
        self.online = False
        self.check_connection()

    def check_connection(self):
        """检查服务器连接状态"""
        try:
            response = requests.get(f"{self.server_url}/api/v1/ping", timeout=5)
            self.online = response.status_code == 200
        except:
            self.online = False
        return self.online

    def set_offline_mode(self, offline=True):
        """主动设置离线模式"""
        self.online = not offline

    def is_online(self):
        """获取当前连接状态"""
        return self.online

    def wait_for_connection(self, timeout=60, interval=5):
        """等待连接建立"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_connection():
                return True
            time.sleep(interval)
        return False
```

## 2. 关于模型使用的澄清

根据补充信息，我们需要明确以下几点：

### 2.1 模型训练与使用的分离

- **服务器端(4090 GPU)**:
  - 负责YOLO模型的训练和生成best.pt
  - 使用完整的YOLO11m架构
  - 提供best.pt文件的托管和分发

- **本地端(用户电脑)**:
  - 仅使用已训练好的best.pt进行推理
  - 不进行任何模型训练
  - 根据硬件条件选择适当的推理优化方案

### 2.2 本地推理优化方案

对于集成显卡或CPU环境，我们提供以下优化方案，确保best.pt能够高效运行：

1. **GPU内存优化**:
   - 使用PyTorch的`torch.cuda.amp`自动混合精度
   - 批处理大小动态调整，适应可用内存
   - 实现内存管理机制，避免OOM错误

2. **推理引擎转换**:
   - 支持将best.pt转换为ONNX格式
   - 针对Intel集成显卡，支持OpenVINO推理
   - 对于AMD显卡，提供DirectML支持

3. **模型设置动态调整**:
   ```python
   def optimize_model_settings(model, hardware_info):
       """根据硬件条件优化模型设置"""
       if hardware_info.get('gpu_memory', 0) < 2000:  # 小于2GB显存
           # 降低分辨率和批处理大小
           return {
               'img_size': 320,  # 降低从640
               'batch_size': 1,
               'half_precision': True
           }
       elif hardware_info.get('gpu_memory', 0) < 4000:  # 小于4GB显存
           return {
               'img_size': 480,
               'batch_size': 2,
               'half_precision': True
           }
       return {  # 默认设置
           'img_size': 640,
           'batch_size': 4,
           'half_precision': False
       }
   ```

## 3. config.ini 标准化实施

现在我们需要确保所有代码统一使用config.ini作为唯一配置源，不再有任何硬编码路径。实施步骤如下：

### 3.1 统一配置读取接口

```python
# config_utils.py
import os
import configparser
from pathlib import Path

class ConfigReader:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigReader, cls).__new__(cls)
            cls._instance._init_config()
        return cls._instance

    def _init_config(self):
        """初始化配置"""
        self._config = configparser.ConfigParser()
        config_path = self._find_config_file()

        if config_path and os.path.exists(config_path):
            self._config.read(config_path, encoding='utf-8')
        else:
            raise FileNotFoundError("无法找到config.ini配置文件")

    def _find_config_file(self):
        """查找配置文件"""
        # 从当前目录向上查找
        current_dir = Path.cwd()
        while current_dir.as_posix() != current_dir.root:
            config_path = current_dir / "config.ini"
            if config_path.exists():
                return str(config_path)
            current_dir = current_dir.parent

        # 检查配置环境变量
        if os.environ.get('WFGAMEAI_CONFIG'):
            return os.environ.get('WFGAMEAI_CONFIG')

        return None

    def get_path(self, section, key):
        """获取路径配置，确保路径存在"""
        path = self._config.get(section, key, fallback=None)
        if path:
            # 创建目录如果不存在
            if 'dir' in key and not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            return os.path.normpath(path)
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

# 使用单例模式提供全局访问点
config = ConfigReader()
```

### 3.2 path工具函数封装

```python
# path_utils.py
import os
from config_utils import config

def get_server_dir():
    """获取服务器主目录"""
    return config.get_path('Paths', 'server_dir')

def get_scripts_dir():
    """获取脚本目录"""
    return config.get_path('Paths', 'scripts_dir')

def get_testcase_dir():
    """获取测试用例目录"""
    return config.get_path('Paths', 'testcase_dir')

def get_reports_dir():
    """获取报告主目录"""
    return config.get_path('Paths', 'reports_dir')

def get_ui_reports_dir():
    """获取UI报告目录"""
    return config.get_path('Paths', 'ui_reports_dir')

def safe_join_path(base_path, *paths):
    """安全连接路径"""
    return os.path.normpath(os.path.join(base_path, *paths))

def get_testcase_path(filename):
    """获取测试用例文件完整路径"""
    return safe_join_path(get_testcase_dir(), filename)

def get_model_path():
    """获取模型文件路径"""
    return config.get_path('Paths', 'model_file')
```

### 3.3 修改脚本引用示例

修改record_script.py和replay_script.py中的路径引用:

```python
# 修改前
TESTCASE_DIR = "C:/Users/Administrator/PycharmProjects/WFGameAI/wfgame-ai-server/testcase"
MODEL_PATH = "C:/Users/Administrator/PycharmProjects/WFGameAI/models/best.pt"

# 修改后
from path_utils import get_testcase_dir, get_model_path

TESTCASE_DIR = get_testcase_dir()
MODEL_PATH = get_model_path()
```

### 3.4 标准化config.ini文件结构

```ini
# config.ini 标准结构
[Paths]
# 核心目录配置
server_dir = wfgame-ai-server
scripts_dir = %(server_dir)s/apps/scripts
testcase_dir = %(server_dir)s/testcase
reports_dir = %(server_dir)s/outputs/WFGameAI-reports
ui_reports_dir = %(reports_dir)s/ui_reports
datasets_dir = datasets
model_file = models/best.pt

[Server]
# 服务器连接配置
host = 127.0.0.1
port = 8000
api_version = v1
use_https = False

[Model]
# 模型配置
confidence_threshold = 0.25
nms_threshold = 0.45
max_det = 300

[DBMysql]
# 数据库配置信息
HOST = 127.0.0.1
USERNAME = root
PASSWD = qa123456
DBNAME = gogotest_data

[Device]
# 设备管理配置
default_timeout = 30
screenshot_quality = 80
```

## 4. 补充实现细节

### 本地助手用户界面原型

本地助手应用将提供简单直观的界面，核心功能包括:

1. **欢迎/状态页面**:
   - 显示连接状态(在线/离线)
   - 模型状态与版本信息
   - 检测到的本地设备列表

2. **脚本管理页面**:
   - 本地脚本列表
   - 服务器脚本同步状态
   - 脚本编辑与调试功能

3. **设备管理页面**:
   - 本地连接的设备列表
   - 设备详细信息(型号、系统版本等)
   - 设备控制选项(截图、重启等)

4. **执行控制面板**:
   - 选择脚本和设备
   - 设置执行参数
   - 实时执行状态监控
   - 结果预览

5. **设置页面**:
   - 服务器连接配置
   - 本地存储管理
   - 性能调优选项

### 后端服务API设计

为支持本地助手与中央服务器的通信，需要实现以下API端点:

```
# 认证API
POST /api/v1/auth/login        # 用户登录
POST /api/v1/auth/logout       # 用户登出
GET  /api/v1/auth/status       # 检查认证状态

# 模型API
GET  /api/v1/models/latest     # 获取最新模型
GET  /api/v1/models/info       # 获取模型信息

# 脚本API
GET  /api/v1/scripts/list      # 获取脚本列表
GET  /api/v1/scripts/{id}      # 获取单个脚本
POST /api/v1/scripts/upload    # 上传脚本
PUT  /api/v1/scripts/{id}      # 更新脚本

# 设备API
GET  /api/v1/devices/list      # 获取服务器设备列表
POST /api/v1/devices/reserve   # 预约设备
POST /api/v1/devices/release   # 释放设备

# 执行API
POST /api/v1/execute/start     # 开始执行测试
GET  /api/v1/execute/status    # 获取执行状态
POST /api/v1/execute/stop      # 停止执行

# 报告API
GET  /api/v1/reports/list      # 获取报告列表
GET  /api/v1/reports/{id}      # 获取单个报告
POST /api/v1/reports/upload    # 上传本地报告
```
