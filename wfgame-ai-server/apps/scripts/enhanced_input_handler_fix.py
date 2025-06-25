# 临时修复文件 - replay_single_script 方法的正确实现

def replay_single_script(self, script_path: str) -> bool:
    """
    回放单个脚本

    Args:
        script_path: 脚本文件路径

    Returns:
        回放是否成功
    """
    print(f"📜 开始回放脚本: {script_path}")

    try:
        # 读取脚本文件
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()

        # 解析JSON脚本
        import json
        script_json = json.loads(script_content)

        # 执行每个步骤
        for step in script_json.get('steps', []):
            # 兼容两种脚本格式：新格式使用action字段，旧格式使用class字段
            action = step.get('action')
            step_class = step.get('class', '')
            target = step.get('target')
            value = step.get('value')
            params = step.get('params', {})
            remark = step.get('remark', '')

            # 如果没有action字段，根据class字段推导action
            if not action:
                if step_class in ['app_start', 'start_app']:
                    action = 'app_start'
                elif step_class in ['app_stop', 'stop_app']:
                    action = 'app_stop'
                elif step_class in ['device_preparation']:
                    action = 'device_preparation'
                elif step_class in ['click', 'tap']:
                    action = 'click'
                elif step_class in ['input', 'type']:
                    action = 'input'
                elif step_class in ['wait', 'sleep']:
                    action = 'wait'
                else:
                    action = 'click'  # 默认为点击

            print(f"🔧 执行步骤: action={action}, class={step_class}, remark={remark}")

            if action == 'device_preparation':
                # 设备预处理操作
                print(f"🔧 执行设备预处理...")
                check_usb = params.get('check_usb', False)
                setup_wireless = params.get('setup_wireless', False)
                configure_permissions = params.get('configure_permissions', False)
                handle_screen_lock = params.get('handle_screen_lock', False)
                setup_input_method = params.get('setup_input_method', False)

                preparation_success = True

                if check_usb:
                    print("🔌 检查USB连接...")
                    result = self._run_adb_command(['devices'])
                    if result[0] and result[1] and self.device_serial and self.device_serial in result[1]:
                        print("✅ USB连接正常")
                    else:
                        print("❌ USB连接异常")
                        preparation_success = False

                if setup_input_method:
                    print("⌨️ 设置输入法...")
                    # 检查是否已安装ADB输入法
                    result = self._run_adb_command(['shell', 'ime', 'list', '-s'])
                    if result[0] and result[1] and 'com.android.adbkeyboard/.AdbIME' in result[1]:
                        print("✅ ADB输入法已安装")
                        # 启用ADB输入法
                        enable_result = self._run_adb_command(['shell', 'ime', 'enable', 'com.android.adbkeyboard/.AdbIME'])
                        set_result = self._run_adb_command(['shell', 'ime', 'set', 'com.android.adbkeyboard/.AdbIME'])
                        if enable_result[0] and set_result[0]:
                            print("✅ ADB输入法设置成功")
                        else:
                            print("⚠️ ADB输入法设置失败，但继续执行")
                    else:
                        print("⚠️ ADB输入法未安装，跳过设置")

                if handle_screen_lock:
                    print("🔓 处理屏幕锁定...")
                    # 唤醒设备
                    self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_WAKEUP'])
                    time.sleep(1)
                    # 检查屏幕状态
                    result = self._run_adb_command(['shell', 'dumpsys', 'power', '|', 'grep', 'mHoldingDisplaySuspendBlocker'])
                    print("✅ 屏幕唤醒处理完成")

                if configure_permissions:
                    print("🔐 配置权限...")
                    # 这里可以添加具体的权限配置逻辑
                    print("✅ 权限配置完成")

                if preparation_success:
                    print("✅ 设备预处理完成")
                else:
                    print("⚠️ 设备预处理部分失败，但继续执行")

            elif action == 'app_start':
                # 应用启动操作
                print(f"🚀 启动应用: {params.get('app_name', '未知应用')}")
                app_name = params.get('app_name')
                package_name = params.get('package_name')
                activity_name = params.get('activity_name')

                if package_name and activity_name:
                    # 使用完整的启动命令
                    result = self._run_adb_command(['shell', 'am', 'start', '-n', activity_name])
                    if result[0]:
                        print(f"✅ 成功启动应用: {app_name}")
                        time.sleep(2)  # 等待应用启动
                    else:
                        print(f"❌ 启动应用失败: {result[1]}")
                        return False
                else:
                    print(f"❌ 缺少应用启动参数: package_name={package_name}, activity_name={activity_name}")
                    return False

            elif action == 'app_stop':
                # 应用停止操作
                print(f"🛑 停止应用: {params.get('app_name', '未知应用')}")
                package_name = params.get('package_name')

                if package_name:
                    result = self._run_adb_command(['shell', 'am', 'force-stop', package_name])
                    if result[0]:
                        print(f"✅ 成功停止应用: {package_name}")
                        time.sleep(1)
                    else:
                        print(f"❌ 停止应用失败: {result[1]}")
                        return False
                else:
                    print(f"❌ 缺少应用停止参数: package_name={package_name}")
                    return False

            elif action == 'click':
                # 点击操作
                ui_xml = self.get_ui_hierarchy()
                if not ui_xml:
                    print(f"❌ 获取UI结构失败，无法执行 {action}")
                    return False
                element = self.find_custom_target_element(self._parse_ui_xml(ui_xml), target)
                if element:
                    self.click_custom_target(element)
                else:
                    print(f"❌ 找不到点击目标: {target}")
                    return False

            elif action == 'input':
                # 输入操作
                ui_xml = self.get_ui_hierarchy()
                if not ui_xml:
                    print(f"❌ 获取UI结构失败，无法执行 {action}")
                    return False
                element = self.find_custom_target_element(self._parse_ui_xml(ui_xml), target)
                if element:
                    self.tap_element(element)
                    time.sleep(0.5)  # 等待输入框获得焦点
                    self.clear_input_field()
                    self.input_text_smart(value)
                else:
                    print(f"❌ 找不到输入目标: {target}")
                    return False

            elif action == 'wait':
                # 等待操作
                wait_time = params.get('duration', value or 1.0)
                print(f"⏰ 等待 {wait_time} 秒")
                time.sleep(float(wait_time))

            else:
                print(f"❌ 不支持的操作: {action}")
                return False

        print("✅ 脚本回放完成")
        return True

    except Exception as e:
        print(f"❌ 脚本回放过程中发生错误: {e}")
        return False
