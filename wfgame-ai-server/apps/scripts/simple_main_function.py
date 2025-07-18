"""
Temporary file containing a clean main function for replay_script.py
"""

def main():
    """主函数 - 支持多设备并发回放和文件日志"""
    import sys
    import json
    import time
    import os
    from adbutils import adb

    # 加载YOLO模型用于AI检测
    print_realtime("🔄 正在加载YOLO模型...")
    model_loaded = load_yolo_model_for_detection()
    if model_loaded:
        print_realtime("✅ YOLO模型加载成功，AI检测功能可用")
    else:
        print_realtime("⚠️ YOLO模型加载失败，AI检测功能不可用")

    # 检查是否有--script参数
    if '--script' not in sys.argv:
        print_realtime("❌ 错误: 必须指定 --script 参数")
        print_realtime("用法示例:")
        print_realtime("  python replay_script.py --script testcase/scene1.json")
        print_realtime("  python replay_script.py --show-screens --script testcase/scene1.json --loop-count 1")
        print_realtime("  python replay_script.py --script testcase/scene1.json --loop-count 1 --script testcase/scene2.json --max-duration 30")
        print_realtime("  python replay_script.py --log-dir /path/to/logs --device serial123 --script testcase/scene1.json")
        return

    # 解析脚本参数和多设备参数
    scripts, multi_device_params = parse_script_arguments(sys.argv[1:])

    if not scripts:
        print_realtime("❌ 未找到有效的脚本参数")
        return

    # 提取多设备参数
    log_dir = multi_device_params.get('log_dir')
    device_serial = multi_device_params.get('device_serial')
    account_user = multi_device_params.get('account_user')
    account_pass = multi_device_params.get('account_pass')

    # 如果指定了log_dir和device_serial，则启用文件日志模式
    file_logger = None
    original_stdout = None
    original_stderr = None

    if log_dir and device_serial:
        try:
            file_logger = FileLogger(log_dir, device_serial)
            file_logger.log(f"🎬 启动设备 {device_serial} 的脚本回放")
            file_logger.log(f"📝 将执行 {len(scripts)} 个脚本")

            # 重定向stdout和stderr到文件日志
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            sys.stdout = SafeOutputWrapper(file_logger, "stdout")
            sys.stderr = SafeOutputWrapper(file_logger, "stderr")

            print_realtime(f"✅ 文件日志已启用: {log_dir}/{device_serial}.log")
        except Exception as e:
            print_realtime(f"⚠️ 文件日志启用失败: {e}")

    exit_code = 0
    report_url = ""

    try:
        print_realtime("🎬 启动精简版回放脚本")
        print_realtime(f"📝 将执行 {len(scripts)} 个脚本:")
        for i, script in enumerate(scripts, 1):
            print_realtime(f"  {i}. {script['path']} (循环:{script['loop_count']}, 最大时长:{script['max_duration']}s)")

        # 如果有账号信息，记录日志
        if account_user:
            print_realtime(f"👤 使用账号: {account_user}")

        # 验证脚本文件存在
        missing_scripts = []
        for script in scripts:
            if not os.path.exists(script['path']):
                missing_scripts.append(script['path'])

        if missing_scripts:
            print_realtime("❌ 以下脚本文件不存在:")
            for path in missing_scripts:
                print_realtime(f"  - {path}")
            exit_code = -1
        else:
            # 获取连接的设备
            try:
                devices = adb.device_list()
                if not devices:
                    print_realtime("❌ 未找到连接的设备")
                    exit_code = -1
                else:
                    print_realtime(f"📱 找到 {len(devices)} 个设备")

                    # 如果指定了特定设备，检查是否存在
                    if device_serial:
                        device_found = any(d.serial == device_serial for d in devices)
                        if not device_found:
                            print_realtime(f"❌ 指定的设备 {device_serial} 未找到")
                            exit_code = -1
                        else:
                            print_realtime(f"✅ 使用指定设备: {device_serial}")
                            # 过滤设备列表，只使用指定设备
                            devices = [d for d in devices if d.serial == device_serial]

                    if exit_code == 0:
                        # 最终检查模型状态
                        global model
                        if model is not None:
                            print_realtime("✅ 模型状态检查通过，AI检测功能可用")
                        else:
                            print_realtime("⚠️ 模型状态检查失败，将使用备用检测模式")

                        # 执行脚本回放的核心逻辑
                        processed_device_names = []
                        current_execution_device_dirs = []

                        # 为每个设备执行脚本
                        for device in devices:
                            device_name = device.serial
                            processed_device_names.append(device_name)

                            try:
                                print_realtime(f"🎯 开始处理设备: {device_name}")

                                # 创建设备报告目录
                                device_report_dir = None
                                if not log_dir:  # 如果没有指定日志目录，创建默认目录
                                    try:
                                        global REPORT_MANAGER
                                        if REPORT_MANAGER:
                                            clean_device_name = "".join(c for c in device_name if c.isalnum() or c in ('-', '_', '.'))
                                            if not clean_device_name:
                                                clean_device_name = f"device_{abs(hash(device_name)) % 10000}"

                                            device_report_dir = REPORT_MANAGER.create_device_directory(clean_device_name)
                                            current_execution_device_dirs.append(device_report_dir)
                                            print_realtime(f"📁 设备报告目录: {device_report_dir}")
                                        else:
                                            # 回退到旧的目录创建方式
                                            clean_device_name = "".join(c for c in device_name if c.isalnum() or c in ('-', '_', '.'))
                                            if not clean_device_name:
                                                clean_device_name = f"device_{abs(hash(device_name)) % 10000}"
                                            device_report_dir = os.path.join(DEVICE_REPORTS_DIR, clean_device_name)
                                            os.makedirs(device_report_dir, exist_ok=True)
                                            current_execution_device_dirs.append(device_report_dir)
                                            print_realtime(f"📁 设备报告目录: {device_report_dir}")
                                    except Exception as e:
                                        print_realtime(f"⚠️ 设备报告目录创建失败: {e}")

                                # 执行所有脚本
                                device_success = True
                                for script_index, script in enumerate(scripts, 1):
                                    script_path = script['path']
                                    loop_count = script['loop_count']
                                    max_duration = script['max_duration']

                                    print_realtime(f"📜 设备 {device_name} 执行脚本 {script_index}/{len(scripts)}: {script_path}")

                                    # 循环执行脚本
                                    for loop in range(loop_count):
                                        print_realtime(f"🔄 第 {loop + 1}/{loop_count} 次循环")

                                        try:
                                            # 使用airtest连接设备
                                            from airtest.core.api import auto_setup
                                            auto_setup(__file__, devices=[f"android:///{device_name}"])

                                            # 设置置信度阈值
                                            try:
                                                confidence_threshold = get_confidence_threshold_from_config()
                                                from airtest.core.settings import Settings as ST
                                                ST.THRESHOLD = confidence_threshold
                                                print_realtime(f"🎯 AI检测置信度设置为: {confidence_threshold}")
                                            except Exception as e:
                                                print_realtime(f"⚠️ 置信度配置失败，使用默认值: {e}")

                                            # 读取并执行脚本
                                            start_time = time.time()
                                            script_success = True

                                            try:
                                                with open(script_path, 'r', encoding='utf-8') as f:
                                                    script_data = json.load(f)

                                                actions = script_data.get('actions', [])
                                                print_realtime(f"📋 脚本包含 {len(actions)} 个动作")

                                                # 执行动作序列
                                                for action_index, action in enumerate(actions, 1):
                                                    elapsed_time = time.time() - start_time
                                                    if max_duration > 0 and elapsed_time >= max_duration:
                                                        print_realtime(f"⏰ 达到最大执行时间 {max_duration}s，停止执行")
                                                        break

                                                    print_realtime(f"🎬 执行动作 {action_index}/{len(actions)}: {action.get('type', 'unknown')}")

                                                    # 简化版动作处理 - 直接使用airtest基础功能
                                                    try:
                                                        action_type = action.get('type', '')

                                                        if action_type == 'tap':
                                                            # 点击动作
                                                            coords = action.get('coordinates', [])
                                                            if len(coords) >= 2:
                                                                from airtest.core.api import touch
                                                                touch((coords[0], coords[1]))
                                                                print_realtime(f"✅ 点击坐标: {coords[0]}, {coords[1]}")
                                                                time.sleep(0.5)

                                                        elif action_type == 'swipe':
                                                            # 滑动动作
                                                            start_coords = action.get('start_coordinates', [])
                                                            end_coords = action.get('end_coordinates', [])
                                                            if len(start_coords) >= 2 and len(end_coords) >= 2:
                                                                from airtest.core.api import swipe
                                                                swipe((start_coords[0], start_coords[1]), (end_coords[0], end_coords[1]))
                                                                print_realtime(f"✅ 滑动: {start_coords} -> {end_coords}")
                                                                time.sleep(0.5)

                                                        elif action_type == 'wait':
                                                            # 等待动作
                                                            duration = action.get('duration', 1)
                                                            print_realtime(f"⏰ 等待 {duration} 秒")
                                                            time.sleep(duration)

                                                        elif action_type == 'keyevent':
                                                            # 按键动作
                                                            key = action.get('key', '')
                                                            if key:
                                                                from airtest.core.api import keyevent
                                                                keyevent(key)
                                                                print_realtime(f"✅ 按键: {key}")
                                                                time.sleep(0.5)

                                                        else:
                                                            print_realtime(f"⚠️ 不支持的动作类型: {action_type}")

                                                    except Exception as e:
                                                        print_realtime(f"❌ 动作执行异常: {e}")
                                                        script_success = False

                                                if script_success:
                                                    print_realtime(f"✅ 脚本执行成功 (循环 {loop + 1})")
                                                else:
                                                    print_realtime(f"❌ 脚本执行失败 (循环 {loop + 1})")
                                                    device_success = False

                                            except Exception as e:
                                                print_realtime(f"❌ 脚本执行异常: {e}")
                                                script_success = False
                                                device_success = False

                                        except Exception as e:
                                            print_realtime(f"❌ 设备连接或脚本执行失败: {e}")
                                            device_success = False

                                # 生成设备报告
                                if device_report_dir:
                                    try:
                                        print_realtime(f"📊 生成设备 {device_name} 的报告...")

                                        # 创建简单的设备报告
                                        device_report_data = {
                                            "device": device_name,
                                            "scripts": [{"path": s['path'], "loop_count": s['loop_count'], "max_duration": s['max_duration']} for s in scripts],
                                            "success": device_success,
                                            "timestamp": time.time(),
                                            "execution_time": time.time() - start_time if 'start_time' in locals() else 0
                                        }

                                        report_file = os.path.join(device_report_dir, "report.json")
                                        with open(report_file, 'w', encoding='utf-8') as f:
                                            json.dump(device_report_data, f, indent=2, ensure_ascii=False)

                                        print_realtime(f"✅ 设备报告已生成: {report_file}")

                                    except Exception as e:
                                        print_realtime(f"⚠️ 设备报告生成失败: {e}")

                                if not device_success:
                                    exit_code = -1
                                    print_realtime(f"❌ 设备 {device_name} 执行失败")
                                else:
                                    print_realtime(f"✅ 设备 {device_name} 执行成功")

                            except Exception as e:
                                print_realtime(f"❌ 设备 {device_name} 处理异常: {e}")
                                exit_code = -1

                        # 生成汇总报告
                        try:
                            if current_execution_device_dirs and REPORT_GENERATOR:
                                print_realtime("📊 生成汇总报告...")
                                summary_report_path = REPORT_GENERATOR.generate_summary_report(
                                    processed_device_names,
                                    current_execution_device_dirs
                                )
                                if summary_report_path:
                                    report_url = summary_report_path
                                    print_realtime(f"✅ 汇总报告已生成: {summary_report_path}")
                                else:
                                    print_realtime("⚠️ 汇总报告生成失败")

                        except Exception as e:
                            print_realtime(f"⚠️ 汇总报告生成失败: {e}")

                        print_realtime("✅ 脚本回放执行完成")

            except Exception as e:
                print_realtime(f"❌ 设备列表获取失败: {e}")
                exit_code = -1

    except Exception as e:
        print_realtime(f"❌ 脚本回放过程出错: {e}")
        exit_code = -1

    finally:
        # 资源清理和结果写入
        if file_logger and log_dir and device_serial:
            try:
                # 恢复原始输出流
                if original_stdout:
                    sys.stdout = original_stdout
                if original_stderr:
                    sys.stderr = original_stderr

                # 写入结果文件
                result_data = {
                    "exit_code": exit_code,
                    "report_url": report_url,
                    "device": device_serial,
                    "timestamp": time.time()
                }
                write_result(log_dir, device_serial, result_data)
                file_logger.log(f"✅ 结果已写入: {result_data}")
            except Exception as e:
                print_realtime(f"⚠️ 结果写入失败: {e}")

        print_realtime("🏁 脚本回放任务结束")
