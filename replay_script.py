import cv2
import numpy as np
from ultralytics import YOLO
import json
import time
from datetime import datetime
from adbutils import adb
import os
import glob
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
def detect_buttons(frame, button_class, special_region=None):
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
                    return True, None
        return False, None

    for box in results[0].boxes:
        cls_id = int(box.cls.item())
        if model.names[cls_id] == button_class:
            box_x, box_y = box.xywh[0][:2].tolist()
            x, y = box_x * scale_x, box_y * scale_y
            return True, (x, y)
    return False, None

# 单设备回放任务
def replay_device(device, script, screenshot_queue, click_queue, result_queue, stop_event, device_name):
    serial = device.serial
    log(f"设备 {device_name} 开始回放")
    for step in script["steps"]:
        if stop_event.is_set():
            log(f"设备 {device_name} 因中止信号停止回放")
            break
        step_num = step["step"]
        button_class = step["class"]
        remark = step["remark"]
        log(f"设备 {device_name}: 执行步骤 {step_num} - {button_class} ({remark})")

        if button_class != "unknown":
            max_attempts = 15
            for attempt in range(max_attempts):
                if stop_event.is_set():
                    break
                screenshot = device.screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                screenshot_queue.put((serial, step_num, frame, button_class, None))
                success, coords = click_queue.get()

                if success:
                    x, y = coords
                    device.shell(f"input tap {x} {y}")
                    log(f"设备 {device_name}: 检测到 {button_class} 并点击: ({x:.1f}, {y:.1f})")
                    action_queue.put((serial, step_num, button_class, x, y, time.time()))
                    result_queue.put((serial, step_num, "click", True))

                    time.sleep(1)
                    screenshot = device.screenshot()
                    frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

                    if button_class in special_buttons:
                        special_region = (max(0, x - 50), x, max(0, y - 50), y + 50)
                        screenshot_queue.put((serial, step_num, frame, button_class, special_region))
                        v_success, _ = click_queue.get()
                        if v_success:
                            log(f"设备 {device_name}: {button_class} 前方单选框已勾选")
                            result_queue.put((serial, step_num, "verify", True))
                        else:
                            log(f"设备 {device_name}: {button_class} 前方单选框未勾选")
                            result_queue.put((serial, step_num, "verify", False))
                            stop_event.set()
                    else:
                        screenshot_queue.put((serial, step_num, frame, button_class, None))
                        v_success, _ = click_queue.get()
                        if not v_success:
                            log(f"设备 {device_name}: 按钮 {button_class} 已消失")
                            result_queue.put((serial, step_num, "verify", True))
                        else:
                            log(f"设备 {device_name}: 按钮 {button_class} 未消失")
                            result_queue.put((serial, step_num, "verify", False))
                            stop_event.set()
                    break
                log(f"设备 {device_name}: 尝试 {attempt + 1}/{max_attempts} 未检测到 {button_class}")
                time.sleep(1)
            else:
                result_queue.put((serial, step_num, "click", False))
                stop_event.set()
        else:
            screenshot = device.screenshot()
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            h, w = frame.shape[:2]
            x, y = step["relative_x"] * w, step["relative_y"] * h
            device.shell(f"input tap {x} {y}")
            log(f"设备 {device_name}: 未识别按钮点击: ({x:.1f}, {y:.1f})")
            action_queue.put((serial, step_num, button_class, x, y, time.time()))
            result_queue.put((serial, step_num, "click", True))
            time.sleep(3)

    log(f"设备 {device_name} 回放完成")
    if not stop_event.is_set():
        for step in script["steps"]:
            result_queue.put((serial, step["step"], "click", True))
            if step["class"] != "unknown":
                result_queue.put((serial, step["step"], "verify", True))

# 主线程检测服务
def detection_service(screenshot_queue, click_queue, stop_event):
    while not stop_event.is_set():
        try:
            item = screenshot_queue.get(timeout=60)
            if len(item) != 5:
                log(f"跳过无效数据: {item}")
                continue
            serial, step_num, frame, button_class, special_region = item
            success, coords = detect_buttons(frame, button_class, special_region)
            click_queue.put((success, coords))
        except queue.Empty:
            continue
        except Exception as e:
            log(f"检测服务错误: {e}")

# 回放步骤（主线程负责显示）
def replay_steps(script_path, show_screens=False):
    global model, devices
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    device_names = {d.serial: get_device_name(d) for d in devices}
    log(f"加载脚本: {script_path}")
    log(f"检测到 {len(devices)} 个设备: {[device_names[d.serial] for d in devices]}")
    log("开始回放")

    screenshot_queue = queue.Queue()
    click_queue = queue.Queue()
    result_queue = queue.Queue()
    stop_event = Event()
    threads = []

    # 显示相关变量
    frame_buffers = {d.serial: None for d in devices}
    action_buffers = {d.serial: None for d in devices}
    action_timestamps = {d.serial: 0 for d in devices}
    windows = {d.serial: f"Device {device_names[d.serial]}" for d in devices}
    window_created = {d.serial: False for d in devices}

    # 如果启用显示，初始化窗口
    if show_screens:
        for serial in windows:
            try:
                cv2.namedWindow(windows[serial], cv2.WINDOW_NORMAL)
                cv2.resizeWindow(windows[serial], 360, 640)
                log(f"创建窗口: {windows[serial]}")
                window_created[serial] = True
            except Exception as e:
                log(f"创建窗口 {windows[serial]} 失败: {e}")

    # 启动检测线程
    detection_thread = Thread(target=detection_service, args=(screenshot_queue, click_queue, stop_event))
    detection_thread.daemon = True
    detection_thread.start()
    threads.append(detection_thread)

    # 启动回放线程
    active_devices = set(d.serial for d in devices)
    step_results = {d.serial: {} for d in devices}
    for device in devices:
        t = Thread(target=replay_device, args=(device, script, screenshot_queue, click_queue, result_queue, stop_event, device_names[device.serial]))
        t.daemon = True
        t.start()
        threads.append(t)

    # 主循环：监控回放并处理显示
    total_steps = len(script["steps"])
    last_update_time = time.time()
    while active_devices and not stop_event.is_set():
        # 处理结果队列
        while not result_queue.empty():
            serial, step, action, success = result_queue.get_nowait()
            step_results[serial][(step, action)] = success

        # 检查回放进度
        for step_num in range(1, total_steps + 1):
            for serial in list(active_devices):
                if (step_num, "click") not in step_results[serial]:
                    timestamp = script["steps"][step_num - 1].get("timestamp", time.time())
                    try:
                        timestamp = float(timestamp)
                    except (TypeError, ValueError):
                        timestamp = time.time()
                    if time.time() - timestamp > 60:
                        log(f"设备 {device_names[serial]} 步骤 {step_num} 超时或未完成")
                        stop_event.set()
                    continue
                if not step_results[serial][(step_num, "click")]:
                    log(f"设备 {device_names[serial]} 步骤 {step_num} 点击失败")
                    stop_event.set()
                    break
                if script["steps"][step_num - 1]["class"] != "unknown" and (step_num, "verify") not in step_results[serial]:
                    continue
                if script["steps"][step_num - 1]["class"] != "unknown" and not step_results[serial][(step_num, "verify")]:
                    log(f"设备 {device_names[serial]} 步骤 {step_num} 验证失败")
                    stop_event.set()
                    break
            if stop_event.is_set():
                break

        # 检查是否所有步骤完成
        for serial in list(active_devices):
            if all((i, "click") in step_results[serial] for i in range(1, total_steps + 1)):
                if all((i, "verify") in step_results[serial] and step_results[serial][(i, "verify")]
                       for i in range(1, total_steps + 1) if script["steps"][i - 1]["class"] != "unknown"):
                    active_devices.remove(serial)

        # 处理显示（每1秒更新一次）
        if show_screens and (time.time() - last_update_time >= 1.0):
            # 处理点击动作并更新帧
            while not action_queue.empty():
                serial, step_num, button_class, x, y, timestamp = action_queue.get_nowait()
                screenshot = devices[[d.serial for d in devices].index(serial)].screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                frame_buffers[serial] = frame
                action_buffers[serial] = (step_num, button_class, x, y)
                action_timestamps[serial] = timestamp
                log(f"设备 {serial} 更新点击: 步骤 {step_num} - {button_class} 在 ({x:.1f}, {y:.1f})")

            # 更新并显示所有窗口
            for serial in windows:
                if frame_buffers[serial] is not None and window_created[serial]:
                    annotated_frame = frame_buffers[serial].copy()
                    if action_buffers[serial] and (time.time() - action_timestamps[serial]) < 1.0:
                        _, step_num, button_class, x, y = action_buffers[serial]
                        cv2.circle(annotated_frame, (int(x), int(y)), 20, (0, 0, 255), 3)
                        cv2.putText(annotated_frame, f"Step {step_num}: {button_class} (Clicked)",
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    try:
                        cv2.imshow(windows[serial], annotated_frame)
                    except Exception as e:
                        log(f"显示窗口 {windows[serial]} 失败: {e}")
            last_update_time = time.time()

            # 处理退出事件
            key = cv2.waitKey(1)
            if key & 0xFF == ord('q'):
                log("检测到 'q' 键，停止回放")
                stop_event.set()

        time.sleep(0.05)

    # 回放结束处理
    stop_event.set()
    for t in threads:
        t.join(timeout=1.0)
    cv2.destroyAllWindows()
    if active_devices or stop_event.is_set():
        log("回放失败，部分设备未完成")
        return False
    log("所有设备回放成功")
    sys.exit(0)

# 获取最新的 JSON 文件
def get_latest_json(directory):
    json_files = glob.glob(os.path.join(directory, "scene1_*.json"))
    if not json_files:
        raise FileNotFoundError("未找到任何 JSON 文件")
    return max(json_files, key=os.path.getctime)

# 主程序
def main():
    parser = argparse.ArgumentParser(description="设备回放脚本")
    parser.add_argument("--show-screens", action="store_true", help="显示所有设备画面并同步回放")
    args = parser.parse_args()

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
        script_path = get_latest_json("/Users/helloppx/PycharmProjects/GameAI/outputs/recordlogs")
        success = replay_steps(script_path, show_screens=args.show_screens)
        if not success:
            print("回放失败，请检查日志")
        else:
            print("回放成功")
    except Exception as e:
        print(f"回放失败: {e}")

if __name__ == "__main__":
    main()