import cv2
import numpy as np
from ultralytics import YOLO
import json
import time
from datetime import datetime
from adbutils import adb
import argparse
import os
import signal
import sys
import traceback
from threading import Thread
import queue

# 全局变量
script = {"steps": []}
save_path = ""
model = None
devices = []
click_counts = {}
MAX_CLICKS = 2
screenshot_queue = queue.Queue()


# 优雅退出处理
def signal_handler(sig, frame):
    print("\n收到 Ctrl+C，退出")
    if is_recording and script["steps"]:  # 录制模式保存
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(script, f, indent=4, ensure_ascii=False)
        print(f"最终脚本保存至: {save_path}")
    cv2.destroyAllWindows()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


# 获取设备品牌、型号和分辨率
def get_device_name(device):
    try:
        brand = device.shell("getprop ro.product.brand").strip()
        model = device.shell("getprop ro.product.model").strip()
        resolution = device.shell("wm size").strip().replace("Physical size: ", "")
        return f"{brand}-{model}-{resolution}"
    except Exception as e:
        print(f"获取设备 {device.serial} 信息失败: {e}")
        return device.serial


# 鼠标点击回调
def on_mouse(event, x, y, flags, param):
    global script, save_path, model, click_counts
    serial = param["serial"]
    frame = param["frame"]
    results = param["results"]
    device = next(d for d in devices if d.serial == serial)

    if event == cv2.EVENT_LBUTTONDOWN:
        orig_h, orig_w = frame.shape[:2]
        scale_x, scale_y = orig_w / 640, orig_h / 640
        matched = False

        if results and len(results[0].boxes) > 0:
            for box in results[0].boxes:
                box_x, box_y, box_w, box_h = box.xywh[0].tolist()
                box_x, box_y, box_w, box_h = box_x * scale_x, box_y * scale_y, box_w * scale_x, box_h * scale_y
                left, top = int(box_x - box_w / 2), int(box_y - box_h / 2)
                right, bottom = int(box_x + box_w / 2), int(box_y + box_h / 2)
                if left <= x <= right and top <= y <= bottom:
                    cls_id = int(box.cls.item())
                    conf = box.conf.item()
                    button_class = model.names[cls_id]
                    matched = True

                    # 录制模式：--record 或 --record-no-match
                    if is_recording:
                        # 匹配按钮的记录逻辑（适用于 --record 和 --record-no-match）
                        button_key = None
                        for key in click_counts:
                            k_class, k_x, k_y = key.split("_")
                            k_x, k_y = float(k_x), float(k_y)
                            if (button_class == k_class and
                                    abs(box_x - k_x) < 20 and
                                    abs(box_y - k_y) < 20):
                                button_key = key
                                break
                        if not button_key:
                            button_key = f"{button_class}_{box_x:.1f}_{box_y:.1f}"

                        click_counts[button_key] = click_counts.get(button_key, 0) + 1
                        if click_counts[button_key] > MAX_CLICKS:
                            print(f"按钮 {button_class} 已点击 {MAX_CLICKS} 次，忽略")
                            return

                        step = {
                            "step": len(script["steps"]) + 1,
                            "class": button_class,
                            "confidence": conf,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                            "remark": ""
                        }
                        script["steps"].append(step)
                        with open(save_path, "w", encoding="utf-8") as f:
                            json.dump(script, f, indent=4, ensure_ascii=False)
                        print("\n" + "=" * 50)
                        print(f"【按钮动作录入】: {button_class}，步骤 {step['step']} 已保存至 {save_path}")
                        print("=" * 50 + "\n")
                        device.shell(f"input tap {box_x} {box_y}")
                    else:  # 非录制模式，直接交互
                        device.shell(f"input tap {box_x} {box_y}")
                        print(f"交互点击: {button_class} at ({box_x:.1f}, {box_y:.1f})")
                    return

        # 未识别按钮处理（仅适用于 --record-no-match）
        if is_recording and args.record_no_match:
            rel_x, rel_y = x / orig_w, y / orig_h
            step = {
                "step": len(script["steps"]) + 1,
                "class": "unknown",
                "confidence": 0.0,
                "relative_x": rel_x,
                "relative_y": rel_y,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "remark": "未识别按钮"
            }
            script["steps"].append(step)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(script, f, indent=4, ensure_ascii=False)
            device.shell(f"input tap {x} {y}")
            print("\n" + "=" * 50)
            print(f"【未识别点击录入】: 比例坐标 ({rel_x:.3f}, {rel_y:.3f})，步骤 {step['step']} 已保存至 {save_path}")
            print("=" * 50 + "\n")
        elif not matched:  # 非录制模式下的未识别点击
            device.shell(f"input tap {x} {y}")
            print(f"交互点击: 未识别按钮 at ({x:.1f}, {y:.1f})")


# 设备屏幕捕获线程
def capture_device(device, screenshot_queue):
    while True:
        screenshot = device.screenshot()
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        screenshot_queue.put((device.serial, frame))
        time.sleep(0.1)  # 控制刷新率


# 解析命令行参数
parser = argparse.ArgumentParser(description="Record game operation script")
parser.add_argument("--record", action="store_true", help="Enable recording mode")
parser.add_argument("--record-no-match", action="store_true", help="Record clicks without matched buttons")
args = parser.parse_args()

# 自动连接 ADB 设备
try:
    devices = adb.device_list()
    if not devices:
        raise Exception("未检测到 ADB 设备，请检查连接和 USB 调试")
    device_names = {d.serial: get_device_name(d) for d in devices}  # 获取设备名称
    print(f"已连接设备: {[device_names[d.serial] for d in devices]}")
except Exception as e:
    print(f"ADB 初始化失败: {e}")
    sys.exit(1)

# 加载模型
try:
    model = YOLO("/Users/helloppx/PycharmProjects/GameAI/outputs/train/weights/best.pt")
except Exception as e:
    print(f"模型加载失败: {e}")
    sys.exit(1)

# 判断是否为录制模式
is_recording = args.record or args.record_no_match  # 任意一个为 True 即进入录制模式

# 录制模式生成保存路径
if is_recording:
    output_dir = "/Users/helloppx/PycharmProjects/GameAI/outputs/recordlogs"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    save_path = os.path.join(output_dir, f"scene1_{timestamp}.json")

# 修改后的启动提示
print("启动脚本，按 'q' 退出")
if is_recording:
    if args.record_no_match:
        print("已进入录制模式，未识别按钮点击将被记录为比例坐标")
    else:
        print("已进入录制模式，仅记录匹配的按钮点击")
else:
    print("已进入交互模式，点击窗口直接操作设备，不生成 JSON")

# 启动设备捕获线程
threads = []
for device in devices:
    t = Thread(target=capture_device, args=(device, screenshot_queue))
    t.daemon = True
    t.start()
    threads.append(t)

# 主循环显示所有设备
windows = {d.serial: f"Device {get_device_name(d)}" for d in devices}
frame_buffers = {d.serial: None for d in devices}
results_buffers = {d.serial: None for d in devices}

while True:
    try:
        serial, frame = screenshot_queue.get(timeout=1)
        frame_for_detection = cv2.resize(frame, (640, 640))
        results = model.predict(source=frame_for_detection, device="mps", imgsz=640, conf=0.6)

        # 更新缓冲区
        frame_buffers[serial] = frame
        results_buffers[serial] = results

        annotated_frame = frame.copy()
        if results:
            orig_h, orig_w = frame.shape[:2]
            scale_x, scale_y = orig_w / 640, orig_h / 640
            for box in results[0].boxes:
                x, y, w, h = box.xywh[0].tolist()
                x, y, w, h = x * scale_x, y * scale_y, w * scale_x, h * scale_y
                cls_id = int(box.cls.item())
                conf = box.conf.item()
                cv2.rectangle(annotated_frame,
                              (int(x - w / 2), int(y - h / 2)),
                              (int(x + w / 2), int(y + h / 2)),
                              (0, 255, 0), 2)
                cv2.putText(annotated_frame, f"{model.names[cls_id]} {conf:.2f}",
                            (int(x - w / 2), int(y - h / 2 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow(windows[serial], annotated_frame)
        cv2.setMouseCallback(windows[serial], on_mouse, param={"serial": serial, "frame": frame, "results": results})

        key = cv2.waitKey(50) & 0xFF
        if key == ord("q"):
            print("退出程序")
            break
    except queue.Empty:
        for serial in windows:
            if frame_buffers[serial] is not None:
                cv2.imshow(windows[serial], frame_buffers[serial])
        continue
    except Exception as e:
        print(f"主循环异常: {traceback.format_exc()}")
        break

# 修改后的结束逻辑
if is_recording and script["steps"]:  # 录制模式且有记录时保存
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=4, ensure_ascii=False)
    print(f"程序结束，最终脚本保存至: {save_path}")
elif is_recording:  # 录制模式但没记录
    print("程序结束，录制模式未记录任何操作，未生成 JSON")
else:  # 非录制模式
    print("程序结束，非录制模式，未生成 JSON")

cv2.destroyAllWindows()