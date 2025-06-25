# -*- coding: utf-8 -*-
"""
Action处理器模块
负责处理JSON脚本中的各种action操作
"""

import json
import time
import cv2
import numpy as np
import traceback
import queue
import os
from collections import namedtuple

# 尝试导入相关模块，如果失败则使用占位符
try:
    from .enhanced_input_handler import DeviceScriptReplayer
except (ImportError, AttributeError):
    try:
        from enhanced_input_handler import DeviceScriptReplayer
    except (ImportError, AttributeError):
        print("⚠️ 警告: 无法导入DeviceScriptReplayer，部分功能可能不可用")
        DeviceScriptReplayer = None

try:
    from .app_lifecycle_manager import AppLifecycleManager
except ImportError:
    try:
        from app_lifecycle_manager import AppLifecycleManager
    except ImportError:
        print("⚠️ 警告: 无法导入app_lifecycle_manager，部分功能可能不可用")
        AppLifecycleManager = None

try:
    from .app_permission_manager import integrate_with_app_launch
except ImportError:
    try:
        from app_permission_manager import integrate_with_app_launch
    except ImportError:
        print("⚠️ 警告: 无法导入app_permission_manager，部分功能可能不可用")
        integrate_with_app_launch = None

try:
    from .enhanced_device_preparation_manager import EnhancedDevicePreparationManager
except ImportError:
    try:
        from enhanced_device_preparation_manager import EnhancedDevicePreparationManager
    except ImportError:
        print("⚠️ 警告: 无法导入enhanced_device_preparation_manager，部分功能可能不可用")
        EnhancedDevicePreparationManager = None

# Import try_log_screen function for thumbnail generation
try:
    from replay_script import try_log_screen
except ImportError:
    try_log_screen = None

# Import the screenshot helper function
def get_device_screenshot(device):
    """
    获取设备截图的通用方法，兼容 adbutils.AdbDevice

    Args:
        device: adbutils.AdbDevice 对象

    Returns:
        PIL.Image 对象或 None
    """

    try:
        # 使用subprocess直接获取字节数据，避免字符编码问题
        import subprocess
        result = subprocess.run(
            f"adb -s {device.serial} exec-out screencap -p",
            shell=True,
            capture_output=True,
            timeout=10
        )

        if result.returncode == 0 and result.stdout:
            from PIL import Image
            import io
            # result.stdout 已经是字节数据，直接使用
            return Image.open(io.BytesIO(result.stdout))
        else:
            print("⚠️ 警告：screencap命令返回空数据或失败")
            return None
    except subprocess.TimeoutExpired:
        print("❌ 截图超时")
        return None
    except Exception as e:
        print(f"❌ ADB截图失败: {e}")

        # 尝试备用方法：转换为airtest设备
        try:
            from airtest.core.api import connect_device
            print("尝试使用airtest设备进行截图...")
            airtest_device = connect_device(f"Android:///{device.serial}")
            return airtest_device.snapshot()
        except Exception as e2:
            print(f"❌ Airtest截图也失败: {e2}")
            return None


class ActionContext:
    """Action执行上下文类 - 统一接口"""

    def __init__(self, device, input_handler=None, config=None, screenshot_dir=None, script_name=None,
                 device_name=None, log_dir=None, queues=None, step_idx=None):
        """
        初始化ActionContext - 支持多种初始化方式

        Args:
            device: 设备对象
            input_handler: 输入处理器（可选，懒加载）
            config: 配置信息
            screenshot_dir: 截图目录
            script_name: 脚本名称
            device_name: 设备名称（兼容旧接口）
            log_dir: 日志目录（兼容旧接口）
            queues: 队列字典（兼容旧接口）
            step_idx: 步骤索引（用于多设备模式下的简化日志）
        """
        self.device = device
        self.input_handler = input_handler
        self.config = config or {}
        self.screenshot_dir = screenshot_dir or log_dir
        self.script_name = script_name
        self.step_idx = step_idx

        # 兼容旧接口
        self.device_name = device_name
        self.log_dir = log_dir or screenshot_dir
        self.queues = queues or {}

    @property
    def screenshot_queue(self):
        return self.queues.get('screenshot_queue')

    @property
    def click_queue(self):
        return self.queues.get('click_queue')

    @property
    def action_queue(self):
        return self.queues.get('action_queue')


class ActionResult:
    """Action执行结果类 - 统一接口"""

    def __init__(self, success=True, message="", screenshot_path=None, details=None, should_stop=False,
                 executed=None, should_continue=None):
        """
        初始化ActionResult - 支持多种初始化方式

        Args:
            success: 操作是否成功
            message: 结果消息
            screenshot_path: 截图路径
            details: 附加详细信息
            should_stop: 是否应该停止执行
            executed: 是否实际执行了操作（兼容旧接口）
            should_continue: 是否应该继续执行（兼容旧接口）
        """
        self.success = success
        self.message = message
        self.screenshot_path = screenshot_path
        self.details = details or {}
        self.should_stop = should_stop

        # 兼容旧接口
        self.executed = executed if executed is not None else success
        self.should_continue = should_continue if should_continue is not None else (not should_stop)

    def to_tuple(self):
        """转换为元组格式，兼容现有代码"""
        return (self.success, self.executed, self.should_continue)

    @classmethod
    def from_tuple(cls, tuple_result):
        """从元组创建ActionResult对象"""
        if len(tuple_result) == 3:
            success, executed, should_continue = tuple_result
            return cls(
                success=success,
                executed=executed,
                should_continue=should_continue,
                message="操作完成" if success else "操作失败"
            )
        else:
            # 如果元组格式不对，返回默认的失败结果
            return cls(success=False, message="无效的元组格式")


class ActionProcessor:
    """Action处理器类 - 支持新旧接口"""

    def __init__(self, device, device_name=None, log_txt_path=None, detect_buttons_func=None, context=None):
        """
        初始化Action处理器 - 支持多种初始化方式

        新接口参数:
            device: 设备对象
            input_handler: 输入处理器（可选，懒加载）
            ai_service: AI服务（可选）
            config: 配置字典

        旧接口参数（兼容性）:
            device_name: 设备名称
            log_txt_path: 日志文件路径
            detect_buttons_func: AI检测按钮的函数
        """
        self.device = device
        self.input_handler = None
        self.ai_service = None
        self.config = {}        # 兼容旧接口
        self.device_name = device_name
        self.log_txt_path = log_txt_path
        self.detect_buttons = detect_buttons_func
        self.device_account = None

    def set_device_account(self, device_account):
        """设置设备账号信息"""
        self.device_account = device_account

    def _auto_allocate_device_account(self):
        """自动为设备分配账号（智能重试机制）"""
        try:
            # 尝试获取设备序列号
            device_serial = getattr(self.device, 'serial', None)
            if not device_serial:
                device_serial = self.device_name

            if not device_serial:
                print("⚠️ 无法获取设备序列号，无法自动分配账号")
                return False

            print(f"🔄 正在为设备 {device_serial} 自动分配账号...")

            # 导入账号管理器
            try:
                from account_manager import get_account_manager
                account_manager = get_account_manager()
            except ImportError as e:
                print(f"❌ 无法导入账号管理器: {e}")
                return False

            # 尝试分配账号
            device_account = account_manager.allocate_account(device_serial)

            if device_account:
                self.set_device_account(device_account)
                username, password = device_account
                print(f"✅ 自动为设备 {device_serial} 分配账号成功: {username}")
                return True
            else:
                print(f"❌ 无法为设备 {device_serial} 分配账号（账号池可能已满）")

                # 获取详细的分配状态信息
                try:
                    total_accounts = len(account_manager.accounts)
                    available_count = account_manager.get_available_accounts_count()
                    allocation_status = account_manager.get_allocation_status()

                    print(f"📊 账号池状态: 总账号数={total_accounts}, 可用={available_count}, 已分配={len(allocation_status)}")

                    if allocation_status:
                        print("📋 当前分配状态:")
                        for dev_serial, username in list(allocation_status.items())[:5]:  # 只显示前5个
                            print(f"   - {dev_serial}: {username}")
                        if len(allocation_status) > 5:
                            print(f"   ... 还有 {len(allocation_status) - 5} 个分配")

                except Exception as status_e:
                    print(f"⚠️ 获取账号状态信息失败: {status_e}")

                return False

        except Exception as e:
            print(f"❌ 自动账号分配过程中发生异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def process_action(self, step, context_or_step_idx, log_dir_or_context=None):
        """
        处理单个action步骤 - 支持新旧接口

        新接口:
            step: 步骤配置
            context: ActionContext对象

        旧接口（兼容性）:
            step: 步骤配置
            step_idx: 步骤索引
            log_dir: 日志目录

        Returns:
            ActionResult对象（新接口）或 tuple（旧接口兼容）
        """
        # 判断是新接口还是旧接口
        if isinstance(context_or_step_idx, ActionContext):
            # 新接口
            context = context_or_step_idx
            return self._process_action_new(step, context)
        else:
            # 旧接口兼容
            step_idx = context_or_step_idx
            log_dir = log_dir_or_context
            result = self._process_action_old(step, step_idx, log_dir)
            return result

    def _process_action_new(self, step, context):
        """使用新接口处理action"""
        step_action = step.get("action", "click")
        step_class = step.get("class", "")
        step_remark = step.get("remark", "")

        try:
            # 懒加载输入处理器
            if not self.input_handler and hasattr(context, 'device'):
                from enhanced_input_handler import DeviceScriptReplayer
                self.input_handler = DeviceScriptReplayer(context.device.serial)

            # 处理不同类型的步骤
            if step_class == "delay":
                return self._handle_delay_new(step, context)
            elif step_class == "device_preparation":
                return self._handle_device_preparation_new(step, context)
            elif step_class == "app_start":
                return self._handle_app_start_new(step, context)
            elif step_class == "app_stop":
                return self._handle_app_stop_new(step, context)
            elif step_class == "log":
                return self._handle_log_new(step, context)
            elif step_action == "wait_if_exists":
                return self._handle_wait_if_exists_new(step, context)
            elif step_action == "swipe":
                return self._handle_swipe_new(step, context)
            elif step_action == "input":
                return self._handle_input_new(step, context)
            elif step_action == "checkbox":
                return self._handle_checkbox_new(step, context)
            elif step_action == "auto_login":
                return self._handle_auto_login_new(step, context)
            elif step_action == "wait_for_disappearance":
                return self._handle_wait_for_disappearance_new(step, context)

            # 新的3个关键功能
            elif step_action == "wait_for_appearance":
                return self._handle_wait_for_appearance_new(step, context)
            elif step_action == "wait_for_stable":
                return self._handle_wait_for_stable_new(step, context)
            elif step_action == "retry_until_success":
                return self._handle_retry_until_success_new(step, context)

            # 废弃click_target，替换为click
            elif step_action == "click_target":
                print("⚠️ 警告: click_target已废弃，请使用click替代")
                # 将click_target转换为标准click处理
                converted_step = step.copy()
                converted_step["action"] = "click"
                if "target_selector" in converted_step:
                    target_selector = converted_step["target_selector"]
                    # 尝试从target_selector提取参数
                    if target_selector.get("type"):
                        converted_step["ui_type"] = target_selector["type"]
                        converted_step["detection_method"] = "ui"
                    del converted_step["target_selector"]
                return self._process_action_new(converted_step, context)
            else:
                # 默认处理：AI检测点击或备选点击
                if step_class == "unknown" and "relative_x" in step and "relative_y" in step:
                    return self._handle_fallback_click_new(step, context)
                elif step_class and step_class != "unknown":
                    return self._handle_ai_detection_click_new(step, context)
                else:
                    return ActionResult(success=False, message="无法处理的步骤类型")

        except Exception as e:
            return ActionResult(
                success=False,
                message=f"步骤执行异常: {e}",
                details={"exception": str(e), "step": step}
            )


    def _process_action_old(self, step, step_idx, log_dir):
        """使用旧接口处理action（兼容性）"""
        step_action = step.get("action", "click")
        step_class = step.get("class", "")

        # 处理特殊步骤类型
        if step_class == "delay":
            return self._handle_delay(step, step_idx, log_dir)
        elif step_class == "device_preparation":
            return self._handle_device_preparation(step, step_idx)
        elif step_class == "app_start":
            return self._handle_app_start(step, step_idx)
        elif step_class == "app_stop":
            return self._handle_app_stop(step, step_idx)
        elif step_class == "log":
            return self._handle_log(step, step_idx)

        # 处理新的3个关键功能
        elif step_action == "wait_for_appearance":
            return self._handle_wait_for_appearance(step, step_idx, log_dir)
        elif step_action == "wait_for_stable":
            return self._handle_wait_for_stable(step, step_idx, log_dir)
        elif step_action == "retry_until_success":
            return self._handle_retry_until_success(step, step_idx, log_dir)

        # 处理现有功能
        elif step_action == "wait_if_exists":
            return self._handle_wait_if_exists(step, step_idx, log_dir)
        elif step_action == "swipe":
            return self._handle_swipe(step, step_idx)
        elif step_action == "input":
            return self._handle_input(step, step_idx)
        elif step_action == "checkbox":
            return self._handle_checkbox(step, step_idx)
        elif step_action == "auto_login":
            return self._handle_auto_login(step, step_idx)
        elif step_action == "wait_for_disappearance":
            return self._handle_wait_for_disappearance(step, step_idx, log_dir)

        # 废弃click_target，替换为click
        elif step_action == "click_target":
            print("⚠️ 警告: click_target已废弃，请使用click替代")
            # 将click_target转换为标准click处理
            converted_step = step.copy()
            converted_step["action"] = "click"
            if "target_selector" in converted_step:
                target_selector = converted_step["target_selector"]
                # 尝试从target_selector提取参数
                if target_selector.get("type"):
                    converted_step["ui_type"] = target_selector["type"]
                    converted_step["detection_method"] = "ui"
                del converted_step["target_selector"]
            return self._process_action_old(converted_step, step_idx, log_dir)
        else:
            # 默认处理：尝试AI检测点击
            if step_class == "unknown" and "relative_x" in step and "relative_y" in step:
                return self._handle_fallback_click(step, step_idx, log_dir)
            elif step_class and step_class != "unknown":
                return self._handle_ai_detection_click(step, step_idx, log_dir)
            else:
                return False, False, False

    def _handle_delay(self, step, step_idx, log_dir=None):
        """处理延时步骤"""
        delay_seconds = step.get("params", {}).get("seconds", 1)
        step_remark = step.get("remark", "")

        print(f"延时 {delay_seconds} 秒: {step_remark}")
        time.sleep(delay_seconds)

        # 创建screen对象以支持报告截图显示
        screen_data = self._create_unified_screen_object(
            log_dir,
            pos_list=[],
            confidence=1.0,
            rect_info=[]
        )

        # 记录延时日志
        timestamp = time.time()
        delay_entry = {
            "tag": "function",
            "depth": 1,
            "time": timestamp,
            "data": {
                "name": "delay",
                "call_args": {"seconds": delay_seconds},
                "start_time": timestamp - delay_seconds,
                "ret": None,
                "end_time": timestamp,
                "desc": step_remark or f"延时 {delay_seconds} 秒",
                "title": f"#{step_idx+1} {step_remark or f'延时 {delay_seconds} 秒'}"
            }
        }

        # 添加screen对象到日志条目（如果可用）
        if screen_data:
            delay_entry["data"]["screen"] = screen_data

        self._write_log_entry(delay_entry)

        return True, True, True

    def _handle_device_preparation(self, step, step_idx):
        """处理设备预处理步骤"""
        params = step.get("params", {})
        step_remark = step.get("remark", "")

        # 设备预处理参数
        check_usb = params.get("check_usb", True)
        setup_wireless = params.get("setup_wireless", True)
        configure_permissions = params.get("configure_permissions", True)
        handle_screen_lock = params.get("handle_screen_lock", True)
        setup_input_method = params.get("setup_input_method", True)
        save_logs = params.get("save_logs", True)

        print(f"🔧 开始设备预处理: {step_remark}")
        print(f"📋 预处理参数: USB检查={check_usb}, 无线设置={setup_wireless}, 权限配置={configure_permissions}")
        print(f"屏幕锁定={handle_screen_lock}, 输入法设置={setup_input_method}, 保存日志={save_logs}")

        success = True

        try:
            device_manager = EnhancedDevicePreparationManager(save_logs=save_logs) if EnhancedDevicePreparationManager else None

            # 执行预处理步骤
            if check_usb and device_manager:
                print("🔍 执行USB连接检查...")
                if not device_manager._check_usb_connections():
                    print("❌ USB连接检查失败")
                    success = False

            if success and setup_wireless and device_manager:
                print("📶 配置无线连接...")
                if not device_manager._setup_wireless_connection(self.device.serial):
                    print("⚠️ 无线连接配置失败，但继续执行")

            if success and configure_permissions and device_manager:
                print("🔒 配置设备权限...")
                device_manager._fix_device_permissions(self.device.serial)

            if success and handle_screen_lock and device_manager:
                print("🔓 处理屏幕锁定...")
                print("⚠️ 警告: 正在使用旧版屏幕处理逻辑，建议切换到智能预处理")
                # 在旧版预处理中也尝试使用智能屏幕检测，避免误操作
                try:
                    from screen_state_detector import ScreenStateDetector
                    detector = ScreenStateDetector(self.device.serial)
                    screen_ready = detector.ensure_screen_ready()
                    if screen_ready:
                        print("✅ 智能屏幕检测成功，跳过旧版屏幕处理")
                    else:
                        print("⚠️ 智能屏幕检测失败，使用旧版屏幕处理")
                        device_manager._handle_screen_lock(self.device.serial)
                except ImportError:
                    print("⚠️ 无法导入智能屏幕检测，使用旧版屏幕处理")
                    device_manager._handle_screen_lock(self.device.serial)
                except Exception as e:
                    print(f"❌ 智能屏幕检测异常: {e}，使用旧版屏幕处理")
                    device_manager._handle_screen_lock(self.device.serial)

            if success and setup_input_method and device_manager:
                print("⌨️ 设置输入法...")
                if not device_manager._wake_up_yousite(self.device.serial):
                    print("⚠️ 输入法设置失败，但继续执行")

            print(f"✅ 设备预处理完成，结果: {'成功' if success else '失败'}")

        except Exception as e:
            print(f"❌ 设备预处理过程中出现错误: {e}")
            success = False

        # 记录设备预处理日志
        timestamp = time.time()
        device_prep_entry = {
            "tag": "function",
            "depth": 1,
            "time": timestamp,
            "data": {
                "name": "device_preparation",
                "call_args": {
                    "device_serial": self.device.serial,
                    "check_usb": check_usb,
                    "setup_wireless": setup_wireless,
                    "configure_permissions": configure_permissions,
                    "handle_screen_lock": handle_screen_lock,
                    "setup_input_method": setup_input_method,
                    "save_logs": save_logs
                },
                "start_time": timestamp,
                "ret": success,
                "end_time": timestamp + 1.0
            }
        }
        self._write_log_entry(device_prep_entry)

        return True, True, True

    def _handle_app_start(self, step, step_idx):
        """处理应用启动步骤"""
        print(f"处理应用启动步骤: {step_idx + 1}")
        params = step.get("params", {})
        step_remark = step.get("remark", "")
        app_name = params.get("app_name", "")
        package_name = params.get("package_name", "")

        # 扁平化权限配置参数
        handle_permission = params.get("handle_permission", True)
        permission_wait = params.get("permission_wait", 10)
        allow_permission = params.get("allow_permission", True)
        first_only = params.get("first_only", False)

        if not package_name:
            print(f"错误: app_start 步骤必须提供 package_name 参数")
            return True, False, True

        print(f"启动应用: {app_name or package_name} - {step_remark}")

        # 构建权限配置（转换为内部格式）
        permission_config = {
            "handle": handle_permission,
            "wait": permission_wait,
            "allow": allow_permission,
            "first_only": first_only
        }
        print(f"🔧 权限配置:permission_config={permission_config}")
        # print(f"🔧 权限配置:handle={handle_permission}, wait={permission_wait}s, allow={allow_permission}, first_only={first_only}")
        try:
            # 步骤1: 首先实际启动应用
            app_identifier = app_name or package_name

            print(f"🚀 正在启动应用: {app_identifier}")
            # 使用AppLifecycleManager来实际启动应用
            app_manager = AppLifecycleManager() if AppLifecycleManager else None
            print(f"应用管理器2: {app_manager}")
            # 现在所有信息都在脚本中提供，直接使用package_name启动
            if package_name and app_manager:
                print(f"🔍 使用脚本中提供的包名直接启动: {package_name}")
                startup_success = app_manager.force_start_by_package(package_name, self.device.serial)
            else:
                print(f"❌ 缺少package_name参数或AppLifecycleManager不可用，无法启动应用")
                startup_success = False
            print(f"应用启动命令执行: {'成功' if startup_success else '失败'}")
            # 步骤2: 如果应用启动成功，等待一下然后处理权限
            if startup_success:
                print("⏱️ 等待应用完全启动...")
                time.sleep(5)  # 增加等待时间到5秒，给应用更多时间加载权限弹窗

                print("🔍 开始权限弹窗检测和处理...")
                # 处理权限弹窗
                try:
                    if integrate_with_app_launch:
                        result = integrate_with_app_launch(
                            self.device.serial,
                            app_identifier,
                            auto_allow_permissions=True
                        )
                        print(f"权限处理结果: {result}")
                    else:
                        print("⚠️ integrate_with_app_launch不可用，跳过权限处理")
                        result = True
                except Exception as e:
                    print(f"权限处理发生异常: {e}")
                    print("假设无权限弹窗，继续执行")
                    result = True  # 异常时假设成功，避免阻塞

                # 最终结果是启动成功且权限处理成功
                final_result = startup_success and result
            else:
                print("❌ 应用启动失败，跳过权限处理")
                final_result = False

            print(f"应用启动整体结果: {final_result}")

            # 记录应用启动日志
            timestamp = time.time()
            app_start_entry = {
                "tag": "function",
                "depth": 1,
                "time": timestamp,
                "data": {
                    "name": "start_app",
                    "call_args": {
                        "app_name": app_identifier,
                        "handle_permission": handle_permission,
                        "permission_wait": permission_wait,
                        "allow_permission": allow_permission,
                        "first_only": first_only
                    },
                    "start_time": timestamp,
                    "ret": final_result,
                    "end_time": timestamp + 1
                }
            }
            self._write_log_entry(app_start_entry)

            # 修复: 根据实际结果返回正确的状态
            if final_result:
                print("✅ 应用启动和权限处理都成功")
                return True, True, True
            else:
                print("❌ 应用启动或权限处理失败")
                return True, False, True  # 步骤执行了但失败了

        except Exception as e:
            print(f"启动应用失败: {e}")
            return True, False, True  # 异常情况也应该标记为失败

    def _handle_app_stop(self, step, step_idx):
        """处理应用停止步骤"""
        params = step.get("params", {})
        step_remark = step.get("remark", "")
        app_name = params.get("app_name", "")
        package_name = params.get("package_name", "")

        print(f"停止应用 - {step_remark}")

        try:
            app_manager = AppLifecycleManager() if AppLifecycleManager else None
            print(f"应用管理器: {app_manager}")

            if package_name and app_manager:
                # 直接使用包名停止应用
                print(f"使用包名停止应用: {package_name}")
                result = app_manager.force_stop_by_package(package_name, self.device.serial)
                call_args = {"package_name": package_name}
            elif app_name and app_manager:
                # 使用模板名停止应用
                print(f"使用模板名停止应用: {app_name}")
                result = app_manager.stop_app(app_name, self.device.serial)
                call_args = {"app_name": app_name}
            else:
                print("错误: 未提供app_name或package_name参数，或AppLifecycleManager不可用")
                return True, False, True

            print(f"应用停止结果: {result}")

            # 记录应用停止日志
            timestamp = time.time()
            app_stop_entry = {
                "tag": "function",
                "depth": 1,
                "time": timestamp,
                "data": {
                    "name": "stop_app",
                    "call_args": call_args,
                    "start_time": timestamp,
                    "ret": result,
                    "end_time": timestamp + 1
                }
            }
            self._write_log_entry(app_stop_entry)
        except Exception as e:
            print(f"停止应用失败: {e}")

        return True, True, True

    def _handle_log(self, step, step_idx):
        """处理日志步骤"""
        log_message = step.get("params", {}).get("message", step.get("remark", ""))
        print(f"日志: {log_message}")

        # 记录日志条目
        timestamp = time.time()
        log_entry = {
            "tag": "function",
            "depth": 1,
            "time": timestamp,
            "data": {
                "name": "log",
                "call_args": {"msg": log_message},
                "start_time": timestamp,
                "ret": None,
                "end_time": timestamp
            }
        }
        self._write_log_entry(log_entry)

        return True, True, True

    def _handle_wait_if_exists(self, step, step_idx, log_dir):
        """处理条件等待步骤"""
        element_class = step.get("class", "")
        step_remark = step.get("remark", "")
        polling_interval = step.get("polling_interval", 5000) / 1000.0  # 转换为秒，默认5秒轮询
        max_duration = step.get("max_duration", 300)  # 默认300秒超时
        confidence = step.get("confidence", 0.8)  # 默认置信度

        print(f"\n🚀 [步骤 {step_idx+1}] 开始执行 wait_if_exists 操作")
        print(f"📋 元素类型: '{element_class}'")
        print(f"⚙️ 轮询间隔: {polling_interval}秒")
        print(f"⏰ 最大等待: {max_duration}秒")
        print(f"🎯 置信度: {confidence}")
        print(f"📝 备注: {step_remark}")
        print(f"⏱️ 步骤开始时间: {time.strftime('%H:%M:%S', time.localtime())}")

        wait_start_time = time.time()
        element_found = False
        wait_result = "not_found"  # not_found, disappeared, timeout

        try:
            # 第一步：检查元素是否存在
            print(f"\n🔍 [阶段1] 检查元素 '{element_class}' 是否存在...")            # 获取当前屏幕截图
            print(f"📱 正在获取屏幕截图...")
            screenshot = get_device_screenshot(self.device)
            if screenshot is None:
                print(f"❌ 警告: 无法获取屏幕截图，跳过条件等待")
                wait_result = "screenshot_failed"
            else:
                # Convert PIL Image to numpy array to access shape
                screenshot_array = np.array(screenshot)
                screenshot_cv = cv2.cvtColor(screenshot_array, cv2.COLOR_RGB2BGR)

                # 使用传递的检测函数进行AI检测
                if self.detect_buttons:
                    success, detection_result = self.detect_buttons(screenshot_cv, target_class=element_class)
                    print(f"🔍 检测结果: success={success}, detection_result={detection_result}")

                    if success and detection_result[0] is not None:
                        element_found = True
                        x, y, detected_class = detection_result
                        print(f"✅ [阶段1-成功] 元素 '{element_class}' 已找到!")
                        print(f"📍 位置: ({x:.1f}, {y:.1f})")
                        print(f"🏷️ 检测类别: {detected_class}")
                    else:
                        element_found = False
                        print(f"❌ [阶段1-失败] 未检测到元素 '{element_class}'")
                else:
                    print(f"⚠️ 检测函数不可用，跳过实际检测")
                    element_found = False

                if element_found:
                    print(f"✅ [阶段1] 元素 '{element_class}' 已存在，开始监控消失...")

                    # 第二步：监控元素消失
                    print(f"\n👁️ [阶段2] 监控元素消失...")
                    loop_count = 0

                    while element_found and (time.time() - wait_start_time) < max_duration:
                        loop_count += 1
                        print(f"🔄 [循环 {loop_count}] 等待元素消失... (已等待 {time.time() - wait_start_time:.1f}秒)")

                        time.sleep(polling_interval)                        # 重新检测
                        current_screenshot = get_device_screenshot(self.device)
                        if current_screenshot is not None:
                            print(f"🤖 [循环 {loop_count}] 重新检测元素...")
                            current_screenshot_array = np.array(current_screenshot)
                            current_screenshot_cv = cv2.cvtColor(current_screenshot_array, cv2.COLOR_RGB2BGR)                            # 重新检测元素是否仍然存在
                            if self.detect_buttons:
                                current_success, current_result = self.detect_buttons(current_screenshot_cv, target_class=element_class)
                                print(f"🔍 [循环 {loop_count}] 检测结果: success={current_success}")
                            else:
                                current_success = False  # 如果检测函数不可用，假设元素已消失

                            if not current_success:
                                wait_result = "disappeared"
                                elapsed_time = time.time() - wait_start_time
                                print(f"🎉 [循环 {loop_count}] 元素已消失! 总等待时间: {elapsed_time:.1f}秒")
                                break
                            else:
                                print(f"⏳ [循环 {loop_count}] 元素仍然存在，继续等待...")
                        else:
                            print(f"❌ [循环 {loop_count}] 无法获取屏幕截图")

                    if element_found and (time.time() - wait_start_time) >= max_duration:
                        wait_result = "timeout"
                        print(f"⏰ [阶段2] 等待超时: 元素在 {max_duration}秒后仍未消失")
                else:
                    print(f"ℹ️ [阶段1] 元素 '{element_class}' 不存在，无需等待")
                    wait_result = "not_found"

        except Exception as e:
            print(f"❌ wait_if_exists 执行过程中发生异常: {e}")
            traceback.print_exc()
            wait_result = "error"

        # 记录最终结果
        timestamp = time.time()
        total_wait_time = timestamp - wait_start_time

        print(f"\n🏁 [步骤 {step_idx+1}] wait_if_exists 执行完成")
        print(f"📊 最终结果:")
        print(f"   - 元素发现: {element_found}")
        print(f"   - 等待结果: {wait_result}")
        print(f"   - 总等待时间: {total_wait_time:.1f}秒")
        print(f"⏱️ 步骤结束时间: {time.strftime('%H:%M:%S', time.localtime())}")
        print(f"{'='*60}")        # 创建screen对象以支持报告截图显示
        screen_data = self._create_unified_screen_object(
            log_dir,
            pos_list=[],
            confidence=confidence,
            rect_info=[]
        )

        # 记录条件等待日志
        wait_entry = {
            "tag": "function",
            "depth": 1,
            "time": timestamp,
            "data": {
                "name": "wait_if_exists",
                "call_args": {
                    "element_class": element_class,
                    "polling_interval": polling_interval,
                    "max_duration": max_duration,
                    "confidence": confidence
                },
                "start_time": wait_start_time,
                "ret": {
                    "element_found": element_found,
                    "wait_result": wait_result,
                    "total_wait_time": total_wait_time
                },
                "end_time": timestamp,
                "desc": step_remark or "条件等待操作",
                "title": f"#{step_idx+1} {step_remark or '条件等待操作'}"
            }
        }

        # 添加screen对象到日志条目（如果可用）
        if screen_data:
            wait_entry["data"]["screen"] = screen_data

        self._write_log_entry(wait_entry)

        return True, True, True

    def _handle_wait_for_disappearance(self, step, step_idx, log_dir):
        """处理等待消失步骤"""
        element_class = step.get("class", "")
        step_remark = step.get("remark", "")
        polling_interval = step.get("polling_interval", 1000) / 1000.0  # 转换为秒，默认1秒轮询
        max_duration = step.get("max_duration", 30)  # 默认30秒超时
        confidence = step.get("confidence", 0.8)  # 默认置信度

        print(f"\n🚀 [步骤 {step_idx+1}] 开始执行 wait_for_disappearance 操作")
        print(f"📋 元素类型: '{element_class}'")
        print(f"⚙️ 轮询间隔: {polling_interval}秒")
        print(f"⏰ 最大等待: {max_duration}秒")
        print(f"🎯 置信度: {confidence}")
        print(f"📝 备注: {step_remark}")

        wait_start_time = time.time()
        element_disappeared = False
        wait_result = "timeout"  # timeout, disappeared, error

        try:
            loop_count = 0
            while (time.time() - wait_start_time) < max_duration:
                loop_count += 1
                print(f"🔄 [循环 {loop_count}] 检测元素是否已消失... (已等待 {time.time() - wait_start_time:.1f}秒)")

                # 获取当前屏幕截图
                screenshot = self.device.screenshot()
                if screenshot is None:
                    print(f"❌ [循环 {loop_count}] 无法获取屏幕截图")
                    time.sleep(polling_interval)
                    continue

                # 转换为OpenCV格式
                screenshot_array = np.array(screenshot)
                screenshot_cv = cv2.cvtColor(screenshot_array, cv2.COLOR_RGB2BGR)

                # 使用检测函数进行实际检测
                if self.detect_buttons:
                    success, detection_result = self.detect_buttons(screenshot_cv, target_class=element_class)
                    element_found = success and detection_result[0] is not None
                    print(f"🔍 [循环 {loop_count}] 检测结果: success={success}, 元素存在={element_found}")
                else:
                    # 如果检测函数不可用，假设元素已消失
                    element_found = False
                    print(f"⚠️ [循环 {loop_count}] 检测函数不可用，假设元素已消失")

                if not element_found:
                    element_disappeared = True
                    wait_result = "disappeared"
                    elapsed_time = time.time() - wait_start_time
                    print(f"🎉 [循环 {loop_count}] 元素已消失! 总等待时间: {elapsed_time:.1f}秒")
                    break
                else:
                    print(f"⏳ [循环 {loop_count}] 元素仍然存在，继续等待...")

                time.sleep(polling_interval)

        except Exception as e:
            print(f"❌ wait_for_disappearance 执行过程中发生异常: {e}")
            traceback.print_exc()
            wait_result = "error"

        # 记录最终结果
        timestamp = time.time()
        total_wait_time = timestamp - wait_start_time

        print(f"\n🏁 [步骤 {step_idx+1}] wait_for_disappearance 执行完成")
        print(f"📊 最终结果:")
        print(f"   - 元素已消失: {element_disappeared}")
        print(f"   - 等待结果: {wait_result}")
        print(f"   - 总等待时间: {total_wait_time:.1f}秒")
        print(f"{'='*60}")        # 创建screen对象以支持报告截图显示
        screen_data = self._create_unified_screen_object(
            log_dir,
            pos_list=[],
            confidence=confidence,
            rect_info=[]
        )

        # 记录条件等待日志
        wait_entry = {
            "tag": "function",
            "depth": 1,
            "time": timestamp,
            "data": {
                "name": "wait_for_disappearance",
                "call_args": {
                    "element_class": element_class,
                    "polling_interval": polling_interval,
                    "max_duration": max_duration,
                    "confidence": confidence
                },
                "start_time": wait_start_time,
                "ret": {
                    "element_disappeared": element_disappeared,
                    "wait_result": wait_result,
                    "total_wait_time": total_wait_time
                },
                "end_time": timestamp,
                "desc": step_remark or "等待消失操作",
                "title": f"#{step_idx+1} {step_remark or '等待消失操作'}"
            }
        }

        # 添加screen对象到日志条目（如果可用）
        if screen_data:
            wait_entry["data"]["screen"] = screen_data

        self._write_log_entry(wait_entry)

        return True, True, True

    def _handle_swipe(self, step, step_idx):
        """处理滑动步骤"""
        start_x = step.get("start_x")
        start_y = step.get("start_y")
        end_x = step.get("end_x")
        end_y = step.get("end_y")
        duration = step.get("duration", 300)
        step_remark = step.get("remark", "")

        if start_x is None or start_y is None or end_x is None or end_y is None:
            print(f"错误: swipe 步骤缺少必要的坐标参数")
            return True, False, True
        print(f"执行滑动操作: ({start_x}, {start_y}) -> ({end_x}, {end_y}), 持续{duration}ms: {step_remark}")

        # 获取截图目录
        log_dir = None
        if self.log_txt_path:
            log_dir = os.path.dirname(self.log_txt_path)

        # 执行ADB滑动命令
        self.device.shell(f"input swipe {int(start_x)} {int(start_y)} {int(end_x)} {int(end_y)} {int(duration)}")

        # 创建screen对象以支持报告截图显示
        screen_data = self._create_unified_screen_object(
            log_dir,
            pos_list=[[int(start_x), int(start_y)], [int(end_x), int(end_y)]],
            confidence=1.0,
            rect_info=[{
                "left": min(int(start_x), int(end_x)) - 20,
                "top": min(int(start_y), int(end_y)) - 20,
                "width": abs(int(end_x) - int(start_x)) + 40,
                "height": abs(int(end_y) - int(start_y)) + 40
            }]
        )

        # 记录滑动日志
        timestamp = time.time()
        swipe_entry = {
            "tag": "function",
            "depth": 1,
            "time": timestamp,
            "data": {
                "name": "swipe",
                "call_args": {
                    "start": [int(start_x), int(start_y)],
                    "end": [int(end_x), int(end_y)],
                    "duration": int(duration)
                },
                "start_time": timestamp,
                "ret": {
                    "start_pos": [int(start_x), int(start_y)],
                    "end_pos": [int(end_x), int(end_y)]
                },
                "end_time": timestamp + (duration / 1000.0),
                "desc": step_remark or "滑动操作",
                "title": f"#{step_idx+1} {step_remark or '滑动操作'}"
            }
        }

        # 添加screen对象到日志条目（如果可用）
        if screen_data:
            swipe_entry["data"]["screen"] = screen_data

        self._write_log_entry(swipe_entry)

        # 滑动后等待一段时间让UI响应
        time.sleep(duration / 1000.0 + 0.5)

        return True, True, True

    def _handle_input(self, step, step_idx):
        """处理文本输入步骤"""
        input_text = step.get("text", "")
        target_selector = step.get("target_selector", {})
        step_remark = step.get("remark", "")

        # 智能账号分配：如果需要账号参数但没有分配，尝试自动分配
        if ("${account:username}" in input_text or "${account:password}" in input_text):
            if not self.device_account:
                print("🔄 检测到需要账号参数但设备未分配账号，尝试自动分配...")
                self._auto_allocate_device_account()

        # 参数替换处理：${account:username} 和 ${account:password}
        if "${account:username}" in input_text:
            if self.device_account and len(self.device_account) >= 1:
                input_text = input_text.replace("${account:username}", self.device_account[0])
                print(f"✅ 替换用户名参数: {self.device_account[0]}")
            else:
                device_serial = getattr(self.device, 'serial', self.device_name)
                print(f"❌ 错误: 设备 {device_serial} 没有分配账号，无法替换用户名参数")
                print("💡 可能原因: 1)账号池已满 2)账号文件错误 3)账号管理器初始化失败")
                print("💡 解决建议: 检查 datasets/accounts_info/accounts.txt 或运行账号诊断工具")
                return True, False, True

        if "${account:password}" in input_text:
            if self.device_account and len(self.device_account) >= 2:
                input_text = input_text.replace("${account:password}", self.device_account[1])
                print(f"✅ 替换密码参数")
            else:
                device_serial = getattr(self.device, 'serial', self.device_name)
                print(f"❌ 错误: 设备 {device_serial} 没有分配账号，无法替换密码参数")
                print("💡 可能原因: 1)账号池已满 2)账号文件错误 3)账号管理器初始化失败")
                print("💡 解决建议: 检查 datasets/accounts_info/accounts.txt 或运行账号诊断工具")
                return True, False, True
            print(f"执行文本输入 - {step_remark}")
        try:
            # 获取截图目录
            log_dir = None
            if self.log_txt_path:
                log_dir = os.path.dirname(self.log_txt_path)

            # 初始化增强输入处理器
            if DeviceScriptReplayer:
                input_handler = DeviceScriptReplayer(self.device.serial)

                # 检查是否使用智能参数化选择器
                if target_selector.get('type'):
                    print(f"🤖 使用智能参数化输入: type={target_selector.get('type')}")
                    # 先查找目标输入框
                    target_element = input_handler.find_element_smart(target_selector)
                    if target_element:
                        print(f"✅ 找到目标输入框: {target_element.get('text', '')[:20]}...")
                        # 点击获取焦点后输入文本
                        if input_handler.tap_element(target_element):
                            success = input_handler.input_text_smart(input_text)
                        else:
                            print("❌ 点击输入框获取焦点失败")
                            success = False
                    else:
                        print("❌ 未找到匹配的输入框元素")
                        success = False
                else:
                    # 传统方式：使用增强版焦点检测
                    success = input_handler.input_text_with_focus_detection(input_text, target_selector)
            else:
                print("⚠️ DeviceScriptReplayer不可用，无法执行文本输入")
                return True, False, True

            if success:
                print(f"✅ 文本输入成功")

                # 创建screen对象以支持报告截图显示
                screen_data = self._create_unified_screen_object(
                    log_dir,
                    pos_list=[],
                    confidence=1.0,
                    rect_info=[]
                )

                # 记录输入操作日志
                timestamp = time.time()
                input_entry = {
                    "tag": "function",
                    "depth": 1,
                    "time": timestamp,
                    "data": {
                        "name": "input_text",
                        "call_args": {
                            "text": "***" if "${account:password}" in step.get("text", "") else input_text,
                            "target_selector": target_selector
                        },
                        "start_time": timestamp,
                        "ret": {"success": True},
                        "end_time": timestamp + 1,
                        "desc": step_remark or "文本输入操作",
                        "title": f"#{step_idx+1} {step_remark or '文本输入操作'}"
                    }
                }

                # 添加screen对象到日志条目（如果可用）
                if screen_data:
                    input_entry["data"]["screen"] = screen_data

                self._write_log_entry(input_entry)

                return True, True, True
            else:
                print(f"❌ 错误: 文本输入失败 - 无法找到合适的输入焦点")
                return True, False, True

        except Exception as e:
            print(f"❌ 错误: 文本输入过程中发生异常: {e}")
            traceback.print_exc()
            return True, False, True
    def _handle_checkbox(self, step, step_idx):
        """处理checkbox勾选步骤"""
        target_selector = step.get("target_selector", {})
        step_remark = step.get("remark", "")

        print(f"执行checkbox勾选操作 - {step_remark}")
        try:
            # 获取截图目录
            log_dir = None
            if self.log_txt_path:
                log_dir = os.path.dirname(self.log_txt_path)

            # 初始化增强输入处理器
            if DeviceScriptReplayer:
                input_handler = DeviceScriptReplayer(self.device.serial)

                # 获取UI结构
                xml_content = input_handler.get_ui_hierarchy()
                if xml_content:
                    elements = input_handler._parse_ui_xml(xml_content)

                    # 查找checkbox - 使用智能查找方法
                    if target_selector.get('type'):
                        # 新版：使用智能元素查找
                        checkbox = input_handler.find_element_smart(target_selector)
                    else:
                        # 传统方式：使用具体的CHECKBOX_PATTERNS
                        checkbox = input_handler.find_agreement_checkbox(elements, target_selector)

                    if checkbox:
                        success = input_handler.check_checkbox(checkbox)

                        if success:
                            print(f"✅ checkbox勾选成功")

                            # 创建screen对象以支持报告截图显示
                            screen_data = self._create_unified_screen_object(
                                log_dir,
                                pos_list=[],
                                confidence=1.0,
                                rect_info=[]
                            )

                        # 记录checkbox操作日志
                        timestamp = time.time()
                        checkbox_entry = {
                            "tag": "function",
                            "depth": 1,
                            "time": timestamp,
                            "data": {
                                "name": "check_checkbox",
                                "call_args": {
                                    "target_selector": target_selector
                                },
                                "start_time": timestamp,
                                "ret": {"success": True},
                                "end_time": timestamp + 0.5,
                                "desc": step_remark or "勾选checkbox操作",
                                "title": f"#{step_idx+1} {step_remark or '勾选checkbox操作'}"
                            }
                        }                        # 添加screen对象到日志条目（如果可用）
                        if screen_data:
                            checkbox_entry["data"]["screen"] = screen_data

                        self._write_log_entry(checkbox_entry)

                        return True, True, True
                    else:
                        print(f"❌ 错误: checkbox勾选失败")
                        return True, False, True
                else:
                    print(f"❌ 错误: 未找到checkbox元素")
                    return True, False, True
            else:
                print(f"❌ 错误: 无法获取UI结构")
                return True, False, True

        except Exception as e:
            print(f"❌ 错误: checkbox勾选过程中发生异常: {e}")
            traceback.print_exc()
            return True, False, True


    def _handle_click_target(self, step, step_idx=None):
        """处理通用目标点击步骤 - 已废弃，请使用click替代"""
        print("⚠️ 警告: _handle_click_target已废弃，请使用标准click操作替代")
        print("💡 建议: 将target_selector转换为detection_method + ui_type参数")

        # 转换为标准点击操作
        converted_step = step.copy()
        converted_step["action"] = "click"

        if "target_selector" in converted_step:
            target_selector = converted_step["target_selector"]
            # 尝试从target_selector提取参数
            if target_selector.get("type"):
                converted_step["ui_type"] = target_selector["type"]
                converted_step["detection_method"] = "ui"
            del converted_step["target_selector"]

        # 使用旧接口处理转换后的步骤
        log_dir = None
        if self.log_txt_path:
            log_dir = os.path.dirname(self.log_txt_path)

        return self._process_action_old(converted_step, step_idx or 0, log_dir)

    def _handle_auto_login(self, step, step_idx):
        """处理完整自动登录流程"""
        params = step.get("params", {})
        step_remark = step.get("remark", "")
        username = params.get("username", "")
        password = params.get("password", "")

        # 智能账号分配：如果需要账号参数但没有分配，尝试自动分配
        if ("${account:username}" in username or "${account:password}" in password):
            if not self.device_account:
                print("🔄 检测到需要账号参数但设备未分配账号，尝试自动分配...")
                self._auto_allocate_device_account()

        # 参数替换处理
        if "${account:username}" in username:
            if self.device_account and len(self.device_account) >= 1:
                username = username.replace("${account:username}", self.device_account[0])
                print(f"✅ 替换用户名参数: {self.device_account[0]}")
            else:
                device_serial = getattr(self.device, 'serial', self.device_name)
                print(f"❌ 错误: 设备 {device_serial} 没有分配账号，无法替换用户名参数")
                print("💡 可能原因: 1)账号池已满 2)账号文件错误 3)账号管理器初始化失败")
                print("💡 解决建议: 检查 datasets/accounts_info/accounts.txt 或运行账号诊断工具")
                return True, False, True

        if "${account:password}" in password:
            if self.device_account and len(self.device_account) >= 2:
                password = password.replace("${account:password}", self.device_account[1])
                print(f"✅ 替换密码参数")
            else:
                device_serial = getattr(self.device, 'serial', self.device_name)
                print(f"❌ 错误: 设备 {device_serial} 没有分配账号，无法替换密码参数")
                print("💡 可能原因: 1)账号池已满 2)账号文件错误 3)账号管理器初始化失败")
                print("💡 解决建议: 检查 datasets/accounts_info/accounts.txt 或运行账号诊断工具")
                return True, False, True
            print(f"执行完整自动登录流程 - {step_remark}")
        print(f"用户名: {username}")
        print(f"密码: {'*' * len(password)}")

        try:
            # 获取截图目录
            log_dir = None
            if self.log_txt_path:
                log_dir = os.path.dirname(self.log_txt_path)            # 初始化增强输入处理器
            if DeviceScriptReplayer:
                input_handler = DeviceScriptReplayer(self.device.serial)

                # 执行完整的自动登录流程
                success = input_handler.perform_auto_login(username, password)
            else:
                print("⚠️ DeviceScriptReplayer不可用，无法执行自动登录")
                return True, False, True

            if success:
                print(f"✅ 完整自动登录流程执行成功")

                # 创建screen对象以支持报告截图显示
                screen_data = self._create_unified_screen_object(
                    log_dir,
                    pos_list=[],
                    confidence=1.0,
                    rect_info=[]
                )

                # 记录自动登录操作日志
                timestamp = time.time()
                auto_login_entry = {
                    "tag": "function",
                    "depth": 1,
                    "time": timestamp,
                    "data": {
                        "name": "perform_auto_login",
                        "call_args": {
                            "username": username,
                            "password": "***隐藏密码***"
                        },
                        "start_time": timestamp,
                        "ret": {"success": True},
                        "end_time": timestamp + 3.0,
                        "desc": step_remark or "完整自动登录操作",
                        "title": f"#{step_idx+1} {step_remark or '完整自动登录操作'}"
                    }
                }

                # 添加screen对象到日志条目（如果可用）
                if screen_data:
                    auto_login_entry["data"]["screen"] = screen_data

                self._write_log_entry(auto_login_entry)

                return True, True, True
            else:
                print(f"❌ 错误: 完整自动登录流程执行失败")
                return True, False, True

        except Exception as e:
            print(f"❌ 错误: 自动登录过程中发生异常: {e}")
            traceback.print_exc()
            return True, False, True

    def _create_unified_screen_object(self, log_dir, pos_list=None, confidence=0.85, rect_info=None):
        """
        创建统一的screen对象，确保与Airtest报告格式兼容

        Args:
            log_dir: 日志目录
            pos_list: 位置列表，格式为 [[x, y], ...]
            confidence: 置信度
            rect_info: 矩形信息，格式为 [{"left": x, "top": y, "width": w, "height": h}, ...]

        Returns:
            dict: screen对象或None
        """
        try:
            if not log_dir:
                return None

            # 使用try_log_screen函数生成截图和缩略图
            if try_log_screen and hasattr(self, 'device'):
                screen_result = try_log_screen(self.device, log_dir)
                if screen_result:
                    # 构建完整的screen对象
                    screen_object = {
                        "src": screen_result["screen"],
                        "_filepath": screen_result["screen"],
                        "thumbnail": screen_result["screen"].replace(".jpg", "_small.jpg"),
                        "resolution": screen_result["resolution"],
                        "pos": pos_list or [],
                        "vector": [],
                        "confidence": confidence,
                        "rect": rect_info or []
                    }
                    return screen_object

            # 备用方案：直接使用get_device_screenshot
            screenshot = get_device_screenshot(self.device)
            if screenshot:
                # 转换为OpenCV格式
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

                # 生成时间戳文件名
                timestamp = time.time()
                screenshot_timestamp = int(timestamp * 1000)
                screenshot_filename = f"{screenshot_timestamp}.jpg"
                screenshot_path = os.path.join(log_dir, screenshot_filename)

                # 保存主截图
                cv2.imwrite(screenshot_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

                # 创建缩略图
                thumbnail_filename = f"{screenshot_timestamp}_small.jpg"
                thumbnail_path = os.path.join(log_dir, thumbnail_filename)
                small_frame = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)
                cv2.imwrite(thumbnail_path, small_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])

                # 获取分辨率
                height, width = frame.shape[:2]
                resolution = [width, height]

                # 构建screen对象
                screen_object = {
                    "src": screenshot_filename,
                    "_filepath": screenshot_filename,
                    "thumbnail": thumbnail_filename,
                    "resolution": resolution,
                    "pos": pos_list or [],
                    "vector": [],
                    "confidence": confidence,
                    "rect": rect_info or []
                }
                return screen_object

        except Exception as e:
            print(f"❌ 创建screen对象失败: {e}")

        return None

    # 新接口核心方法实现
    def _handle_ai_detection_click_new(self, step, context):
        """处理AI检测点击 - 新接口"""
        step_class = step.get("class", "")
        step_remark = step.get("remark", "")

        if not step_class or step_class == "unknown":
            return ActionResult(success=False, message="无效的检测类别")

        print(f"执行AI检测点击: {step_class}, 备注: {step_remark}")

        try:
            # 获取屏幕截图
            screenshot = get_device_screenshot(context.device)
            if screenshot is None:
                return ActionResult(success=False, message="无法获取设备屏幕截图")

            import cv2
            import numpy as np
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # 使用AI检测（如果可用）
            if self.detect_buttons:
                success, detection_result = self.detect_buttons(frame, target_class=step_class)

                if success and detection_result[0] is not None:
                    x, y, detected_class = detection_result

                    # 执行点击操作
                    context.device.shell(f"input tap {int(x)} {int(y)}")
                    print(f"✅ AI检测点击成功: {detected_class}，位置: ({int(x)}, {int(y)})")

                    # 生成带缩略图的截图日志
                    screen_data = None
                    if try_log_screen and hasattr(context, 'screenshot_dir') and context.screenshot_dir:
                        screen_result = try_log_screen(context.device, context.screenshot_dir)
                        if screen_result:
                            height, width = frame.shape[:2]
                            screen_data = {
                                "src": screen_result["screen"],
                                "_filepath": screen_result["screen"],
                                "thumbnail": screen_result["screen"].replace(".jpg", "_small.jpg"),
                                "resolution": screen_result["resolution"],
                                "pos": [[int(x), int(y)]],
                                "vector": [],
                                "confidence": 0.85,
                                "rect": [{
                                    "left": max(0, int(x) - 50),
                                    "top": max(0, int(y) - 50),
                                    "width": 100,
                                    "height": 100
                                }]
                            }

                    # 记录触摸操作日志
                    timestamp = time.time()
                    touch_entry = {
                        "tag": "function",
                        "depth": 1,
                        "time": timestamp,
                        "data": {
                            "name": "touch",
                            "call_args": {"v": [int(x), int(y)]},
                            "start_time": timestamp,
                            "ret": [int(x), int(y)],
                            "end_time": timestamp + 0.1,
                            "desc": step_remark or f"点击{detected_class}",
                            "title": f"#{step_remark or f'点击{detected_class}'}"
                        }
                    }

                    # 添加screenshot数据到entry中
                    if screen_data:
                        touch_entry["data"]["screen"] = screen_data

                    # 写入日志
                    self._write_log_entry(touch_entry)

                    return ActionResult(
                        success=True,
                        message="AI detection click completed",
                        details={
                            "detected_class": detected_class,
                            "coordinates": (int(x), int(y))
                        }
                    )
                else:
                    return ActionResult(
                        success=False,
                        message=f"AI检测未找到目标: {step_class}"
                    )
            else:
                return ActionResult(success=False, message="AI检测功能不可用")

        except Exception as e:
            return ActionResult(
                success=False,
                message=f"AI检测点击异常: {e}",
                details={"exception": str(e)}
            )

    def _handle_fallback_click_new(self, step, context):
        """处理备选点击 - 新接口"""
        step_remark = step.get("remark", "")

        if "relative_x" not in step or "relative_y" not in step:
            return ActionResult(success=False, message="备选步骤缺少相对坐标信息")

        try:
            # 获取屏幕截图以获取分辨率
            screenshot = get_device_screenshot(context.device)
            if screenshot is None:
                return ActionResult(success=False, message="无法获取屏幕截图")

            import cv2
            import numpy as np
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            height, width = frame.shape[:2]

            # 计算绝对坐标
            rel_x = float(step["relative_x"])
            rel_y = float(step["relative_y"])
            abs_x = int(width * rel_x)
            abs_y = int(height * rel_y)
            print(f"执行备选点击: 相对位置 ({rel_x}, {rel_y}) -> 绝对位置 ({abs_x}, {abs_y})")

            # 执行点击操作
            context.device.shell(f"input tap {abs_x} {abs_y}")

            # 生成带缩略图的截图日志
            screen_data = None
            if try_log_screen and hasattr(context, 'screenshot_dir') and context.screenshot_dir:
                screen_result = try_log_screen(context.device, context.screenshot_dir)
                if screen_result:
                    screen_data = {
                        "src": screen_result["screen"],
                        "_filepath": screen_result["screen"],
                        "thumbnail": screen_result["screen"].replace(".jpg", "_small.jpg"),
                        "resolution": screen_result["resolution"],
                        "pos": [[abs_x, abs_y]],
                        "vector": [],
                        "confidence": 1.0,
                        "rect": [{
                            "left": max(0, abs_x - 50),
                            "top": max(0, abs_y - 50),
                            "width": 100,
                            "height": 100
                        }]
                    }

            # 记录触摸操作日志
            if hasattr(context, 'log_txt_path'):
                import time
                timestamp = time.time()
                touch_entry = {
                    "tag": "function",
                    "depth": 1,
                    "time": timestamp,
                    "data": {
                        "name": "touch",
                        "call_args": {"v": [abs_x, abs_y]},
                        "start_time": timestamp,
                        "ret": [abs_x, abs_y],
                        "end_time": timestamp + 0.1,
                        "desc": step_remark or f"备选点击({rel_x:.3f}, {rel_y:.3f})",
                        "title": f"#{step_remark or f'备选点击({rel_x:.3f}, {rel_y:.3f})'}"
                    }
                }

                # 添加screenshot数据到entry中
                if screen_data:
                    touch_entry["data"]["screen"] = screen_data

                # 写入日志
                try:
                    log_entry_str = json.dumps(touch_entry, ensure_ascii=False, separators=(',', ':'))
                    with open(context.log_txt_path, "a", encoding="utf-8") as f:
                        f.write(log_entry_str + "\n")
                except Exception as log_e:
                    print(f"⚠️ 警告: 写入日志失败: {log_e}")

            return ActionResult(
                success=True,
                message="Fallback click completed",
                details={
                    "relative_coordinates": (rel_x, rel_y),
                    "absolute_coordinates": (abs_x, abs_y),
                    "has_screenshot": screen_data is not None
                }
            )

        except Exception as e:
            return ActionResult(
                success=False,
                message=f"备选点击异常: {e}",
                details={"exception": str(e)}
            )

    def _record_assert_failure_new(self, step, context, reason):
        """记录断言失败 - 新接口"""
        try:
            step_class = step.get("class", "")
            step_remark = step.get("remark", "")

            # 获取截图用于失败记录
            screenshot = get_device_screenshot(context.device)
            if screenshot:
                import cv2
                import numpy as np
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

                timestamp = time.time()
                screenshot_timestamp = int(timestamp * 1000)
                screenshot_filename = f"{screenshot_timestamp}_failure.jpg"
                screenshot_path = os.path.join(context.screenshot_dir, screenshot_filename)
                cv2.imwrite(screenshot_path, frame)

                return ActionResult(
                    success=False,
                    message="Assert failure recorded",
                    screenshot_path=screenshot_path,
                    details={
                        "reason": reason,
                        "step_class": step_class,
                        "step_remark": step_remark
                    }
                )
            else:
                return ActionResult(
                    success=False,
                    message="Assert failure recorded (no screenshot)",
                    details={"reason": reason}
                )

        except Exception as e:
            return ActionResult(
                success=False,
                message=f"记录断言失败时异常: {e}",
                details={"exception": str(e)}
            )

    # 简化的新接口方法实现
    def _handle_delay_new(self, step, context):
        """处理延时步骤 - 新接口"""
        delay_seconds = step.get("params", {}).get("seconds", 1)
        step_remark = step.get("remark", "")
        print(f"延时 {delay_seconds} 秒: {step_remark}")
        time.sleep(delay_seconds)
        return ActionResult(success=True, message=f"延时 {delay_seconds} 秒完成")

    def _handle_device_preparation_new(self, step, context):
        """设备预处理 - 新接口，集成屏幕状态检测，完全替代旧方法"""
        device_serial = getattr(self.device, 'serial', None)
        if not device_serial:
            print("⚠️ 无法获取设备序列号")
            return ActionResult(success=False, message="无法获取设备序列号")

        # 获取预处理参数
        params = step.get("params", {})
        check_usb = params.get("check_usb", True)
        setup_wireless = params.get("setup_wireless", False)
        configure_permissions = params.get("configure_permissions", True)
        handle_screen_lock = params.get("handle_screen_lock", True)
        setup_input_method = params.get("setup_input_method", True)
        save_logs = params.get("save_logs", False)

        print(f"🔍 开始智能设备预处理 - 设备 {device_serial}")
        print(f"📋 预处理参数: USB检查={check_usb}, 屏幕锁定={handle_screen_lock}, 输入法设置={setup_input_method}")

        # 预处理结果统计
        results = {
            "screen_ready": False,
            "usb_check": False,
            "permissions": False,
            "input_method": False
        }

        # 1. 智能屏幕状态检测和处理（最重要，必须先执行）
        if handle_screen_lock:
            try:
                from screen_state_detector import ScreenStateDetector
                print(f"🔍 检查设备 {device_serial} 屏幕状态...")
                detector = ScreenStateDetector(device_serial)
                screen_ready = detector.ensure_screen_ready()
                results["screen_ready"] = screen_ready
                if screen_ready:
                    print(f"✅ 设备 {device_serial} 屏幕已就绪")
                else:
                    print(f"⚠️ 设备 {device_serial} 屏幕准备失败")
            except ImportError:
                print("⚠️ 无法导入屏幕状态检测器")
                results["screen_ready"] = False
            except Exception as e:
                print(f"❌ 屏幕状态检测异常: {e}")
                results["screen_ready"] = False

        # 2. 执行其他预处理步骤（即使有步骤失败也继续执行，不回退到旧版）
        if check_usb:
            try:
                print("🔍 执行USB连接检查...")
                if EnhancedDevicePreparationManager:
                    device_manager = EnhancedDevicePreparationManager()
                    results["usb_check"] = device_manager._check_usb_connections()
                    if results["usb_check"]:
                        print("✅ USB连接检查通过")
                    else:
                        print("⚠️ USB连接检查失败")
                else:
                    print("⚠️ 设备预处理管理器不可用")
                    results["usb_check"] = False
            except Exception as e:
                print(f"❌ USB检查异常: {e}")
                results["usb_check"] = False

        if configure_permissions:
            try:
                print("🔐 配置设备权限...")
                if EnhancedDevicePreparationManager:
                    device_manager = EnhancedDevicePreparationManager()
                    device_manager._fix_device_permissions(device_serial)
                    results["permissions"] = True
                    print("✅ 设备权限配置完成")
                else:
                    print("⚠️ 设备预处理管理器不可用")
                    results["permissions"] = False
            except Exception as e:
                print(f"❌ 权限配置异常: {e}")
                results["permissions"] = False

        if setup_input_method:
            try:
                print("⌨️ 设置输入法...")
                if EnhancedDevicePreparationManager:
                    device_manager = EnhancedDevicePreparationManager()
                    input_result = device_manager._wake_up_yousite(device_serial)
                    results["input_method"] = input_result
                    if input_result:
                        print("✅ 输入法设置成功")
                    else:
                        print("⚠️ 输入法设置失败")
                else:
                    print("⚠️ 设备预处理管理器不可用")
                    results["input_method"] = False

            except Exception as e:
                print(f"❌ 输入法设置异常: {e}")
                results["input_method"] = False

        # 3. 评估总体结果（屏幕准备是最关键的）
        critical_success = results["screen_ready"] if handle_screen_lock else True
        overall_success = critical_success and (
            not check_usb or results["usb_check"]
        ) and (
            not configure_permissions or results["permissions"]
        ) and (
            not setup_input_method or results["input_method"]
        )

        print(f"📊 智能设备预处理结果统计:")
        print(f"   - 屏幕就绪: {'✅' if results['screen_ready'] else '❌'}")
        print(f"   - USB检查: {'✅' if results['usb_check'] else '❌'}")
        print(f"   - 权限配置: {'✅' if results['permissions'] else '❌'}")
        print(f"   - 输入法设置: {'✅' if results['input_method'] else '❌'}")
        print(f"✅ 智能设备预处理完成 - 设备 {device_serial}，总体结果: {'成功' if overall_success else '部分成功'}")

        # 4. 记录详细日志
        timestamp = time.time()
        device_prep_entry = {
            "tag": "function",
            "depth": 1,
            "time": timestamp,
            "data": {
                "name": "device_preparation_smart",
                "call_args": {
                    "device_serial": device_serial,
                    "check_usb": check_usb,
                    "setup_wireless": setup_wireless,
                    "configure_permissions": configure_permissions,
                    "handle_screen_lock": handle_screen_lock,
                    "setup_input_method": setup_input_method,
                    "save_logs": save_logs
                },
                "start_time": timestamp,
                "ret": {
                    "overall_success": overall_success,
                    "results": results
                },
                "end_time": timestamp + 1.0
            }
        }
        self._write_log_entry(device_prep_entry)

        # 5. 绝不回退到旧版预处理，避免二次屏幕操作
        return ActionResult(
            success=overall_success,
            message=f"智能设备预处理完成，关键步骤: {'成功' if critical_success else '失败'}",
            details=results
        )

    def _handle_app_start_new(self, step, context):
        """应用启动 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx参数
        step_idx = getattr(context, 'step_idx', 0)
        result = self._handle_app_start(step, step_idx)
        return ActionResult.from_tuple(result)

    def _handle_app_stop_new(self, step, context):
        """应用停止 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx参数
        step_idx = getattr(context, 'step_idx', 0)
        result = self._handle_app_stop(step, step_idx)
        return ActionResult.from_tuple(result)

    def _handle_log_new(self, step, context):
        """日志记录 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx参数
        step_idx = getattr(context, 'step_idx', 0)
        result = self._handle_log(step, step_idx)
        return ActionResult.from_tuple(result)

    def _handle_wait_if_exists_new(self, step, context):
        """条件等待 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx和log_dir参数
        step_idx = getattr(context, 'step_idx', 0)
        log_dir = getattr(context, 'screenshot_dir', None)
        result = self._handle_wait_if_exists(step, step_idx, log_dir)
        return ActionResult.from_tuple(result)

    def _handle_swipe_new(self, step, context):
        """滑动操作 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx参数
        step_idx = getattr(context, 'step_idx', 0)
        result = self._handle_swipe(step, step_idx)
        return ActionResult.from_tuple(result)

    def _handle_input_new(self, step, context):
        """文本输入 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx参数
        step_idx = getattr(context, 'step_idx', 0)
        result = self._handle_input(step, step_idx)
        return ActionResult.from_tuple(result)

    def _handle_checkbox_new(self, step, context):
        """勾选框操作 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx参数
        step_idx = getattr(context, 'step_idx', 0)
        result = self._handle_checkbox(step, step_idx)
        return ActionResult.from_tuple(result)
    def _handle_click_target_new(self, step, context):
        """目标点击 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx参数
        step_idx = getattr(context, 'step_idx', 0)
        result = self._handle_click_target(step, step_idx)
        return ActionResult.from_tuple(result)

    def _handle_auto_login_new(self, step, context):
        """自动登录 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx参数
        step_idx = getattr(context, 'step_idx', 0)
        result = self._handle_auto_login(step, step_idx)
        return ActionResult.from_tuple(result)

    def _handle_wait_for_disappearance_new(self, step, context):
        """等待消失 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx和log_dir参数
        step_idx = getattr(context, 'step_idx', 0)
        log_dir = getattr(context, 'screenshot_dir', None)
        result = self._handle_wait_for_disappearance(step, step_idx, log_dir)
        return ActionResult.from_tuple(result)

    # ===== 3个关键功能的新接口方法 =====

    def _handle_wait_for_appearance_new(self, step, context):
        """等待元素出现 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx和log_dir参数
        step_idx = getattr(context, 'step_idx', 0)
        log_dir = getattr(context, 'screenshot_dir', None)
        result = self._handle_wait_for_appearance(step, step_idx, log_dir)
        return ActionResult.from_tuple(result)

    def _handle_wait_for_stable_new(self, step, context):
        """等待界面稳定 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx和log_dir参数
        step_idx = getattr(context, 'step_idx', 0)
        log_dir = getattr(context, 'screenshot_dir', None)
        result = self._handle_wait_for_stable(step, step_idx, log_dir)
        return ActionResult.from_tuple(result)

    def _handle_retry_until_success_new(self, step, context):
        """重试直到成功 - 新接口"""
        # 使用旧接口的完整实现来确保真实操作
        # 将ActionContext转换为step_idx和log_dir参数
        step_idx = getattr(context, 'step_idx', 0)
        log_dir = getattr(context, 'screenshot_dir', None)
        result = self._handle_retry_until_success(step, step_idx, log_dir)
        return ActionResult.from_tuple(result)

    def _handle_wait_for_appearance(self, step, step_idx, log_dir):
        """处理等待元素出现步骤 - 等待指定元素从无到有的出现过程"""
        # 解析参数，支持新的参数名称
        yolo_class = step.get("yolo_class", step.get("class", ""))  # 向后兼容
        ui_type = step.get("ui_type", step.get("type", ""))  # 向后兼容
        detection_method = step.get("detection_method", "yolo" if yolo_class else "ui")

        step_remark = step.get("remark", "")
        timeout = step.get("timeout", 10)
        polling_interval = step.get("polling_interval", 1)
        confidence = step.get("confidence", 0.8)
        fail_on_timeout = step.get("fail_on_timeout", True)
        screenshot_on_timeout = step.get("screenshot_on_timeout", True)
        fallback_yolo_class = step.get("fallback_yolo_class", "")

        print(f"\n🚀 [步骤 {step_idx+1}] 开始执行 wait_for_appearance 操作")
        print(f"📋 检测方式: {detection_method}")
        if detection_method == "yolo" and yolo_class:
            print(f"🎯 AI类别: '{yolo_class}'")
        elif detection_method == "ui" and ui_type:
            print(f"🎯 UI类型: '{ui_type}'")
        print(f"⏰ 超时时间: {timeout}秒")
        print(f"🔄 轮询间隔: {polling_interval}秒")
        print(f"🎯 置信度: {confidence}")
        print(f"📝 备注: {step_remark}")

        wait_start_time = time.time()
        element_appeared = False
        wait_result = "not_appeared"
        detected_class = ""
        detection_result = None

        try:
            loop_count = 0
            while time.time() - wait_start_time < timeout:
                loop_count += 1
                print(f"\n🔍 [循环 {loop_count}] 检查元素是否出现...")

                # 根据detection_method选择检测方式
                if detection_method == "yolo" and yolo_class:
                    # AI检测方式
                    if self.detect_buttons:
                        success, detection_result = self.detect_buttons(yolo_class, confidence=confidence)
                        print(f"🔍 AI检测结果: success={success}, detection_result={detection_result}")

                        if success and detection_result[0] is not None:
                            element_appeared = True
                            x, y, detected_class = detection_result
                            wait_result = "appeared"
                            print(f"✅ [AI检测成功] 元素 '{yolo_class}' 已出现!")
                            print(f"📍 位置: ({x:.1f}, {y:.1f})")
                            print(f"🏷️ 检测类别: {detected_class}")
                            break
                    else:
                        print("⚠️ AI检测功能不可用")

                elif detection_method == "ui" and ui_type:
                    # UI检测方式
                    if DeviceScriptReplayer:
                        input_handler = DeviceScriptReplayer(self.device.serial)
                        target_selector = {"type": ui_type}
                        target_element = input_handler.find_element_smart(target_selector)

                        if target_element:
                            element_appeared = True
                            wait_result = "appeared"
                            bounds = target_element.get('bounds', '')
                            coords = input_handler._parse_bounds(bounds) if bounds else None
                            if coords:
                                x, y = coords
                                detection_result = (x, y, ui_type)
                            print(f"✅ [UI检测成功] 元素 '{ui_type}' 已出现!")
                            break
                    else:
                        print("⚠️ UI检测功能不可用")

                if element_appeared:
                    break

                print(f"⏳ [循环 {loop_count}] 元素尚未出现，等待 {polling_interval}秒后重试...")
                time.sleep(polling_interval)

            # 检查是否使用备选方案
            if not element_appeared and fallback_yolo_class and detection_method == "ui":
                print(f"\n🔄 UI检测失败，尝试备选AI检测: {fallback_yolo_class}")
                if self.detect_buttons:
                    success, detection_result = self.detect_buttons(fallback_yolo_class, confidence=confidence)
                    if success and detection_result[0] is not None:
                        element_appeared = True
                        x, y, detected_class = detection_result
                        wait_result = "appeared_fallback"
                        print(f"✅ [备选AI检测成功] 元素已出现!")

            total_wait_time = time.time() - wait_start_time

            if element_appeared:
                print(f"🎉 元素出现检测成功! 总等待时间: {total_wait_time:.1f}秒")
            else:
                wait_result = "timeout"
                print(f"⏰ 等待超时! 总等待时间: {total_wait_time:.1f}秒")

        except Exception as e:
            print(f"❌ 等待过程中发生异常: {e}")
            wait_result = "error"
            total_wait_time = time.time() - wait_start_time

        # 创建screen对象以支持报告截图显示
        pos_list = []
        if detection_result and len(detection_result) >= 2:
            pos_list = [[int(detection_result[0]), int(detection_result[1])]]

        screen_data = self._create_unified_screen_object(
            log_dir,
            pos_list=pos_list,
            confidence=confidence,
            rect_info=[]
        )

        # 记录等待结果日志
        timestamp = time.time()
        wait_entry = {
            "tag": "function",
            "depth": 1,
            "time": timestamp,
            "data": {
                "name": "wait_for_appearance",
                "call_args": {
                    "detection_method": detection_method,
                    "yolo_class": yolo_class,
                    "ui_type": ui_type,
                    "timeout": timeout,
                    "polling_interval": polling_interval,
                    "confidence": confidence
                },
                "start_time": wait_start_time,
                "ret": {
                    "element_appeared": element_appeared,
                    "wait_result": wait_result,
                    "total_wait_time": total_wait_time,
                    "detected_class": detected_class
                },
                "end_time": timestamp,
                "desc": step_remark or "等待元素出现操作",
                "title": f"#{step_idx+1} {step_remark or '等待元素出现操作'}"
            }
        }

        # 添加screen对象到日志条目
        if screen_data:
            wait_entry["data"]["screen"] = screen_data

        self._write_log_entry(wait_entry)

        # 根据配置决定返回结果
        if not element_appeared and fail_on_timeout:
            return True, False, True  # 执行了但失败
        else:
            return True, True, True   # 成功或忽略失败

    def _handle_wait_for_stable(self, step, step_idx, log_dir):
        """处理等待界面稳定步骤 - 等待界面连续N秒无变化，确保操作时机"""
        detection_method = step.get("detection_method", "yolo")
        step_remark = step.get("remark", "")
        duration = step.get("duration", 2)
        max_wait = step.get("max_wait", 10)
        check_structure = step.get("check_structure", True)
        check_positions = step.get("check_positions", True)
        tolerance = step.get("tolerance", 0.05)
        ignore_animations = step.get("ignore_animations", True)

        print(f"\n🚀 [步骤 {step_idx+1}] 开始执行 wait_for_stable 操作")
        print(f"📋 检测方式: {detection_method}")
        print(f"🎯 稳定持续时间: {duration}秒")
        print(f"⏰ 最大等待时间: {max_wait}秒")
        print(f"🔍 检查结构稳定: {check_structure}")
        print(f"📍 检查位置稳定: {check_positions}")
        print(f"📊 变化容忍度: {tolerance}")
        print(f"📝 备注: {step_remark}")

        wait_start_time = time.time()
        stable_start_time = None
        last_screenshot = None
        last_ui_structure = None
        is_stable = False
        stability_result = "not_stable"

        try:
            while time.time() - wait_start_time < max_wait:
                current_time = time.time()

                # 获取当前状态
                current_screenshot = None
                current_ui_structure = None

                if detection_method == "yolo":
                    # 使用截图比较检测稳定性
                    try:
                        import subprocess
                        screenshot_result = subprocess.run(
                            f"adb -s {self.device.serial} exec-out screencap -p",
                            shell=True, capture_output=True
                        )
                        if screenshot_result.returncode == 0:
                            import cv2
                            import numpy as np
                            # 将字节数据转换为图像
                            nparr = np.frombuffer(screenshot_result.stdout, np.uint8)
                            current_screenshot = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    except Exception as e:
                        print(f"⚠️ 截图获取失败: {e}")

                elif detection_method == "ui":
                    # 使用UI结构比较检测稳定性
                    if DeviceScriptReplayer:
                        input_handler = DeviceScriptReplayer(self.device.serial)
                        current_ui_structure = input_handler.get_ui_hierarchy()

                # 检查是否与上次状态相同
                is_same = False

                if detection_method == "yolo" and current_screenshot is not None:
                    if last_screenshot is not None:
                        # 计算图像差异
                        diff = cv2.absdiff(current_screenshot, last_screenshot)
                        diff_ratio = np.sum(diff) / (diff.shape[0] * diff.shape[1] * diff.shape[2] * 255)
                        is_same = diff_ratio < tolerance
                        print(f"🖼️ 截图差异比例: {diff_ratio:.4f} (阈值: {tolerance})")
                    else:
                        print("📸 获取第一张参考截图")
                    last_screenshot = current_screenshot.copy() if current_screenshot is not None else None

                elif detection_method == "ui" and current_ui_structure:
                    if last_ui_structure:
                        # 简单的字符串比较（可以优化为结构化比较）
                        is_same = current_ui_structure == last_ui_structure
                        print(f"🏗️ UI结构相同: {is_same}")
                    else:
                        print("🏗️ 获取第一个参考UI结构")
                    last_ui_structure = current_ui_structure

                # 更新稳定状态
                if is_same:
                    if stable_start_time is None:
                        stable_start_time = current_time
                        print(f"🟢 界面开始稳定...")

                    stable_duration = current_time - stable_start_time
                    print(f"⏱️ 已稳定 {stable_duration:.1f}/{duration}秒")

                    if stable_duration >= duration:
                        is_stable = True
                        stability_result = "stable"
                        print(f"✅ 界面已稳定 {duration}秒!")
                        break
                else:
                    if stable_start_time is not None:
                        print(f"🔄 界面发生变化，重新开始计时")
                    stable_start_time = None

                time.sleep(0.5)  # 检查间隔

            total_wait_time = time.time() - wait_start_time

            if not is_stable:
                stability_result = "timeout"
                print(f"⏰ 等待稳定超时! 总等待时间: {total_wait_time:.1f}秒")
            else:
                print(f"🎉 界面稳定检测成功! 总等待时间: {total_wait_time:.1f}秒")

        except Exception as e:
            print(f"❌ 稳定检测过程中发生异常: {e}")
            stability_result = "error"
            total_wait_time = time.time() - wait_start_time

        # 创建screen对象
        screen_data = self._create_unified_screen_object(
            log_dir,
            pos_list=[],
            confidence=1.0,
            rect_info=[]
        )

        # 记录稳定检测结果日志
        timestamp = time.time()
        stable_entry = {
            "tag": "function",
            "depth": 1,
            "time": timestamp,
            "data": {
                "name": "wait_for_stable",
                "call_args": {
                    "detection_method": detection_method,
                    "duration": duration,
                    "max_wait": max_wait,
                    "tolerance": tolerance
                },
                "start_time": wait_start_time,
                "ret": {
                    "is_stable": is_stable,
                    "stability_result": stability_result,
                    "total_wait_time": total_wait_time
                },
                "end_time": timestamp,
                "desc": step_remark or "等待界面稳定操作",
                "title": f"#{step_idx+1} {step_remark or '等待界面稳定操作'}"
            }
        }

        # 添加screen对象到日志条目
        if screen_data:
            stable_entry["data"]["screen"] = screen_data

        self._write_log_entry(stable_entry)

        return True, True, True

    def _handle_retry_until_success(self, step, step_idx, log_dir):
        """处理重试直到成功步骤 - 对任意操作进行重试，直到成功或达到最大次数"""
        # 解析参数
        detection_method = step.get("detection_method", "yolo")
        retry_action = step.get("retry_action", "click")
        yolo_class = step.get("yolo_class", step.get("class", ""))  # 向后兼容
        ui_type = step.get("ui_type", step.get("type", ""))  # 向后兼容
        text = step.get("text", "")
        step_remark = step.get("remark", "")

        max_retries = step.get("max_retries", 5)
        retry_strategy = step.get("retry_strategy", "fixed")
        retry_interval = step.get("retry_interval", 1)
        initial_delay = step.get("initial_delay", 1)
        max_delay = step.get("max_delay", 10)
        backoff_multiplier = step.get("backoff_multiplier", 2)
        verify_success = step.get("verify_success", False)
        stop_on_success = step.get("stop_on_success", True)

        print(f"\n🚀 [步骤 {step_idx+1}] 开始执行 retry_until_success 操作")
        print(f"📋 检测方式: {detection_method}")
        print(f"🎯 重试操作: {retry_action}")
        if detection_method == "yolo" and yolo_class:
            print(f"🎯 AI类别: '{yolo_class}'")
        elif detection_method == "ui" and ui_type:
            print(f"🎯 UI类型: '{ui_type}'")
        print(f"🔄 最大重试次数: {max_retries}")
        print(f"⏰ 重试策略: {retry_strategy}")
        print(f"📝 备注: {step_remark}")

        retry_start_time = time.time()
        success = False
        last_error = None
        retry_count = 0
        current_delay = initial_delay

        for attempt in range(max_retries + 1):  # +1 为第一次尝试
            retry_count = attempt
            print(f"\n🔄 [尝试 {attempt + 1}/{max_retries + 1}] 执行 {retry_action} 操作...")

            try:
                # 构造重试操作的step
                retry_step = {
                    "action": retry_action,
                    "detection_method": detection_method,
                    "yolo_class": yolo_class,
                    "ui_type": ui_type,
                    "text": text,
                    "remark": f"重试操作 {attempt + 1}: {step_remark}"
                }

                # 根据retry_action执行对应操作
                operation_success = False

                if retry_action == "click":
                    if detection_method == "yolo" and yolo_class:
                        # AI检测点击
                        if self.detect_buttons:
                            ai_success, detection_result = self.detect_buttons(yolo_class, confidence=0.8)
                            if ai_success and detection_result[0] is not None:
                                x, y, detected_class = detection_result
                                self.device.shell(f"input tap {int(x)} {int(y)}")
                                operation_success = True
                                print(f"✅ AI点击成功: ({x:.1f}, {y:.1f})")
                    elif detection_method == "ui" and ui_type:
                        # UI检测点击
                        if DeviceScriptReplayer:
                            input_handler = DeviceScriptReplayer(self.device.serial)
                            target_selector = {"type": ui_type}
                            operation_success = input_handler.perform_click_target_action(target_selector)
                            if operation_success:
                                print(f"✅ UI点击成功")

                elif retry_action == "input" and text:
                    # 文本输入操作
                    if detection_method == "ui" and ui_type:
                        if DeviceScriptReplayer:
                            input_handler = DeviceScriptReplayer(self.device.serial)
                            target_selector = {"type": ui_type}

                            # 先找到输入框
                            target_element = input_handler.find_element_smart(target_selector)
                            if target_element:
                                # 点击获取焦点
                                if input_handler.tap_element(target_element):
                                    time.sleep(0.5)
                                    # 输入文本
                                    escaped_text = text.replace(' ', '%s').replace("'", "\\'")
                                    self.device.shell(f"input text '{escaped_text}'")
                                    operation_success = True
                                    print(f"✅ 文本输入成功")

                # 验证操作成功（如果启用）
                if operation_success and verify_success:
                    print("🔍 验证操作结果...")
                    time.sleep(1)  # 等待UI响应
                    # 可以在这里添加更复杂的验证逻辑
                    # 目前简单假设操作成功

                if operation_success:
                    success = True
                    print(f"🎉 [尝试 {attempt + 1}] 操作成功!")
                    if stop_on_success:
                        break
                else:
                    print(f"❌ [尝试 {attempt + 1}] 操作失败")

            except Exception as e:
                print(f"❌ [尝试 {attempt + 1}] 操作异常: {e}")
                last_error = str(e)

            # 如果还有重试机会，计算延迟时间
            if attempt < max_retries and not (success and stop_on_success):
                if retry_strategy == "exponential":
                    delay = min(current_delay, max_delay)
                    current_delay *= backoff_multiplier
                elif retry_strategy == "adaptive":
                    # 自适应策略：前几次快速重试，后面延长间隔
                    if attempt < 2:
                        delay = 1
                    elif attempt < 4:
                        delay = 3
                    else:
                        delay = 5
                else:  # fixed
                    delay = retry_interval

                print(f"⏳ 等待 {delay}秒后重试...")
                time.sleep(delay)

        total_retry_time = time.time() - retry_start_time

        if success:
            print(f"🎉 重试操作最终成功! 尝试次数: {retry_count + 1}, 总时间: {total_retry_time:.1f}秒")
        else:
            print(f"❌ 重试操作最终失败! 尝试次数: {retry_count + 1}, 总时间: {total_retry_time:.1f}秒")

        # 创建screen对象
        screen_data = self._create_unified_screen_object(
            log_dir,
            pos_list=[],
            confidence=1.0,
            rect_info=[]
        )

        # 记录重试结果日志
        timestamp = time.time()
        retry_entry = {
            "tag": "function",
            "depth": 1,
            "time": timestamp,
            "data": {
                "name": "retry_until_success",
                "call_args": {
                    "detection_method": detection_method,
                    "retry_action": retry_action,
                    "yolo_class": yolo_class,
                    "ui_type": ui_type,
                    "max_retries": max_retries,
                    "retry_strategy": retry_strategy
                },
                "start_time": retry_start_time,
                "ret": {
                    "success": success,
                    "retry_count": retry_count + 1,
                    "total_retry_time": total_retry_time,
                    "last_error": last_error
                },
                "end_time": timestamp,
                "desc": step_remark or "重试直到成功操作",
                "title": f"#{step_idx+1} {step_remark or '重试直到成功操作'}"
            }
        }

        # 添加screen对象到日志条目
        if screen_data:
            retry_entry["data"]["screen"] = screen_data

        self._write_log_entry(retry_entry)

        return True, success, True

    def _write_log_entry(self, log_entry):
        """Write log entry to log file"""
        try:
            if self.log_txt_path and os.path.exists(os.path.dirname(self.log_txt_path)):
                with open(self.log_txt_path, "a", encoding="utf-8") as f:
                    log_entry_str = json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))
                    f.write(log_entry_str + "\n")
            else:
                print(f"⚠️ 警告: 无法写入日志文件 {self.log_txt_path}")
        except Exception as e:
            print(f"⚠️ 警告: 写入日志失败: {e}")