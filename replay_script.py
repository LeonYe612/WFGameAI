import cv2
import numpy as np
from ultralytics import YOLO
import json
import time
from datetime import datetime
from adbutils import adb
import os
from threading import Thread, Event
import queue
import sys
import argparse
import logging

# 禁用 Ultralytics 的日志输出
logging.getLogger("ultralytics").setLevel(logging.CRITICAL)

# 全局变量
model = None
devices = []
output_dir = "/Users/helloppx/PycharmProjects/GameAI/outputs/replaylogs"
os.makedirs(output_dir, exist_ok=True)
log_path = os.path.join(output_dir, f"replay_log_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.txt")
special_buttons = ["system-protocol-box"]
screenshot_queue = queue.Queue()
action_queue = queue.Queue()


# 日志函数
def log(message):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')} - {message}\n")
    print(message)


# 获取设备品牌、型号和分辨率
def get_device_name(device):
    try:
        brand = device.shell("getprop ro.product.brand").strip()
        model = device.shell("getprop ro.product.model").strip()
        resolution = device.shell("wm size").strip().replace("Physical size: ", "")
        return f"{brand}-{model}-{resolution}"
    except Exception as e:
        log(f"获取设备 {device.serial} 信息失败: {e}")
        return device.serial


# 主线程检测函数
def detect_buttons(frame, all_classes=None, target_class=None, special_region=None):
    frame_for_detection = cv2.resize(frame, (640, 640))
    results = model.predict(source=frame_for_detection, device="mps", imgsz=640, conf=0.3, verbose=False)
    orig_h, orig_w = frame.shape[:2]
    scale_x, scale_y = orig_w / 640, orig_h / 640

    if special_region:
        x_min, x_max, y_min, y_max = special_region
        for box in results[0].boxes:
            cls_id = int(box.cls.item())
            if "checkbox" in model.names[cls_id]:
                box_x, box_y = box.xywh[0][:2].tolist()
                x, y = box_x * scale_x, box_y * scale_y
                if x_min <= x <= x_max and y_min <= y <= y_max:
                    return True, (None, None, None)
        return False, (None, None, None)

    matched_targets = []
    for box in results[0].boxes:
        cls_id = int(box.cls.item())
        detected_class = model.names[cls_id]
        if target_class and detected_class == target_class:
            box_x, box_y = box.xywh[0][:2].tolist()
            x, y = box_x * scale_x, box_y * scale_y
            return True, (x, y, detected_class)
        elif all_classes and detected_class in all_classes:
            box_x, box_y = box.xywh[0][:2].tolist()
            x, y = box_x * scale_x, box_y * scale_y
            priority = all_classes[detected_class]
            matched_targets.append({"class": detected_class, "x": x, "y": y, "priority": priority})

    if matched_targets:
        matched_targets.sort(key=lambda x: x["priority"])  # 最低 Priority 值优先
        return True, (matched_targets[0]["x"], matched_targets[0]["y"], matched_targets[0]["class"])
    return False, (None, None, None)


# 验证目标是否消失
def verify_target_disappeared(device, target_class, max_attempts=5, delay=0.5):
    for attempt in range(max_attempts):
        screenshot = device.screenshot()
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        success, result = detect_buttons(frame, target_class=target_class)
        if not success or result[0] is None:
            return True
        time.sleep(delay)
    return False


# 单设备回放任务
def replay_device(device, scripts, screenshot_queue, click_queue, result_queue, stop_event, device_name):
    serial = device.serial
    log(f"设备 {device_name} 开始回放")

    step_counter = 0
    global_start_time = time.time()

    for script_idx, script_config in enumerate(scripts):
        script_path = script_config["path"]
        loop_count = script_config.get("loop_count", None)
        max_duration = script_config.get("max_duration", float("inf"))

        if not os.path.exists(script_path):
            log(f"文件 {script_path} 不存在，跳过")
            continue
        with open(script_path, "r", encoding="utf-8") as f:
            steps = json.load(f)["steps"]

        start_time = time.time()
        has_max_duration = max_duration != float("inf")
        has_loop_count = loop_count is not None and loop_count > 0
        loop_idx = 0

        # 构建优先级字典
        all_classes = {s["class"]: s.get("Priority", float("inf")) for s in steps if s["class"] != "unknown"}
        step_map = {s["class"]: s for s in steps}  # 用于查找备注等信息

        while not stop_event.is_set():
            if has_max_duration and time.time() - start_time > max_duration:
                log(f"设备 {device_name} 文件 {script_path} 已达到最大运行时间 {max_duration}s")
                break
            if has_loop_count and loop_idx >= loop_count:
                break

            log(f"设备 {device_name} 开始回放文件: {script_path} (循环次数: {loop_count if has_loop_count else '无限制'}, 最长运行时间: {max_duration if has_max_duration else '无限制'}s, 当前第 {loop_idx + 1} 次)")

            # 动态检测并按优先级执行
            while not stop_event.is_set() and (not has_max_duration or time.time() - start_time <= max_duration):
                screenshot = device.screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                screenshot_queue.put((serial, step_counter + 1, frame, None, all_classes))
                success, result = click_queue.get()

                if success and result[0] is not None:
                    x, y, detected_class = result
                    step = step_map.get(detected_class, {"class": detected_class, "remark": "未定义", "Priority": all_classes[detected_class]})
                    step_counter += 1
                    step_num = step_counter

                    log(f"设备 {device_name}: 执行步骤 {step_num} - {detected_class} (Priority: {all_classes[detected_class]}, remark: {step['remark']})")
                    device.shell(f"input tap {x} {y}")
                    log(f"设备 {device_name}: 检测到 {detected_class} (Priority: {all_classes[detected_class]}) 并点击: ({x:.1f}, {y:.1f})")
                    action_queue.put((serial, step_num, detected_class, x, y, time.time()))
                    result_queue.put((serial, step_num, "click", True))

                    time.sleep(0.5)
                    if verify_target_disappeared(device, detected_class):
                        log(f"设备 {device_name}: 按钮 {detected_class} 已消失")
                        result_queue.put((serial, step_num, "verify", True))
                    else:
                        log(f"设备 {device_name}: 按钮 {detected_class} 未消失")
                        result_queue.put((serial, step_num, "verify", False))

                    # 检查最后一步是否成功
                    if script_idx < len(scripts) - 1 and loop_idx == (loop_count - 1 if has_loop_count else 0):
                        if not verify_target_disappeared(device, detected_class):
                            log(f"设备 {device_name}: 文件 {script_path} 最后一步 {step_num} 执行失败，停止后续文件")
                            stop_event.set()
                            return
                else:
                    # 如果未检测到任何目标，检查是否有 "unknown" 步骤
                    if "unknown" in step_map:
                        step = step_map["unknown"]
                        step_counter += 1
                        step_num = step_counter
                        h, w = frame.shape[:2]
                        x, y = step.get("relative_x", 0.5) * w, step.get("relative_y", 0.5) * h
                        log(f"设备 {device_name}: 执行步骤 {step_num} - unknown (Priority: {step.get('Priority', float('inf'))}, remark: {step['remark']})")
                        device.shell(f"input tap {x} {y}")
                        log(f"设备 {device_name}: 未识别按钮点击: ({x:.1f}, {y:.1f})")
                        action_queue.put((serial, step_num, "unknown", x, y, time.time()))
                        result_queue.put((serial, step_num, "click", True))
                        time.sleep(3)
                    else:
                        log(f"设备 {device_name}: 未检测到任何目标按钮，等待下一轮检测")
                        time.sleep(1)
                        break  # 退出内层循环，重新检测

            loop_idx += 1

    log(f"设备 {device_name} 回放完成")
    if not stop_event.is_set():
        # 确保所有步骤记录完成状态
        step_counter = 0
        for script_config in scripts:
            with open(script_config["path"], "r", encoding="utf-8") as f:
                steps = json.load(f)["steps"]
            for step in steps:
                step_counter += 1
                if (step_counter, "click") not in result_queue.queue:
                    result_queue.put((serial, step_counter, "click", True))
                if step["class"] != "unknown" and (step_counter, "verify") not in result_queue.queue:
                    result_queue.put((serial, step_counter, "verify", True))


# 主线程检测服务
def detection_service(screenshot_queue, click_queue, stop_event):
    while not stop_event.is_set():
        try:
            item = screenshot_queue.get(timeout=60)
            if len(item) != 5:
                log(f"跳过无效数据: {item}")
                continue
            serial, step_num, frame, target_class, all_classes_or_special = item
            success, coords = detect_buttons(frame, all_classes_or_special, target_class)
            click_queue.put((success, coords))
        except queue.Empty:
            continue
        except Exception as e:
            log(f"检测服务错误: {e}")


# 回放步骤（主线程负责显示）
def replay_steps(scripts, show_screens=False):
    global model, devices

    loaded_scripts = []
    for script_config in scripts:
        script_path = script_config["path"]
        if not os.path.exists(script_path):
            log(f"文件 {script_path} 不存在，跳过")
            continue
        loaded_scripts.append(script_config)

    if not loaded_scripts:
        log("未加载任何有效脚本，回放终止")
        return False

    device_names = {d.serial: get_device_name(d) for d in devices}
    log(f"加载脚本: {', '.join(s['path'] for s in loaded_scripts)}")
    log(f"检测到 {len(devices)} 个设备: {[device_names[d.serial] for d in devices]}")
    log("开始回放")

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
                log(f"创建窗口: {windows[serial]}")
                window_created[serial] = True
            except Exception as e:
                log(f"创建窗口 {windows[serial]} 失败: {e}")

    detection_thread = Thread(target=detection_service, args=(screenshot_queue, click_queue, stop_event))
    detection_thread.daemon = True
    detection_thread.start()
    threads.append(detection_thread)

    active_devices = set(d.serial for d in devices)
    step_results = {d.serial: {} for d in devices}
    for device in devices:
        t = Thread(target=replay_device, args=(
            device, loaded_scripts, screenshot_queue, click_queue, result_queue, stop_event, device_names[device.serial]))
        t.daemon = True
        t.start()
        threads.append(t)

    total_steps = sum(len(json.load(open(s["path"], "r", encoding="utf-8"))["steps"]) for s in loaded_scripts)
    last_update_time = time.time()
    while active_devices and not stop_event.is_set():
        while not result_queue.empty():
            serial, step, action, success = result_queue.get_nowait()
            step_results[serial][(step, action)] = success

        step_counter = 0
        for script_config in loaded_scripts:
            with open(script_config["path"], "r", encoding="utf-8") as f:
                steps = json.load(f)["steps"]
            for step in steps:
                step_counter += 1
                for serial in list(active_devices):
                    if (step_counter, "click") not in step_results[serial]:
                        timestamp = step.get("timestamp", time.time())
                        try:
                            timestamp = float(timestamp)
                        except (TypeError, ValueError):
                            timestamp = time.time()
                        if time.time() - timestamp > 60:
                            log(f"设备 {device_names[serial]} 步骤 {step_counter} 超时或未完成")
                        continue
                    if not step_results[serial][(step_counter, "click")]:
                        log(f"设备 {device_names[serial]} 步骤 {step_counter} 点击失败，继续后续步骤")

        for serial in list(active_devices):
            if all((i, "click") in step_results[serial] for i in range(1, total_steps + 1)):
                active_devices.remove(serial)

        if show_screens and (time.time() - last_update_time >= 1.0):
            while not action_queue.empty():
                serial, step_num, button_class, x, y, timestamp = action_queue.get_nowait()
                screenshot = devices[[d.serial for d in devices].index(serial)].screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                frame_buffers[serial] = frame
                action_buffers[serial] = (step_num, button_class, x, y)
                action_timestamps[serial] = timestamp
                log(f"设备 {serial} 更新点击: 步骤 {step_num} - {button_class} 在 ({x:.1f}, {y:.1f})")

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
                        log(f"显示窗口 {windows[serial]} 失败: {e}")
            last_update_time = time.time()

            key = cv2.waitKey(1)
            if key & 0xFF == ord('q'):
                log("检测到 'q' 键，停止回放")
                stop_event.set()

        time.sleep(0.05)

    stop_event.set()
    for t in threads:
        t.join(timeout=1.0)
    cv2.destroyAllWindows()
    if active_devices:
        log("回放未全部完成，部分设备仍有未执行步骤")
        return False
    log("所有设备回放成功")
    return True


# 主程序
def main():
    parser = argparse.ArgumentParser(description="设备回放脚本")
    parser.add_argument("--show-screens", action="store_true", help="显示所有设备画面并同步回放")

    args, remaining = parser.parse_known_args()
    scripts = []
    i = 0
    while i < len(remaining):
        if remaining[i] == "script":
            if i + 1 >= len(remaining):
                parser.error("每个 'script' 后必须指定文件路径")
            script_config = {"path": remaining[i + 1]}
            i += 2
            while i < len(remaining) and remaining[i].startswith("--"):
                if remaining[i] == "--loop-count" and i + 1 < len(remaining):
                    script_config["loop_count"] = int(remaining[i + 1])
                    i += 2
                elif remaining[i] == "--max-duration" and i + 1 < len(remaining):
                    script_config["max_duration"] = float(remaining[i + 1])
                    i += 2
                else:
                    break
            scripts.append(script_config)
        else:
            i += 1

    if not scripts:
        parser.error("必须指定至少一个脚本使用 'script' 命令")

    global devices, model
    devices = adb.device_list()
    if not devices:
        print("错误: 未检测到 ADB 设备")
        exit(1)
    device_names = {d.serial: get_device_name(d) for d in devices}
    print(f"已连接设备: {[device_names[d.serial] for d in devices]}")

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