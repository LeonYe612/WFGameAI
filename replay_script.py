from airtest.core.api import touch, exists, snapshot, set_logdir, connect_device, log
from airtest.report.report import LogToHtml
import cv2
import numpy as np
from ultralytics import YOLO
import json
import time
import os
from threading import Thread, Event
import queue
import sys
import argparse
import logging
import shutil
from adbutils import adb

# 禁用 Ultralytics 的日志输出
logging.getLogger("ultralytics").setLevel(logging.CRITICAL)

# 全局变量
model = None
devices = []
output_dir = "outputs/replaylogs"
report_dir = "outputs/replay_reports"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(report_dir, exist_ok=True)
screenshot_queue = queue.Queue()
action_queue = queue.Queue()


# Airtest 兼容的 JSON 日志格式化器
class AirtestJsonFormatter(logging.Formatter):
    def format(self, record):
        timestamp = record.created
        log_entry = {
            "tag": getattr(record, 'tag', 'function'),
            "depth": getattr(record, 'depth', 0),
            "time": timestamp,
            "data": {
                "name": getattr(record, 'operation_name', 'unknown'),
                "call_args": getattr(record, 'call_args', {"message": record.getMessage()}),
                "start_time": timestamp - 0.001,
                "ret": getattr(record, 'ret', None),
                "end_time": timestamp
            }
        }
        return json.dumps(log_entry, ensure_ascii=False)


# 日志函数
def setup_device_logger(device_name):
    log_file = os.path.join(output_dir, f"{device_name}_log.txt")
    logger = logging.getLogger(device_name)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    formatter = AirtestJsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


# 获取设备名称
def get_device_name(device):
    try:
        brand = device.shell("getprop ro.product.brand").strip()
        model = device.shell("getprop ro.product.model").strip()
        resolution = device.shell("wm size").strip().replace("Physical size: ", "")
        return f"{brand}-{model}-{resolution}"
    except Exception as e:
        print(f"获取设备 {device.serial} 信息失败: {e}")
        return device.serial


# 检测按钮
def detect_buttons(frame, target_class=None):
    frame_for_detection = cv2.resize(frame, (640, 640))
    results = model.predict(source=frame_for_detection, device="mps", imgsz=640, conf=0.3, verbose=False)
    orig_h, orig_w = frame.shape[:2]
    scale_x, scale_y = orig_w / 640, orig_h / 640

    for box in results[0].boxes:
        cls_id = int(box.cls.item())
        detected_class = model.names[cls_id]
        if detected_class == target_class:
            box_x, box_y = box.xywh[0][:2].tolist()
            x, y = box_x * scale_x, box_y * scale_y
            return True, (x, y, detected_class)
    return False, (None, None, None)


# 验证目标消失
def verify_target_disappeared(device, target_class, max_attempts=5, delay=0.5):
    for attempt in range(max_attempts):
        screenshot = device.screenshot()
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        success, result = detect_buttons(frame, target_class=target_class)
        if not success or result[0] is None:
            return True
        time.sleep(delay)
    return False


# 检查设备状态
def check_device_status(device, device_name):
    try:
        device.shell("echo test")
        device.shell("input keyevent 82")
        time.sleep(1)
        device.shell("input swipe 500 1000 500 500")
        time.sleep(1)
        display_state = device.shell("dumpsys power | grep 'mHoldingDisplaySuspendBlocker'")
        if "true" not in display_state.lower():
            print(f"设备 {device_name} 屏幕未打开，尝试唤醒")
            device.shell("input keyevent 26")
            time.sleep(1)
        print(f"设备 {device_name} 状态检查完成")
        return True
    except Exception as e:
        print(f"设备 {device_name} 状态检查失败: {e}")
        return False


# 单设备回放任务
def replay_device(device, scripts, screenshot_queue, click_queue, result_queue, stop_event, device_name):
    if not check_device_status(device, device_name):
        print(f"设备 {device_name} 不可用，跳过回放")
        stop_event.set()
        result_queue.put((device_name, "completed_steps", 0, 0))
        return

    log_dir = os.path.join(output_dir, f"{device_name}_log")
    os.makedirs(log_dir, exist_ok=True)
    set_logdir(log_dir)

    step_counter = 0
    completed_steps = 0
    total_steps = sum(len(json.load(open(s["path"], "r", encoding="utf-8"))["steps"]) for s in scripts)

    for script_idx, script_config in enumerate(scripts):
        script_path = script_config["path"]
        loop_count = script_config.get("loop_count", 1)
        max_duration = script_config.get("max_duration", float("inf"))

        if not os.path.exists(script_path):
            print(f"文件 {script_path} 不存在，跳过")
            continue

        with open(script_path, "r", encoding="utf-8") as f:
            steps = json.load(f)["steps"]

        print(
            f"设备 {device_name} 开始执行脚本: {script_path} (循环次数: {loop_count}, 最长运行时间: {max_duration if max_duration != float('inf') else '无限制'}s)")
        log({"msg": f"Start script {script_path}", "success": True})

        start_time = time.time()
        has_max_duration = max_duration != float("inf")
        loops_completed = 0

        all_classes = {s["class"]: s.get("Priority", float("inf")) for s in steps if s["class"] != "unknown"}
        step_map = {s["class"]: s for s in steps}

        while loops_completed < loop_count and not stop_event.is_set():
            if has_max_duration and time.time() - start_time > max_duration:
                print(f"设备 {device_name} 脚本 {script_path} 已达到最大运行时间 {max_duration}s")
                log({"msg": f"Timeout after {max_duration}s", "success": False})
                break

            print(f"设备 {device_name} 脚本 {script_path} 开始第 {loops_completed + 1} 次循环")
            log({"msg": f"Start loop {loops_completed + 1} for script {script_path}", "success": True})

            for step in steps:
                if stop_event.is_set():
                    break
                if has_max_duration and time.time() - start_time > max_duration:
                    print(f"设备 {device_name} 脚本 {script_path} 超时退出")
                    log({"msg": f"Timeout after {max_duration}s", "success": False})
                    break

                screenshot = device.screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                timestamp = time.time()

                step_class = step.get("class", "unknown")
                step_remark = step.get("remark", "")
                log({"msg": f"Step {step_counter + 1}: Detecting {step_class} - {step_remark}", "success": True})
                snapshot(msg=f"Step {step_counter + 1}: Detecting {step_class} - {step_remark}")

                success, result = detect_buttons(frame, target_class=step_class)
                if success:
                    x, y, detected_class = result
                    step_counter += 1
                    step_num = step_counter

                    log({"msg": f"Step {step_num}: Click {detected_class} at ({x:.1f}, {y:.1f}) - {step_remark}",
                         "success": True})
                    touch([x, y])
                    action_queue.put((device_name, step_num, detected_class, x, y, time.time()))
                    result_queue.put((device_name, step_num, "click", True))
                    completed_steps += 1

                    time.sleep(0.5)
                    disappeared = verify_target_disappeared(device, detected_class)
                    log({
                            "msg": f"Step {step_num}: After click {detected_class} - {'Disappeared' if disappeared else 'Not Disappeared'}",
                            "success": disappeared})
                    snapshot(
                        msg=f"Step {step_num}: After click {detected_class} - {'Disappeared' if disappeared else 'Not Disappeared'}")

                    if script_idx < len(scripts) - 1 and step == steps[-1]:
                        if not disappeared:
                            print(f"设备 {device_name} 脚本 {script_path} 最后一步 {step_num} 执行失败，停止后续脚本")
                            log({"msg": f"Step {step_num}: Failed - Target {detected_class} did not disappear",
                                 "success": False})
                            stop_event.set()
                            return
                else:
                    if step_class == "unknown":
                        step_counter += 1
                        step_num = step_counter
                        h, w = frame.shape[:2]
                        x, y = step.get("relative_x", 0.5) * w, step.get("relative_y", 0.5) * h

                        log({"msg": f"Step {step_num}: Click unknown at ({x:.1f}, {y:.1f}) - {step_remark}",
                             "success": True})
                        touch([x, y])
                        action_queue.put((device_name, step_num, "unknown", x, y, time.time()))
                        result_queue.put((device_name, step_num, "click", True))
                        completed_steps += 1
                        time.sleep(3)
                        snapshot(msg=f"Step {step_num}: Click unknown at ({x:.1f}, {y:.1f})")
                    else:
                        print(f"设备 {device_name} 未检测到目标按钮 {step_class}，等待下一轮检测")
                        log({
                                "msg": f"Step {step_counter + 1}: No target {step_class} detected, waiting for next detection",
                                "success": False})
                        # Save screenshot for debugging
                        cv2.imwrite(os.path.join(log_dir, f"failed_detection_step_{step_counter + 1}_{timestamp}.jpg"),
                                    frame)
                        time.sleep(1)

            loops_completed += 1
            print(f"设备 {device_name} 脚本 {script_path} 完成第 {loops_completed} 次循环")
            log({"msg": f"End loop {loops_completed} for script {script_path}", "success": True})

        print(f"设备 {device_name} 脚本 {script_path} 执行完成")
        log({"msg": f"End script {script_path}", "success": True})

    print(f"设备 {device_name} 回放完成，完成步骤数: {completed_steps}")
    log({"msg": f"End replay for device {device_name}, completed steps: {completed_steps}", "success": True})
    stop_event.set()
    result_queue.put((device_name, "completed_steps", completed_steps, total_steps))


# 检测服务
def detection_service(screenshot_queue, click_queue, stop_event):
    while not stop_event.is_set():
        try:
            item = screenshot_queue.get(timeout=1)
            if len(item) != 5:
                print(f"跳过无效数据: {item}")
                continue
            device_name, step_num, frame, target_class, all_classes_or_special = item
            success, coords = detect_buttons(frame, target_class=target_class)
            click_queue.put((success, coords))
        except queue.Empty:
            continue
        except Exception as e:
            print(f"检测服务错误: {e}")

def generate_airtest_report(device_name, script_path):
    log_dir = os.path.join(output_dir, f"{device_name}_log")
    report_file = os.path.join(report_dir, f"{device_name}_report.html")

    # 创建临时脚本文件
    temp_script = os.path.join(log_dir, "temp_script.py")
    with open(temp_script, "w", encoding="utf-8") as f:
        f.write("# Temporary script for Airtest report generation\n")
        f.write("from airtest.core.api import *\n")
        f.write("log({'msg': 'Temporary script executed', 'success': True})\n")

    try:
        # 调试输出日志目录和文件
        print(f"Log directory: {log_dir}")
        print(f"Log files: {os.listdir(log_dir)}")

        # 使用 LogToHtml 生成报告
        report = LogToHtml(temp_script, log_root=log_dir)
        # report.report("html_report.html", output_file=report_file)
        report.report( output_file=report_file)
        print(f"已为设备 {device_name} 生成 Airtest 报告: {report_file}")
    except Exception as e:
        print(f"设备 {device_name} 的报告生成失败: {e}")
        # 打印详细的异常信息
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(temp_script):
            os.remove(temp_script)

# 生成报告
def generate_report(device_info):
    report = {
        "device_name": device_info['device_name'],
        "success": False,  # 默认设置为 False
        "error_message": None  # 添加错误信息字段
    }
    # 模拟报告生成逻辑
    try:
        # 生成报告的逻辑
        # 这里可以添加具体的报告生成逻辑，例如调用其他函数或处理数据
        report["success"] = True
    except Exception as e:
        report["success"] = False
        report["error_message"] = str(e)  # 记录错误信息
        print(f"Error generating report: {e}")

    if report["success"]:
        print("Report generated successfully")
    else:
        print(f"Report generation failed: {report['error_message']}")

# 回放步骤
def replay_steps(scripts, show_screens=False):
    global model, devices

    loaded_scripts = []
    for script_config in scripts:
        script_path = script_config["path"]
        if not os.path.exists(script_path):
            print(f"文件 {script_path} 不存在，跳过")
            continue
        loaded_scripts.append(script_config)

    if not loaded_scripts:
        print("未加载任何有效脚本，回放终止")
        return False

    device_names = {}
    for device in devices:
        serial = device.serial
        try:
            airtest_device = connect_device(f"Android:///{serial}")
            device_names[serial] = get_device_name(airtest_device)
            airtest_device.serial = serial
            print(f"设备 {device_names[serial]} 连接成功")
        except Exception as e:
            print(f"设备 {serial} 连接失败: {e}")
            continue

    print(f"加载脚本: {', '.join(s['path'] for s in loaded_scripts)}")
    print(f"检测到 {len(devices)} 个设备: {[device_names[d.serial] for d in devices]}")
    print("开始回放")
    log({"msg": "Start replay", "success": True})

    screenshot_queue = queue.Queue()
    click_queue = queue.Queue()
    result_queue = queue.Queue()
    stop_event = Event()
    threads = []

    frame_buffers = {d.serial: None for d in devices}
    action_buffers = {d.serial: None for d in devices}
    action_timestamps = {d.serial: 0 for d in devices}
    windows = {d.serial: f"Device {device_names[d.serial]}" for d in devices}
    window_created = {d.serial: False for d in devices}

    if show_screens:
        for serial in windows:
            try:
                cv2.namedWindow(windows[serial], cv2.WINDOW_NORMAL)
                cv2.resizeWindow(windows[serial], 360, 640)
                print(f"创建窗口: {windows[serial]}")
                window_created[serial] = True
            except Exception as e:
                print(f"创建窗口 {windows[serial]} 失败: {e}")

    detection_thread = Thread(target=detection_service, args=(screenshot_queue, click_queue, stop_event))
    detection_thread.daemon = True
    detection_thread.start()
    threads.append(detection_thread)

    active_devices = set(d.serial for d in devices)
    step_results = {d.serial: {} for d in devices}
    completed_steps_per_device = {d.serial: 0 for d in devices}
    total_steps_per_device = {d.serial: 0 for d in devices}

    for device in devices:
        t = Thread(target=replay_device, args=(
            device, loaded_scripts, screenshot_queue, click_queue, result_queue, stop_event,
            device_names[device.serial]))
        t.daemon = True
        t.start()
        threads.append(t)

    last_update_time = time.time()

    while active_devices and not stop_event.is_set():
        while not result_queue.empty():
            device_name, key, value, total_steps = result_queue.get_nowait()
            serial = [d.serial for d in devices if device_names[d.serial] == device_name][0]
            if key == "completed_steps":
                completed_steps_per_device[serial] = value
                total_steps_per_device[serial] = total_steps
                active_devices.discard(serial)
                print(f"设备 {device_names[serial]} 回放完成，完成步骤数: {value}")
            else:
                step_results[serial][(key, value)] = True

        if show_screens and (time.time() - last_update_time >= 1.0):
            while not action_queue.empty():
                device_name, step_num, button_class, x, y, timestamp = action_queue.get_nowait()
                serial = [d.serial for d in devices if device_names[d.serial] == device_name][0]
                screenshot = devices[[d.serial for d in devices].index(serial)].screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                frame_buffers[serial] = frame
                action_buffers[serial] = (step_num, button_class, x, y)
                action_timestamps[serial] = timestamp
                print(f"设备 {device_name} 更新点击: 步骤 {step_num} - {button_class} 在 ({x:.1f}, {y:.1f})")

            for serial in windows:
                if frame_buffers[serial] is not None and window_created[serial]:
                    annotated_frame = frame_buffers[serial].copy()
                    if action_buffers[serial] and (time.time() - action_timestamps[serial]) < 1.0:
                        step_num, button_class, x, y = action_buffers[serial]
                        cv2.circle(annotated_frame, (int(x), int(y)), 20, (0, 0, 255), 3)
                        cv2.putText(annotated_frame, f"Step {step_num}: {button_class} (Clicked)",
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    try:
                        cv2.imshow(windows[serial], annotated_frame)
                    except Exception as e:
                        print(f"显示窗口 {windows[serial]} 失败: {e}")
            last_update_time = time.time()

            key = cv2.waitKey(1)
            if key & 0xFF == ord('q'):
                print("检测到 'q' 键，停止回放")
                stop_event.set()

        time.sleep(0.05)

    stop_event.set()
    for t in threads:
        t.join(timeout=1.0)
    cv2.destroyAllWindows()

    # 生成报告
    report_success = True
    for device in devices:
        script_path = loaded_scripts[0]["path"] if loaded_scripts else "dummy_script.py"
        try:
            generate_airtest_report(device_names[device.serial], script_path)
            if not os.path.exists(os.path.join(output_dir, f"{device_names[device.serial]}_log",
                                               f"{device_names[device.serial]}_report.html")):
                report_success = False
        except Exception as e:
            print(f"设备 {device_names[device.serial]} 的报告生成失败: {e}")
            report_success = False

    # 检查是否所有步骤都完成
    all_steps_completed = all(
        completed_steps_per_device[serial] == total_steps_per_device[serial] for serial in completed_steps_per_device)

    if not all_steps_completed:
        print("回放未全部完成，部分设备仍有未执行步骤")
        return False
    if not report_success:
        print("所有设备回放成功，但报告生成失败")
        return False
    print("所有设备回放成功，报告生成成功")
    return True


# 主程序
def main():
    parser = argparse.ArgumentParser(description="设备回放脚本")
    parser.add_argument("--show-screens", action="store_true", help="显示所有设备画面并同步回放")
    parser.add_argument("--steps", nargs="+", help="指定多个回放步骤文件")
    parser.add_argument("--loop-count", type=int, action="append", help="指定循环次数，逐脚本应用")
    parser.add_argument("--max-duration", type=float, action="append", help="指定最大运行时间（秒），逐脚本应用")

    args = parser.parse_args()
    scripts = []

    if args.steps:
        script_files = args.steps
        loop_counts = args.loop_count or []
        max_durations = args.max_duration or []

        for i, script_path in enumerate(script_files):
            if script_path.startswith("--"):
                continue
            script_config = {"path": script_path}
            if i < len(loop_counts):
                script_config["loop-count"] = loop_counts[i]
            if i < len(max_durations):
                script_config["max-duration"] = max_durations[i]
            scripts.append(script_config)

    if not scripts:
        parser.error("必须使用 --steps 指定至少一个脚本文件")

    global devices, model
    devices = adb.device_list()
    if not devices:
        print("错误: 未检测到 ADB 设备")
        exit(1)

    # 连接设备
    for device in devices:
        try:
            connect_device(f"Android:///{device.serial}")
            device_name = get_device_name(device)
            setup_device_logger(device_name)
            print(f"设备 {device_name} 连接成功")
        except Exception as e:
            print(f"设备 {device.serial} 连接失败: {e}")

    # 检查设备状态
    for device in devices:
        device_name = get_device_name(device)
        if not check_device_status(device, device_name):
            print(f"设备 {device_name} 不可用，跳过回放")
            exit(1)

    # 加载模型
    try:
        model = YOLO("/Users/helloppx/PycharmProjects/GameAI/outputs/train/weights/best.pt")
    except Exception as e:
        print(f"模型加载失败: {e}")
        exit(1)

    # 检测设备
    devices = adb.device_list()
    if not devices:
        print("错误: 未检测到 ADB 设备")
        exit(1)

    try:
        model = YOLO("/Users/helloppx/PycharmProjects/GameAI/outputs/train/weights/best.pt")
    except Exception as e:
        print(f"模型加载失败: {e}")
        exit(1)

    try:
        success = replay_steps(scripts, show_screens=args.show_screens)
        if not success:
            print("回放失败，请检查日志")
        else:
            print("回放成功")
    except Exception as e:
        print(f"回放失败: {e}")


if __name__ == "__main__":
    main()