"""
应用生命周期管理器 - 负责应用的启动、停止和状态管理
"""
import subprocess
import time
import os
import json
import logging
import re
from typing import Optional, Dict, List, Union, Tuple, Any

# 配置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AppLifecycleManager:
    """应用生命周期管理器，提供统一的应用启动、停止和状态检查接口"""

    def __init__(self):
        """初始化应用生命周期管理器"""
        # 模板配置目录
        self.templates_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "app_templates"
        )

        # 确保模板目录存在
        os.makedirs(self.templates_dir, exist_ok=True)

        # 缓存已加载的模板
        self._template_cache = {}

    def start_app(self, app_name_or_package: str, device_id: str) -> bool:
        """
        启动应用

        Args:
            app_name_or_package: 应用模板名称或包名
            device_id: 设备ID

        Returns:
            bool: 启动是否成功
        """
        logger.info(f"尝试启动应用: {app_name_or_package} 在设备 {device_id}")

        # 尝试作为模板名称处理
        template = self._load_template(app_name_or_package)
        if template:
            package_name = template.get('package_name')
            main_activity = template.get('main_activity', '.MainActivity')
            logger.info(f"使用模板启动应用: {package_name}/{main_activity}")
        else:
            # 作为包名直接使用
            package_name = app_name_or_package
            main_activity = '.MainActivity'
            logger.info(f"直接使用包名启动应用: {package_name}/{main_activity}")

        if not package_name:
            logger.error(f"无法启动应用: {app_name_or_package}，未找到包名")
            return False

        # 确保主活动名称格式正确
        if main_activity and not main_activity.startswith('.') and not '/' in main_activity:
            main_activity = f".{main_activity}"

        # 组装完整组件名
        component = f"{package_name}/{main_activity}" if main_activity else package_name

        # 执行启动命令
        try:
            cmd = f"adb -s {device_id} shell am start -n {component}"
            logger.info(f"执行命令: {cmd}")
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=30
            )

            # 检查命令输出
            if result.returncode == 0:
                logger.info(f"应用启动命令执行成功: {result.stdout.strip()}")

                # 等待应用启动并验证
                time.sleep(1)  # 给应用启动一点时间

                # 验证应用是否成功运行
                if self.check_app_running(package_name, device_id):
                    logger.info(f"应用成功启动并运行中: {package_name}")
                    return True
                else:
                    logger.warning(f"应用启动命令成功但应用未运行: {package_name}")
                    return False
            else:
                logger.error(f"应用启动命令失败: {result.stderr.strip()}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"启动应用超时: {package_name}")
            return False
        except Exception as e:
            logger.error(f"启动应用出错: {e}")
            return False

    def stop_app(self, app_name_or_package: str, device_id: str) -> bool:
        """
        停止应用

        Args:
            app_name_or_package: 应用模板名称或包名
            device_id: 设备ID

        Returns:
            bool: 停止是否成功
        """
        logger.info(f"尝试停止应用: {app_name_or_package} 在设备 {device_id}")

        # 尝试作为模板名称处理
        template = self._load_template(app_name_or_package)
        if template:
            package_name = template.get('package_name')
            logger.info(f"使用模板停止应用: {package_name}")
        else:
            # 作为包名直接使用
            package_name = app_name_or_package
            logger.info(f"直接使用包名停止应用: {package_name}")

        if not package_name:
            logger.error(f"无法停止应用: {app_name_or_package}，未找到包名")
            return False

        # 执行强制停止命令
        return self.force_stop_by_package(package_name, device_id)

    def force_stop_by_package(self, package_name: str, device_id: str) -> bool:
        """
        通过包名强制停止应用

        Args:
            package_name: 应用包名
            device_id: 设备ID

        Returns:
            bool: 停止是否成功
        """
        logger.info(f"强制停止应用: {package_name} 在设备 {device_id}")

        try:
            cmd = f"adb -s {device_id} shell am force-stop {package_name}"
            logger.info(f"执行命令: {cmd}")
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=10
            )

            # 检查命令执行是否成功
            if result.returncode == 0:
                logger.info(f"应用停止命令执行成功，等待验证")

                # 等待应用完全停止
                time.sleep(1)

                # 验证应用是否已停止
                if not self.check_app_running(package_name, device_id):
                    logger.info(f"已确认应用已停止: {package_name}")
                    return True
                else:
                    logger.warning(f"应用停止命令成功但应用仍在运行: {package_name}")
                    return False
            else:
                logger.error(f"应用停止命令失败: {result.stderr.strip()}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"停止应用超时: {package_name}")
            return False
        except Exception as e:
            logger.error(f"停止应用出错: {e}")
            return False

    def check_app_running(self, package_name: str, device_id: str) -> bool:
        """
        检查应用是否正在运行

        Args:
            package_name: 应用包名
            device_id: 设备ID

        Returns:
            bool: 应用是否在运行        """
        logger.info(f"检查应用是否运行: {package_name} 在设备 {device_id}")

        try:
            # 方法1: 使用dumpsys activity检查应用进程 (Windows兼容)
            cmd = ["adb", "-s", device_id, "shell", "dumpsys", "activity", "processes"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and package_name in result.stdout:
                logger.info(f"通过进程检查确认应用正在运行: {package_name}")
                return True            # 方法2: 检查应用当前活动 (Windows兼容)
            cmd = ["adb", "-s", device_id, "shell", "dumpsys", "activity", "activities"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and package_name in result.stdout:
                logger.info(f"通过活动检查确认应用正在运行: {package_name}")
                return True            # 方法3: 使用ps命令检查进程 (Windows兼容)
            cmd = ["adb", "-s", device_id, "shell", "ps", "-A"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and package_name in result.stdout:
                logger.info(f"通过ps命令确认应用正在运行: {package_name}")
                return True

            logger.info(f"应用未运行: {package_name}")
            return False

        except subprocess.TimeoutExpired:
            logger.error(f"检查应用状态超时: {package_name}")
            return False
        except Exception as e:
            logger.error(f"检查应用状态出错: {e}")
            return False

    def get_running_apps(self, device_id: str) -> List[str]:
        """
        获取设备上当前运行的所有应用包名

        Args:
            device_id: 设备ID

        Returns:
            List[str]: 运行中应用的包名列表
        """
        logger.info(f"获取设备运行中的应用: {device_id}")

        running_apps = []

        try:
            # 使用dumpsys activity processes获取所有运行的应用 (Windows兼容)
            cmd = ["adb", "-s", device_id, "shell", "dumpsys", "activity", "processes"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # 匹配所有 ProcessRecord 中的包名
                # 格式: ProcessRecord{xxx pid:package_name/xxx}
                pattern = re.compile(r'ProcessRecord\{[^}]+ \d+:([\w.]+)[:/]')
                matches = pattern.findall(result.stdout)

                # 过滤系统应用和去重
                running_apps = list(set([pkg for pkg in matches if not pkg.startswith('android.')
                              and not pkg.startswith('com.android.')
                              and not pkg.startswith('com.google.')]))

                logger.info(f"检测到运行中的应用: {len(running_apps)} 个")
                if running_apps:
                    logger.info(f"运行中的应用列表: {running_apps}")
            else:
                logger.error(f"获取运行中应用失败: {result.stderr.strip()}")

        except Exception as e:
            logger.error(f"获取运行中应用出错: {e}")
        return running_apps

    def _load_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        加载应用模板

        Args:
            template_name: 模板名称

        Returns:
            Optional[Dict[str, Any]]: 模板数据，如果找不到模板则返回None
        """
        # 如果有缓存，直接返回
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        # 尝试加载模板文件 - 首先在默认路径
        template_path = os.path.join(self.templates_dir, f"{template_name}.json")

        # 如果默认路径不存在，尝试在scripts目录查找
        if not os.path.exists(template_path):
            scripts_template_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "apps", "scripts", "app_templates"
            )
            template_path = os.path.join(scripts_template_dir, f"{template_name}.json")

            if os.path.exists(template_path):
                logger.info(f"在脚本目录找到模板文件: {template_path}")
            else:
                logger.warning(f"模板文件不存在: {template_name}.json (已尝试两个路径)")
                return None

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)

            # 缓存模板
            self._template_cache[template_name] = template
            return template
        except Exception as e:
            logger.error(f"加载模板失败: {e}")
            return None

    def create_template(self, template_name: str, package_name: str,
                       main_activity: str = '.MainActivity',
                       description: str = '') -> bool:
        """
        创建应用模板

        Args:
            template_name: 模板名称
            package_name: 应用包名
            main_activity: 应用主活动名称
            description: 模板描述

        Returns:
            bool: 创建是否成功
        """
        logger.info(f"创建应用模板: {template_name}")

        template = {
            'name': template_name,
            'package_name': package_name,
            'main_activity': main_activity,
            'description': description,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        template_path = os.path.join(self.templates_dir, f"{template_name}.json")
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)

            # 更新缓存
            self._template_cache[template_name] = template
            logger.info(f"应用模板创建成功: {template_path}")
            return True
        except Exception as e:
            logger.error(f"创建应用模板失败: {e}")
            return False

    def get_app_templates(self) -> List[Dict[str, Any]]:
        """
        获取所有应用模板

        Returns:
            List[Dict[str, Any]]: 模板列表
        """
        templates = []

        try:
            # 确保目录存在
            if not os.path.exists(self.templates_dir):
                return []

            # 加载所有模板文件
            for filename in os.listdir(self.templates_dir):
                if filename.endswith('.json'):
                    template_path = os.path.join(self.templates_dir, filename)
                    try:
                        with open(template_path, 'r', encoding='utf-8') as f:
                            template = json.load(f)

                        templates.append(template)

                        # 更新缓存
                        template_name = os.path.splitext(filename)[0]
                        self._template_cache[template_name] = template
                    except Exception as e:
                        logger.error(f"加载模板文件失败 {filename}: {e}")
        except Exception as e:
            logger.error(f"获取应用模板失败: {e}")

        return templates
