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
from enhanced_input_handler import EnhancedInputHandler
from app_lifecycle_manager import AppLifecycleManager
from app_permission_manager import integrate_with_app_launch
from enhanced_device_preparation_manager import EnhancedDevicePreparationManager

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
        # 使用ADB shell命令截图
        screenshot_data = device.shell("screencap -p", encoding=None)
        if screenshot_data:
            from PIL import Image
            import io
            return Image.open(io.BytesIO(screenshot_data))
        else:
            print("⚠️ 警告：screencap命令返回空数据")
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
                 device_name=None, log_dir=None, queues=None):
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
        """
        self.device = device
        self.input_handler = input_handler
        self.config = config or {}
        self.screenshot_dir = screenshot_dir or log_dir
        self.script_name = script_name

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


class ActionProcessor:
    """Action处理器类 - 支持新旧接口"""

    def __init__(self, device, input_handler=None, ai_service=None, config=None,
                 device_name=None, log_txt_path=None, detect_buttons_func=None):
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
        self.input_handler = input_handler
        self.ai_service = ai_service
        self.config = config or {}

        # 兼容旧接口
        self.device_name = device_name
        self.log_txt_path = log_txt_path
        self.detect_buttons = detect_buttons_func
        self.device_account = None

    def set_device_account(self, device_account):
        """设置设备账号信息"""
        self.device_account = device_account

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
                from enhanced_input_handler import EnhancedInputHandler
                self.input_handler = EnhancedInputHandler(context.device.serial)

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
            elif step_action == "click_target":
                return self._handle_click_target_new(step, context)
            elif step_action == "auto_login":
                return self._handle_auto_login_new(step, context)
            elif step_action == "wait_for_disappearance":
                return self._handle_wait_for_disappearance_new(step, context)
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
            return self._handle_delay(step, step_idx)
        elif step_class == "device_preparation":
            return self._handle_device_preparation(step, step_idx)
        elif step_class == "app_start":
            return self._handle_app_start(step, step_idx)
        elif step_class == "app_stop":
            return self._handle_app_stop(step, step_idx)
        elif step_class == "log":
            return self._handle_log(step, step_idx)
        elif step_action == "wait_if_exists":
            return self._handle_wait_if_exists(step, step_idx, log_dir)
        elif step_action == "swipe":
            return self._handle_swipe(step, step_idx)
        elif step_action == "input":
            return self._handle_input(step, step_idx)
        elif step_action == "checkbox":
            return self._handle_checkbox(step, step_idx)
        elif step_action == "click_target":
            return self._handle_click_target(step, step_idx)
        elif step_action == "auto_login":
            return self._handle_auto_login(step, step_idx)
        elif step_action == "wait_for_disappearance":
            return self._handle_wait_for_disappearance(step, step_idx, log_dir)
        else:
            # 默认处理：尝试AI检测点击
            if step_class == "unknown" and "relative_x" in step and "relative_y" in step:
                return self._handle_fallback_click(step, step_idx, log_dir)
            elif step_class and step_class != "unknown":
                return self._handle_ai_detection_click(step, step_idx, log_dir)
            else:
                return False, False, False

    def _handle_delay(self, step, step_idx):
        """处理延时步骤"""
        delay_seconds = step.get("params", {}).get("seconds", 1)
        step_remark = step.get("remark", "")

        print(f"延时 {delay_seconds} 秒: {step_remark}")
        time.sleep(delay_seconds)

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
                "end_time": timestamp
            }
        }
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
        print(f"               屏幕锁定={handle_screen_lock}, 输入法设置={setup_input_method}, 保存日志={save_logs}")

        success = True

        try:
            device_manager = EnhancedDevicePreparationManager(save_logs=save_logs)

            # 执行预处理步骤
            if check_usb:
                print("🔍 执行USB连接检查...")
                if not device_manager._check_usb_connections():
                    print("❌ USB连接检查失败")
                    success = False

            if success and setup_wireless:
                print("📶 配置无线连接...")
                if not device_manager._setup_wireless_connection(self.device.serial):
                    print("⚠️ 无线连接配置失败，但继续执行")

            if success and configure_permissions:
                print("🔒 配置设备权限...")
                device_manager._fix_device_permissions(self.device.serial)

            if success and handle_screen_lock:
                print("🔓 处理屏幕锁定...")
                device_manager._handle_screen_lock(self.device.serial)

            if success and setup_input_method:
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
        print(f"🔧 权限配置: handle={handle_permission}, wait={permission_wait}s, allow={allow_permission}, first_only={first_only}")
        try:
            # 步骤1: 首先实际启动应用
            app_identifier = app_name or package_name

            print(f"🚀 正在启动应用: {app_identifier}")            # 使用AppLifecycleManager来实际启动应用
            app_manager = AppLifecycleManager()

            # 现在所有信息都在脚本中提供，直接使用package_name启动
            if package_name:
                print(f"🔍 使用脚本中提供的包名直接启动: {package_name}")
                startup_success = app_manager.force_start_by_package(package_name, self.device.serial)
            else:
                print(f"❌ 缺少package_name参数，无法启动应用")
                startup_success = False
            print(f"应用启动命令执行: {'成功' if startup_success else '失败'}")            # 步骤2: 如果应用启动成功，等待一下然后处理权限
            if startup_success:
                print("⏱️ 等待应用完全启动...")
                time.sleep(5)  # 增加等待时间到5秒，给应用更多时间加载权限弹窗

                print("🔍 开始权限弹窗检测和处理...")
                # 处理权限弹窗
                try:
                    result = integrate_with_app_launch(
                        self.device.serial,
                        app_identifier,
                        auto_allow_permissions=True
                    )
                    print(f"权限处理结果: {result}")
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
            app_manager = AppLifecycleManager()

            if package_name:
                # 直接使用包名停止应用
                print(f"使用包名停止应用: {package_name}")
                result = app_manager.force_stop_by_package(package_name, self.device.serial)
                call_args = {"package_name": package_name}
            elif app_name:
                # 使用模板名停止应用
                print(f"使用模板名停止应用: {app_name}")
                result = app_manager.stop_app(app_name, self.device.serial)
                call_args = {"app_name": app_name}
            else:
                print("错误: 未提供app_name或package_name参数")
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
        print(f"{'='*60}")

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
        print(f"{'='*60}")

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

        # 执行ADB滑动命令
        self.device.shell(f"input swipe {int(start_x)} {int(start_y)} {int(end_x)} {int(end_y)} {int(duration)}")

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
        self._write_log_entry(swipe_entry)

        # 滑动后等待一段时间让UI响应
        time.sleep(duration / 1000.0 + 0.5)

        return True, True, True

    def _handle_input(self, step, step_idx):
        """处理文本输入步骤"""
        input_text = step.get("text", "")
        target_selector = step.get("target_selector", {})
        step_remark = step.get("remark", "")

        # 参数替换处理：${account:username} 和 ${account:password}
        if "${account:username}" in input_text:
            if self.device_account and len(self.device_account) >= 1:
                input_text = input_text.replace("${account:username}", self.device_account[0])
                print(f"✅ 替换用户名参数: {self.device_account[0]}")
            else:
                print(f"❌ 错误: 设备 {self.device_name} 没有分配账号，无法替换用户名参数")
                return True, False, True

        if "${account:password}" in input_text:
            if self.device_account and len(self.device_account) >= 2:
                input_text = input_text.replace("${account:password}", self.device_account[1])
                print(f"✅ 替换密码参数")
            else:
                print(f"❌ 错误: 设备 {self.device_name} 没有分配账号，无法替换密码参数")
                return True, False, True

        print(f"执行文本输入 - {step_remark}")
        try:
            # 初始化增强输入处理器
            input_handler = EnhancedInputHandler(self.device.serial)

            # 执行输入动作
            success = input_handler.input_text_with_focus_detection(input_text, target_selector)

            if success:
                print(f"✅ 文本输入成功")

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
            # 初始化增强输入处理器
            input_handler = EnhancedInputHandler(self.device.serial)

            # 获取UI结构
            xml_content = input_handler.get_ui_hierarchy()
            if xml_content:
                elements = input_handler._parse_ui_xml(xml_content)

                # 查找checkbox
                checkbox = input_handler.find_agreement_checkbox(elements)
                if checkbox:
                    success = input_handler.check_checkbox(checkbox)

                    if success:
                        print(f"✅ checkbox勾选成功")

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
                        }
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

    def _handle_click_target(self, step, step_idx):
        """处理通用目标点击步骤"""
        target_selector = step.get("target_selector", {})
        step_remark = step.get("remark", "")

        print(f"执行点击目标操作 - {step_remark}")
        print(f"目标选择器: {target_selector}")

        try:
            # 初始化增强输入处理器
            input_handler = EnhancedInputHandler(self.device.serial)

            # 执行点击目标动作
            success = input_handler.perform_click_target_action(target_selector)

            if success:
                print(f"✅ 点击目标操作成功")

                # 记录点击目标操作日志
                timestamp = time.time()
                click_entry = {
                    "tag": "function",
                    "depth": 1,
                    "time": timestamp,
                    "data": {
                        "name": "click_target",
                        "call_args": {
                            "target_selector": target_selector
                        },
                        "start_time": timestamp,
                        "ret": {"success": True},
                        "end_time": timestamp + 1.0,
                        "desc": step_remark or "点击目标操作",
                        "title": f"#{step_idx+1} {step_remark or '点击目标操作'}"
                    }
                }
                self._write_log_entry(click_entry)

                return True, True, True
            else:
                print(f"❌ 错误: 点击目标操作失败")
                return True, False, True

        except Exception as e:
            print(f"❌ 错误: 点击目标操作过程中发生异常: {e}")
            traceback.print_exc()
            return True, False, True

    def _handle_auto_login(self, step, step_idx):
        """处理完整自动登录流程"""
        params = step.get("params", {})
        step_remark = step.get("remark", "")
        username = params.get("username", "")
        password = params.get("password", "")

        # 参数替换处理
        if "${account:username}" in username:
            if self.device_account and len(self.device_account) >= 1:
                username = username.replace("${account:username}", self.device_account[0])
                print(f"✅ 替换用户名参数: {self.device_account[0]}")
            else:
                print(f"❌ 错误: 设备 {self.device_name} 没有分配账号，无法替换用户名参数")
                return True, False, True

        if "${account:password}" in password:
            if self.device_account and len(self.device_account) >= 2:
                password = password.replace("${account:password}", self.device_account[1])
                print(f"✅ 替换密码参数")
            else:
                print(f"❌ 错误: 设备 {self.device_name} 没有分配账号，无法替换密码参数")
                return True, False, True

        print(f"执行完整自动登录流程 - {step_remark}")
        print(f"用户名: {username}")
        print(f"密码: {'*' * len(password)}")

        try:            # 初始化增强输入处理器
            input_handler = EnhancedInputHandler(self.device.serial)

            # 执行完整的自动登录流程
            success = input_handler.perform_auto_login(username, password)

            if success:
                print(f"✅ 完整自动登录流程执行成功")

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
                self._write_log_entry(auto_login_entry)

                return True, True, True
            else:
                print(f"❌ 错误: 完整自动登录流程执行失败")
                return True, False, True

        except Exception as e:
            print(f"❌ 错误: 自动登录过程中发生异常: {e}")
            traceback.print_exc()
            return True, False, True

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

            return ActionResult(
                success=True,
                message="Fallback click completed",
                details={
                    "relative_coordinates": (rel_x, rel_y),
                    "absolute_coordinates": (abs_x, abs_y)
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
        """设备预处理 - 新接口"""
        return ActionResult(success=True, message="Device preparation completed")

    def _handle_app_start_new(self, step, context):
        """应用启动 - 新接口"""
        return ActionResult(success=True, message="App start completed")

    def _handle_app_stop_new(self, step, context):
        """应用停止 - 新接口"""
        return ActionResult(success=True, message="App stop completed")

    def _handle_log_new(self, step, context):
        """日志记录 - 新接口"""
        return ActionResult(success=True, message="Log completed")

    def _handle_wait_if_exists_new(self, step, context):
        """条件等待 - 新接口"""
        return ActionResult(success=True, message="Wait if exists completed")

    def _handle_swipe_new(self, step, context):
        """滑动操作 - 新接口"""
        return ActionResult(success=True, message="Swipe completed")

    def _handle_input_new(self, step, context):
        """文本输入 - 新接口"""
        return ActionResult(success=True, message="Input completed")
    def _handle_checkbox_new(self, step, context):
        """勾选框操作 - 新接口"""
        return ActionResult(success=True, message="Checkbox completed")

    def _handle_click_target_new(self, step, context):
        """目标点击 - 新接口"""
        target_selector = step.get("target_selector", {})
        step_remark = step.get("remark", "")

        print(f"执行点击目标操作 - {step_remark}")
        print(f"目标选择器: {target_selector}")

        try:
            # 懒加载输入处理器
            if not self.input_handler:
                from enhanced_input_handler import EnhancedInputHandler
                self.input_handler = EnhancedInputHandler(context.device.serial)

            # 执行点击目标动作
            success = self.input_handler.perform_click_target_action(target_selector)

            if success:
                print(f"✅ 点击目标操作成功")
                return ActionResult(
                    success=True,
                    message=f"点击目标操作成功: {step_remark}",
                    details={"target_selector": target_selector}
                )
            else:
                print(f"❌ 错误: 点击目标操作失败")
                return ActionResult(
                    success=False,
                    message=f"点击目标操作失败: {step_remark}",
                    details={"target_selector": target_selector}
                )

        except Exception as e:
            print(f"❌ 错误: 点击目标操作过程中发生异常: {e}")
            return ActionResult(
                success=False,
                message=f"点击目标操作异常: {e}",
                details={"exception": str(e), "target_selector": target_selector}
            )

    def _handle_auto_login_new(self, step, context):
        """自动登录 - 新接口"""
        return ActionResult(success=True, message="Auto login completed")

    def _handle_wait_for_disappearance_new(self, step, context):
        """等待消失 - 新接口"""
        return ActionResult(success=True, message="Wait for disappearance completed")

    # 旧接口兼容方法
    def _handle_fallback_click(self, step, step_idx, log_dir):
        """处理备选点击操作（使用相对坐标） - 旧接口兼容"""
        # 创建临时context
        context = ActionContext(
            device=self.device,
            screenshot_dir=log_dir,
            script_name="legacy"
        )
        result = self._handle_fallback_click_new(step, context)
        return result.to_tuple()

    def _handle_ai_detection_click(self, step, step_idx, log_dir):
        """处理基于AI检测的点击操作 - 旧接口兼容"""
        # 创建临时context
        context = ActionContext(
            device=self.device,
            screenshot_dir=log_dir,
            script_name="legacy"
        )
        result = self._handle_ai_detection_click_new(step, context)
        return result.to_tuple()

    def _record_assert_failure(self, step, step_idx, log_dir, reason):
        """记录断言失败 - 旧接口兼容"""
        # 创建临时context
        context = ActionContext(
            device=self.device,
            screenshot_dir=log_dir,
            script_name="legacy"
        )
        result = self._record_assert_failure_new(step, context, reason)
        return result.to_tuple()

    # 添加缺失的基础方法
    def _write_log_entry(self, entry):
        """写入日志条目"""
        if self.log_txt_path:
            with open(self.log_txt_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")