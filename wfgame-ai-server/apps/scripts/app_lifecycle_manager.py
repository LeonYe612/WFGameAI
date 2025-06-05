#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用生命周期管理系统
独立的应用启动/停止管理器，使用模板化配置，与脚本记录/回放功能完全隔离
"""

import os
import json
import time
import subprocess
import configparser
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppState(Enum):
    """应用状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class AppInstance:
    """应用实例信息"""
    package_name: str
    device_serial: str
    pid: Optional[int] = None
    state: AppState = AppState.STOPPED
    start_time: Optional[float] = None
    last_check_time: Optional[float] = None
    error_message: Optional[str] = None
    restart_count: int = 0


@dataclass
class AppTemplate:
    """应用模板配置"""
    name: str
    package_name: str
    activity_name: Optional[str] = None
    start_commands: List[str] = None
    stop_commands: List[str] = None
    check_commands: List[str] = None
    startup_wait_time: int = 5
    max_restart_attempts: int = 3
    health_check_interval: int = 30
    custom_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.start_commands is None:
            self.start_commands = []
        if self.stop_commands is None:
            self.stop_commands = []
        if self.check_commands is None:
            self.check_commands = []
        if self.custom_params is None:
            self.custom_params = {}


class AppLifecycleManager:
    """应用生命周期管理器"""

    def __init__(self, config_path: str = None):
        """
        初始化应用生命周期管理器

        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()

        # 应用模板存储
        self.app_templates: Dict[str, AppTemplate] = {}

        # 运行中的应用实例
        self.app_instances: Dict[str, AppInstance] = {}  # key: f"{device_serial}_{package_name}"

        # 监控线程
        self.monitoring_thread = None
        self.monitoring_active = False

        # 初始化组件
        self._init_directories()
        self._load_app_templates()

        logger.info("应用生命周期管理器初始化完成")

    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        return os.path.join(os.path.dirname(__file__), "..", "..", "..", "config.ini")

    def _load_config(self) -> configparser.ConfigParser:
        """加载配置文件"""
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding='utf-8')
        return config

    def _init_directories(self):
        """初始化必要的目录"""
        self.base_dir = Path(self.config.get('paths', 'project_root', fallback='.'))
        self.templates_dir = self.base_dir / "wfgame-ai-server" / "apps" / "scripts" / "app_templates"
        self.logs_dir = self.base_dir / "wfgame-ai-server" / "apps" / "logs" / "app_lifecycle"

        # 创建目录
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"模板目录: {self.templates_dir}")
        logger.info(f"日志目录: {self.logs_dir}")

    def _load_app_templates(self):
        """加载应用模板配置"""
        template_files = list(self.templates_dir.glob("*.json"))

        for template_file in template_files:
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)

                template = AppTemplate(**template_data)
                self.app_templates[template.name] = template
                logger.info(f"加载应用模板: {template.name}")

            except Exception as e:
                logger.error(f"加载模板文件 {template_file} 失败: {e}")

    def create_app_template(self, template_data: Dict[str, Any]) -> bool:
        """
        创建新的应用模板

        Args:
            template_data: 模板数据字典

        Returns:
            bool: 创建是否成功
        """
        try:
            template = AppTemplate(**template_data)

            # 保存到文件
            template_file = self.templates_dir / f"{template.name}.json"
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(template), f, indent=4, ensure_ascii=False)

            # 添加到内存
            self.app_templates[template.name] = template

            logger.info(f"创建应用模板成功: {template.name}")
            return True

        except Exception as e:
            logger.error(f"创建应用模板失败: {e}")
            return False

    def get_app_templates(self) -> Dict[str, AppTemplate]:
        """获取所有应用模板"""
        return self.app_templates.copy()

    def get_app_template(self, template_name: str) -> Optional[AppTemplate]:
        """获取指定的应用模板"""
        return self.app_templates.get(template_name)

    def start_app(self, template_name: str, device_serial: str, **kwargs) -> bool:
        """
        启动应用

        Args:
            template_name: 应用模板名称
            device_serial: 设备序列号
            **kwargs: 额外参数

        Returns:
            bool: 启动是否成功
        """
        template = self.get_app_template(template_name)
        if not template:
            logger.error(f"找不到应用模板: {template_name}")
            return False

        instance_key = f"{device_serial}_{template.package_name}"

        # 检查是否已经在运行
        if instance_key in self.app_instances:
            instance = self.app_instances[instance_key]
            if instance.state in [AppState.RUNNING, AppState.STARTING]:
                logger.warning(f"应用 {template_name} 在设备 {device_serial} 上已经在运行")
                return True

        try:
            # 创建应用实例
            instance = AppInstance(
                package_name=template.package_name,
                device_serial=device_serial,
                state=AppState.STARTING,
                start_time=time.time()
            )

            self.app_instances[instance_key] = instance            # 执行启动命令
            success = self._execute_start_commands(template, device_serial, **kwargs)

            if success:
                # 等待启动完成
                logger.info(f"应用启动命令执行成功，等待 {template.startup_wait_time} 秒...")
                time.sleep(template.startup_wait_time)

                # 多次检查应用状态，给应用更多启动时间
                max_check_attempts = 3
                for attempt in range(max_check_attempts):
                    if self._check_app_running(template, device_serial):
                        instance.state = AppState.RUNNING
                        instance.last_check_time = time.time()
                        logger.info(f"应用 {template_name} 在设备 {device_serial} 上启动成功 (第 {attempt + 1} 次检查)")

                        # 启动监控线程
                        self._start_monitoring_if_needed()
                        return True
                    else:
                        if attempt < max_check_attempts - 1:
                            logger.info(f"第 {attempt + 1} 次检查失败，等待 2 秒后重试...")
                            time.sleep(2)
                        else:
                            logger.error(f"应用 {template_name} 启动后检查失败，已尝试 {max_check_attempts} 次")

                instance.state = AppState.ERROR
                instance.error_message = "启动后检查失败"
                logger.error(f"应用 {template_name} 在设备 {device_serial} 上启动失败")
                return False
            else:
                instance.state = AppState.ERROR
                instance.error_message = "启动命令执行失败"
                return False

        except Exception as e:
            logger.error(f"启动应用 {template_name} 时发生异常: {e}")
            if instance_key in self.app_instances:
                self.app_instances[instance_key].state = AppState.ERROR
                self.app_instances[instance_key].error_message = str(e)
            return False

    def stop_app(self, template_name: str, device_serial: str) -> bool:
        """
        停止应用

        Args:
            template_name: 应用模板名称
            device_serial: 设备序列号

        Returns:
            bool: 停止是否成功
        """
        template = self.get_app_template(template_name)
        if not template:
            logger.error(f"找不到应用模板: {template_name}")
            return False

        instance_key = f"{device_serial}_{template.package_name}"

        if instance_key not in self.app_instances:
            logger.warning(f"应用 {template_name} 在设备 {device_serial} 上未运行")
            return True

        try:
            instance = self.app_instances[instance_key]
            instance.state = AppState.STOPPING

            # 执行停止命令
            success = self._execute_stop_commands(template, device_serial)

            if success:
                instance.state = AppState.STOPPED
                logger.info(f"应用 {template_name} 在设备 {device_serial} 上停止成功")
            else:
                instance.state = AppState.ERROR
                instance.error_message = "停止命令执行失败"
                logger.error(f"应用 {template_name} 在设备 {device_serial} 上停止失败")

            return success

        except Exception as e:
            logger.error(f"停止应用 {template_name} 时发生异常: {e}")
            if instance_key in self.app_instances:
                self.app_instances[instance_key].state = AppState.ERROR
                self.app_instances[instance_key].error_message = str(e)
            return False

    def restart_app(self, template_name: str, device_serial: str, **kwargs) -> bool:
        """
        重启应用

        Args:
            template_name: 应用模板名称
            device_serial: 设备序列号
            **kwargs: 额外参数

        Returns:
            bool: 重启是否成功
        """
        # 先停止
        if not self.stop_app(template_name, device_serial):
            logger.error(f"重启应用 {template_name} 失败: 停止阶段失败")
            return False

        # 等待一段时间
        time.sleep(2)

        # 再启动
        return self.start_app(template_name, device_serial, **kwargs)

    def get_app_status(self, template_name: str = None, device_serial: str = None) -> Dict[str, Any]:
        """
        获取应用状态

        Args:
            template_name: 应用模板名称，如果为None则返回所有应用
            device_serial: 设备序列号，如果为None则返回所有设备

        Returns:
            Dict[str, Any]: 应用状态信息
        """
        result = {}

        for instance_key, instance in self.app_instances.items():
            device, package = instance_key.split('_', 1)

            # 过滤条件
            if device_serial and device != device_serial:
                continue

            if template_name:
                template = self.get_app_template(template_name)
                if not template or template.package_name != package:
                    continue

            result[instance_key] = {
                'package_name': instance.package_name,
                'device_serial': instance.device_serial,
                'state': instance.state.value,
                'start_time': instance.start_time,
                'last_check_time': instance.last_check_time,
                'error_message': instance.error_message,
                'restart_count': instance.restart_count
            }

        return result

    def _execute_start_commands(self, template: AppTemplate, device_serial: str, **kwargs) -> bool:
        """执行启动命令"""
        if not template.start_commands:
            # 默认启动命令
            commands = [f"adb -s {device_serial} shell am start -n {template.package_name}"]
            if template.activity_name:
                commands = [f"adb -s {device_serial} shell am start -n {template.package_name}/{template.activity_name}"]
        else:
            # 使用模板定义的命令
            commands = [cmd.format(device_serial=device_serial, package_name=template.package_name,
                                 activity_name=template.activity_name, **kwargs)
                       for cmd in template.start_commands]

        return self._execute_commands(commands, f"启动应用 {template.name}")

    def _execute_stop_commands(self, template: AppTemplate, device_serial: str) -> bool:
        """执行停止命令"""
        if not template.stop_commands:
            # 默认停止命令
            commands = [f"adb -s {device_serial} shell am force-stop {template.package_name}"]
        else:
            # 使用模板定义的命令
            commands = [cmd.format(device_serial=device_serial, package_name=template.package_name)
                       for cmd in template.stop_commands]

        return self._execute_commands(commands, f"停止应用 {template.name}")
    def _check_app_running(self, template: AppTemplate, device_serial: str) -> bool:
        """检查应用是否在运行"""
        if template.check_commands:
            # 使用模板定义的检查命令，但改进处理逻辑
            for cmd in template.check_commands:
                try:
                    formatted_cmd = cmd.format(device_serial=device_serial, package_name=template.package_name)
                    logger.info(f"执行检查命令: {formatted_cmd}")

                    result = subprocess.run(
                        formatted_cmd.split(),
                        capture_output=True, text=True, timeout=10
                    )

                    # 对于pidof命令，返回码0且有输出表示应用在运行
                    if result.returncode == 0 and result.stdout.strip():
                        logger.info(f"应用 {template.name} 检查通过，PID: {result.stdout.strip()}")
                        return True
                    else:
                        logger.info(f"应用 {template.name} 检查失败，返回码: {result.returncode}, 输出: '{result.stdout.strip()}'")

                except Exception as e:
                    logger.error(f"检查命令执行异常: {e}")

            return False
        else:
            # 默认检查命令
            try:
                result = subprocess.run(
                    f"adb -s {device_serial} shell pidof {template.package_name}".split(),
                    capture_output=True, text=True, timeout=10
                )
                return result.returncode == 0 and result.stdout.strip()
            except Exception as e:
                logger.error(f"检查应用运行状态失败: {e}")
                return False

    def _execute_commands(self, commands: List[str], operation_name: str) -> bool:
        """执行命令列表"""
        for command in commands:
            try:
                logger.info(f"执行命令: {command}")
                result = subprocess.run(
                    command.split() if isinstance(command, str) else command,
                    capture_output=True, text=True, timeout=30
                )

                if result.returncode != 0:
                    logger.error(f"{operation_name} 命令失败: {command}")
                    logger.error(f"错误输出: {result.stderr}")
                    return False

            except subprocess.TimeoutExpired:
                logger.error(f"{operation_name} 命令超时: {command}")
                return False
            except Exception as e:
                logger.error(f"{operation_name} 命令异常: {command}, 错误: {e}")
                return False

        return True

    def _start_monitoring_if_needed(self):
        """启动监控线程（如果需要）"""
        if not self.monitoring_active and self.app_instances:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            logger.info("启动应用监控线程")

    def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                current_time = time.time()

                for instance_key, instance in list(self.app_instances.items()):
                    if instance.state == AppState.RUNNING:
                        template = None
                        for t in self.app_templates.values():
                            if t.package_name == instance.package_name:
                                template = t
                                break

                        if template and current_time - instance.last_check_time >= template.health_check_interval:
                            # 执行健康检查
                            if self._check_app_running(template, instance.device_serial):
                                instance.last_check_time = current_time
                            else:
                                logger.warning(f"应用 {template.name} 在设备 {instance.device_serial} 上可能已停止")
                                instance.state = AppState.STOPPED

                                # 尝试自动重启
                                if instance.restart_count < template.max_restart_attempts:
                                    logger.info(f"尝试自动重启应用 {template.name}")
                                    instance.restart_count += 1
                                    self.start_app(template.name, instance.device_serial)

                # 如果没有运行中的应用，停止监控
                if not any(instance.state == AppState.RUNNING for instance in self.app_instances.values()):
                    self.monitoring_active = False
                    logger.info("所有应用已停止，停止监控线程")
                    break

                time.sleep(10)  # 监控间隔

            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(10)

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)

    def cleanup(self):
        """清理资源"""
        logger.info("开始清理应用生命周期管理器...")

        # 停止所有应用
        for instance_key, instance in list(self.app_instances.items()):
            if instance.state in [AppState.RUNNING, AppState.STARTING]:
                device, package = instance_key.split('_', 1)
                for template in self.app_templates.values():
                    if template.package_name == package:
                        self.stop_app(template.name, device)
                        break

        # 停止监控
        self.stop_monitoring()

        logger.info("应用生命周期管理器清理完成")

    def force_stop_by_package(self, package_name: str, device_serial: str) -> bool:
        """
        直接通过包名强制停止应用

        Args:
            package_name: 应用包名
            device_serial: 设备序列号

        Returns:
            bool: 停止是否成功
        """
        try:
            logger.info(f"强制停止应用包 {package_name} 在设备 {device_serial}")

            # 构建停止命令
            stop_command = f"adb -s {device_serial} shell am force-stop {package_name}"

            # 执行停止命令
            result = subprocess.run(
                stop_command.split(),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"应用包 {package_name} 在设备 {device_serial} 上强制停止成功")

                # 如果实例存在，更新状态
                instance_key = f"{device_serial}_{package_name}"
                if instance_key in self.app_instances:
                    self.app_instances[instance_key].state = AppState.STOPPED

                return True
            else:
                logger.error(f"强制停止应用包 {package_name} 失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"强制停止应用包 {package_name} 时发生异常: {e}")
            return False

    def force_start_by_package(self, package_name: str, device_serial: str, activity_name: Optional[str] = None) -> bool:
        """
        直接通过包名启动应用

        Args:
            package_name: 应用包名
            device_serial: 设备序列号
            activity_name: Activity名称（可选）

        Returns:
            bool: 启动是否成功
        """
        try:
            logger.info(f"启动应用包 {package_name} 在设备 {device_serial}")

            # 先停止应用
            self.force_stop_by_package(package_name, device_serial)
            time.sleep(1)

            # 构建启动命令
            if activity_name:
                start_command = f"adb -s {device_serial} shell am start -n {package_name}/{activity_name}"
            else:
                # 使用monkey启动应用
                start_command = f"adb -s {device_serial} shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"

            # 执行启动命令
            result = subprocess.run(
                start_command.split(),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"应用包 {package_name} 在设备 {device_serial} 上启动成功")

                # 创建或更新实例状态
                instance_key = f"{device_serial}_{package_name}"
                self.app_instances[instance_key] = AppInstance(
                    package_name=package_name,
                    device_serial=device_serial,
                    state=AppState.RUNNING,
                    start_time=time.time()
                )

                return True
            else:
                logger.error(f"启动应用包 {package_name} 失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"启动应用包 {package_name} 时发生异常: {e}")
            return False

def main():
    """命令行入口点"""
    import argparse

    parser = argparse.ArgumentParser(description="应用生命周期管理器")
    parser.add_argument("--action", choices=["start", "stop", "restart", "status", "create-template"],
                       required=True, help="操作类型")
    parser.add_argument("--template", help="应用模板名称")
    parser.add_argument("--device", help="设备序列号")
    parser.add_argument("--template-file", help="模板文件路径（用于创建模板）")

    args = parser.parse_args()

    manager = AppLifecycleManager()

    try:
        if args.action == "create-template":
            if not args.template_file:
                print("创建模板需要指定 --template-file")
                return

            with open(args.template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)

            if manager.create_app_template(template_data):
                print(f"模板创建成功: {template_data['name']}")
            else:
                print("模板创建失败")

        elif args.action == "status":
            status = manager.get_app_status(args.template, args.device)
            print(json.dumps(status, indent=2, ensure_ascii=False))

        else:
            if not args.template:
                print(f"操作 {args.action} 需要指定 --template")
                return

            if not args.device:
                print(f"操作 {args.action} 需要指定 --device")
                return

            if args.action == "start":
                success = manager.start_app(args.template, args.device)
                print(f"启动应用: {'成功' if success else '失败'}")

            elif args.action == "stop":
                success = manager.stop_app(args.template, args.device)
                print(f"停止应用: {'成功' if success else '失败'}")

            elif args.action == "restart":
                success = manager.restart_app(args.template, args.device)
                print(f"重启应用: {'成功' if success else '失败'}")

    finally:
        manager.cleanup()


if __name__ == "__main__":
    main()
