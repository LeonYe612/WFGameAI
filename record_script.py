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

# 设置项目根目录为基准
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 全局变量
script = {"steps": []}
save_path = ""
model = None
devices = []
click_counts = {}
MAX_CLICKS = 2
screenshot_queue = queue.Queue(maxsize=10)  # 限制队列大小，避免内存占用过高
main_device = None  # 存储主设备
multi_devices_control = False  # 是否启用一机多控功能
device_resolutions = {}  # 存储设备分辨率信息
click_threads = []  # 存储点击线程，避免阻塞主线程
last_click_time = 0  # 记录上次点击时间
MIN_CLICK_INTERVAL = 0.1  # 最小点击间隔(秒)，防止点击过于频繁
device_states = {}  # 存储每个设备的界面状态
prev_frames = {}  # 存储每个设备的前一帧
STATE_CHANGE_THRESHOLD = 5.0  # 界面变化判断阈值
AUTO_INTERACTION = False  # 是否启用自动交互

# 设置界面状态枚举
class UIState:
    UNKNOWN = "未知界面"
    LOADING = "加载中"
    ERROR = "错误提示"
    NORMAL = "正常界面"
    POPUP = "弹窗界面"
    LOGIN = "登录界面"
    BATTLE = "战斗界面"

# 界面元素类型
class ElementType:
    BUTTON = "按钮"
    TEXT = "文本"
    INPUT = "输入框"
    SLIDER = "滑块"
    UNKNOWN = "未知元素"

# 为每个设备初始化状态
def init_device_state(device_serial):
    device_states[device_serial] = {
        "state": UIState.UNKNOWN,
        "last_state_change": time.time(),
        "elements": [],
        "is_responding": True,
        "last_action": None,
        "action_queue": queue.Queue()
    }

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
        resolution_str = device.shell("wm size").strip().replace("Physical size: ", "")
        
        # 解析分辨率
        width, height = map(int, resolution_str.split('x'))
        
        # 存储设备分辨率信息
        device_resolutions[device.serial] = {
            "width": width,
            "height": height,
            "resolution_str": resolution_str
        }
        
        return f"{brand}-{model}-{resolution_str}"
    except Exception as e:
        print(f"获取设备 {device.serial} 信息失败: {e}")
        # 设置默认分辨率以防失败
        device_resolutions[device.serial] = {
            "width": 1080,
            "height": 2400,
            "resolution_str": "1080x2400"
        }
        return device.serial

# 检测界面变化
def detect_screen_change(device_serial, current_frame):
    if device_serial not in prev_frames:
        prev_frames[device_serial] = current_frame
        return False
    
    # 计算帧差
    prev = prev_frames[device_serial]
    if prev.shape != current_frame.shape:
        prev_frames[device_serial] = current_frame
        return True
    
    diff = cv2.absdiff(prev, current_frame)
    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    mean_diff = np.mean(gray_diff)
    
    # 更新前一帧
    prev_frames[device_serial] = current_frame
    
    # 如果平均差异大于阈值，则认为界面发生变化
    return mean_diff > STATE_CHANGE_THRESHOLD

# 分析界面状态
def analyze_ui_state(device_serial, frame, detection_results):
    # 初始设置为正常界面
    current_state = UIState.NORMAL
    
    # 基于检测结果判断界面状态
    if detection_results and len(detection_results[0].boxes) > 0:
        boxes = detection_results[0].boxes
        
        # 检查是否有加载图标
        for box in boxes:
            cls_id = int(box.cls.item())
            if cls_id >= len(model.names):
                continue  # 跳过无效的类别ID
            class_name = model.names[cls_id]
            
            if "loading" in class_name.lower():
                current_state = UIState.LOADING
                break
            elif "error" in class_name.lower() or "fail" in class_name.lower():
                current_state = UIState.ERROR
                break
            elif "popup" in class_name.lower() or "dialog" in class_name.lower():
                current_state = UIState.POPUP
                break
            elif "login" in class_name.lower():
                current_state = UIState.LOGIN
                break
            elif "battle" in class_name.lower() or "fight" in class_name.lower():
                current_state = UIState.BATTLE
                break
    
    # 更新设备状态
    if device_serial in device_states:
        if device_states[device_serial]["state"] != current_state:
            device_states[device_serial]["state"] = current_state
            device_states[device_serial]["last_state_change"] = time.time()
            print(f"设备 {device_serial} 界面状态变化: {current_state}")
    
    return current_state

# 检测并提取界面元素
def extract_ui_elements(frame, detection_results):
    elements = []
    
    if detection_results and len(detection_results[0].boxes) > 0:
        orig_h, orig_w = frame.shape[:2]
        scale_x, scale_y = orig_w / 640, orig_h / 640
        
        for box in detection_results[0].boxes:
            cls_id = int(box.cls.item())
            conf = box.conf.item()
            class_name = model.names[cls_id]
            
            box_x, box_y, box_w, box_h = box.xywh[0].tolist()
            box_x, box_y, box_w, box_h = box_x * scale_x, box_y * scale_y, box_w * scale_x, box_h * scale_y
            
            # 确定元素类型
            element_type = ElementType.UNKNOWN
            if "button" in class_name.lower() or class_name.startswith("operation-"):
                element_type = ElementType.BUTTON
            elif "text" in class_name.lower():
                element_type = ElementType.TEXT
            elif "input" in class_name.lower():
                element_type = ElementType.INPUT
            elif "slider" in class_name.lower():
                element_type = ElementType.SLIDER
            
            elements.append({
                "type": element_type,
                "class": class_name,
                "confidence": conf,
                "x": int(box_x),
                "y": int(box_y),
                "width": int(box_w),
                "height": int(box_h)
            })
    
    return elements

# 自动交互决策
def decide_auto_action(device_serial, elements, current_state):
    if not AUTO_INTERACTION:
        return None
    
    # 没有元素可交互
    if not elements:
        return None
    
    # 根据界面状态决定操作
    if current_state == UIState.ERROR:
        # 在错误界面，寻找确认按钮
        for element in elements:
            if element["type"] == ElementType.BUTTON and (
                    "confirm" in element["class"].lower() or 
                    "ok" in element["class"].lower() or 
                    "close" in element["class"].lower()):
                return {
                    "action": "tap",
                    "x": element["x"],
                    "y": element["y"],
                    "element": element
                }
    
    elif current_state == UIState.POPUP:
        # 处理弹窗，通常是关闭或确认
        for element in elements:
            if element["type"] == ElementType.BUTTON and (
                    "close" in element["class"].lower() or 
                    "confirm" in element["class"].lower()):
                return {
                    "action": "tap",
                    "x": element["x"],
                    "y": element["y"],
                    "element": element
                }
    
    elif current_state == UIState.LOADING:
        # 加载中，等待
        return {
            "action": "wait",
            "duration": 1.0
        }
    
    return None

# 执行交互动作
def execute_action(device, action):
    if not action:
        return
    
    if action["action"] == "tap":
        execute_tap(device, action["x"], action["y"], 
                    action.get("element", {}).get("class", None))
    elif action["action"] == "wait":
        # 等待指定时间，这里不阻塞线程
        time.sleep(action.get("duration", 0.5))
    
    # 记录上一次动作
    device_states[device.serial]["last_action"] = action
    print(f"设备 {get_device_name(device)} 自动执行: {action['action']}")

# 执行点击的线程函数，以非阻塞方式执行点击
def execute_tap(device, x, y, button_class=None):
    try:
        # 确保坐标在有效范围内
        res = device_resolutions.get(device.serial, {"width": 1080, "height": 2400})
        x = max(0, min(int(x), res["width"]))
        y = max(0, min(int(y), res["height"]))
        
        # 直接执行adb shell命令
        device.shell(f"input tap {x} {y}")
        
        # 可选的点击日志输出
        if button_class:
            print(f"点击设备 {get_device_name(device)}: {button_class} at ({x}, {y})")
        else:
            print(f"点击设备 {get_device_name(device)}: 未识别按钮 at ({x}, {y})")
    except Exception as e:
        print(f"点击设备 {get_device_name(device)} 失败: {e}")

# 转换点击坐标，根据设备分辨率进行适配
def adapt_coordinates(source_serial, target_serial, x, y):
    # 如果没有分辨率信息，返回原坐标
    if source_serial not in device_resolutions or target_serial not in device_resolutions:
        return x, y
        
    # 获取源设备和目标设备的分辨率
    source_res = device_resolutions[source_serial]
    target_res = device_resolutions[target_serial]
    
    # 计算点击位置在源设备上的比例
    x_ratio = x / source_res["width"]
    y_ratio = y / source_res["height"]
    
    # 根据比例计算在目标设备上的坐标
    target_x = int(x_ratio * target_res["width"])
    target_y = int(y_ratio * target_res["height"])
    
    return target_x, target_y

# 鼠标点击回调
def on_mouse(event, x, y, flags, param):
    global script, save_path, model, click_counts, multi_devices_control, click_threads, last_click_time
    serial = param["serial"]
    frame = param["frame"]
    results = param["results"]
    device = next(d for d in devices if d.serial == serial)

    if event == cv2.EVENT_LBUTTONDOWN:
        # 防止点击过于频繁导致设备反应不过来
        current_time = time.time()
        if current_time - last_click_time < MIN_CLICK_INTERVAL:
            return
        last_click_time = current_time
        
        orig_h, orig_w = frame.shape[:2]
        scale_x, scale_y = orig_w / 640, orig_h / 640
        matched = False
        
        # 清理已完成的点击线程
        click_threads = [t for t in click_threads if t.is_alive()]

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
                            "remark": "待命名"
                        }
                        script["steps"].append(step)
                        
                        # 非阻塞方式更新JSON文件
                        def save_json():
                            with open(save_path, "w", encoding="utf-8") as f:
                                json.dump(script, f, indent=4, ensure_ascii=False)
                        json_thread = Thread(target=save_json)
                        json_thread.daemon = True
                        json_thread.start()
                        
                        print("\n" + "=" * 50)
                        print(f"【按钮动作录入】: {button_class}，步骤 {step['step']} 已保存至 {save_path}")
                        print("=" * 50 + "\n")
                    
                    # 执行点击（录制模式或交互模式）
                    # 一机多控功能：同步点击所有设备
                    if multi_devices_control and device.serial == main_device.serial:
                        # 首先处理主设备自身的点击，以减少延迟
                        t = Thread(target=execute_tap, args=(device, box_x, box_y, button_class))
                        t.daemon = True
                        t.start()
                        click_threads.append(t)
                        
                        # 并行处理其他设备的点击
                        for dev in devices:
                            if dev.serial != device.serial:
                                # 根据目标设备分辨率转换坐标
                                target_x, target_y = adapt_coordinates(device.serial, dev.serial, box_x, box_y)
                                t = Thread(target=execute_tap, args=(dev, target_x, target_y, button_class))
                                t.daemon = True
                                t.start()
                                click_threads.append(t)
                    else:
                        # 单设备操作
                        t = Thread(target=execute_tap, args=(device, box_x, box_y, button_class))
                        t.daemon = True
                        t.start()
                        click_threads.append(t)
                    return

        # 未识别按钮处理
        # 修改：所有录制模式都记录未识别的点击
        if is_recording:  # 同时适用于 --record 和 --record-no-match
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
            
            # 非阻塞方式更新JSON文件
            def save_json():
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(script, f, indent=4, ensure_ascii=False)
            json_thread = Thread(target=save_json)
            json_thread.daemon = True
            json_thread.start()
            
            print("\n" + "=" * 50)
            print(f"【未识别点击录入】: 比例坐标 ({rel_x:.3f}, {rel_y:.3f})，步骤 {step['step']} 已保存至 {save_path}")
            print("=" * 50 + "\n")
        
        # 执行点击（对所有未匹配的点击）
        if multi_devices_control and device.serial == main_device.serial:
            # 首先处理主设备自身的点击，以减少延迟
            t = Thread(target=execute_tap, args=(device, x, y))
            t.daemon = True
            t.start()
            click_threads.append(t)
            
            # 并行处理其他设备的点击
            for dev in devices:
                if dev.serial != device.serial:
                    # 根据目标设备分辨率转换坐标
                    target_x, target_y = adapt_coordinates(device.serial, dev.serial, x, y)
                    t = Thread(target=execute_tap, args=(dev, target_x, target_y))
                    t.daemon = True
                    t.start()
                    click_threads.append(t)
        else:
            # 单设备操作
            t = Thread(target=execute_tap, args=(device, x, y))
            t.daemon = True
            t.start()
            click_threads.append(t)

# 设备屏幕捕获和分析线程
def capture_and_analyze_device(device, screenshot_queue):
    last_time = time.time()
    
    while True:
        try:
            # 计算是否需要暂停来控制速率
            current_time = time.time()
            elapsed = current_time - last_time
            if elapsed < 0.03:  # 约30FPS
                time.sleep(0.01)  # 短暂休眠，避免CPU过度使用
                continue
                
            last_time = current_time
            
            # 队列已满，跳过此帧
            if screenshot_queue.full():
                continue
                
            # 获取屏幕截图
            screenshot = device.screenshot()
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 检测屏幕变化和UI状态
            has_changed = detect_screen_change(device.serial, frame)
            
            # 只有在屏幕变化或没有之前的帧时才执行完整分析
            if has_changed or device.serial not in prev_frames:
                # 使用YOLO模型预测
                results = model.predict(frame, conf=0.4, verbose=False)
                
                # 分析界面状态
                current_state = analyze_ui_state(device.serial, frame, results)
                
                # 提取界面元素
                elements = extract_ui_elements(frame, results)
                
                # 更新设备状态
                if device.serial in device_states:
                    device_states[device.serial]["elements"] = elements
                
                # 决定自动操作
                if AUTO_INTERACTION:
                    action = decide_auto_action(device.serial, elements, current_state)
                    if action:
                        # 将动作放入设备的动作队列
                        device_states[device.serial]["action_queue"].put(action)
                
                # 将带有分析结果的帧放入队列
                screenshot_queue.put((device.serial, frame, results))
            else:
                # 如果屏幕没有变化，只传递帧，不包含分析结果
                screenshot_queue.put((device.serial, frame, None))
            
            # 处理设备的动作队列
            if device.serial in device_states and not device_states[device.serial]["action_queue"].empty():
                action = device_states[device.serial]["action_queue"].get(block=False)
                execute_action(device, action)
            
        except queue.Full:
            # 队列满了，可能处理速度跟不上，略过
            pass
        except Exception as e:
            print(f"获取设备 {get_device_name(device)} 截图失败: {e}")
            time.sleep(0.5)  # 错误后稍等长一点再重试

# 解析命令行参数
parser = argparse.ArgumentParser(description="Record game operation script")
parser.add_argument("--record", action="store_true", help="Enable recording mode")
parser.add_argument("--record-no-match", action="store_true", help="Record clicks without matched buttons")
parser.add_argument("--multi-devices-control", action="store_true", help="启用一机多控功能，主设备点击同步到所有设备")
parser.add_argument("--main-device", type=str, help="指定主设备序列号，如不指定则使用第一个连接的设备")
parser.add_argument("--auto-interaction", action="store_true", help="启用自动交互功能，自动处理常见界面事件")
args = parser.parse_args()

# 自动连接 ADB 设备
try:
    devices = adb.device_list()
    if not devices:
        raise Exception("未检测到 ADB 设备，请检查连接和 USB 调试")
        
    # 获取设备信息和分辨率
    device_names = {}
    for d in devices:
        device_names[d.serial] = get_device_name(d)
        # 在这里get_device_name函数已经将分辨率存入了device_resolutions字典
        # 初始化设备状态
        init_device_state(d.serial)
    
    # 设置主设备
    if args.main_device:
        main_device = next((d for d in devices if d.serial == args.main_device), None)
        if not main_device:
            print(f"警告: 未找到指定的主设备 {args.main_device}，使用第一个设备作为主设备")
            main_device = devices[0]
    else:
        main_device = devices[0]
    
    # 设置一机多控模式
    multi_devices_control = args.multi_devices_control
    
    print(f"已连接设备: {[device_names[d.serial] for d in devices]}")
    print(f"主设备: {device_names[main_device.serial]}" + (" [Main]" if multi_devices_control else ""))
    if multi_devices_control:
        print("已启用一机多控功能: 主设备的操作将同步到所有设备")
        print("设备分辨率信息:")
        for serial, res in device_resolutions.items():
            device = next(d for d in devices if d.serial == serial)
            print(f"  - {device_names[serial]}: {res['resolution_str']}")
    
    if AUTO_INTERACTION:
        print("已启用自动交互功能: 将自动处理常见界面事件")
except Exception as e:
    print(f"ADB 初始化失败: {e}")
    sys.exit(1)

# 加载模型
try:
    # 使用相对路径加载模型
    model_path = os.path.join(PROJECT_ROOT, "datasets", "train", "weights", "best.pt")
    if not os.path.exists(model_path):
        # 尝试备用路径
        alternate_model_path = os.path.join(PROJECT_ROOT, "..", "GameAI", "outputs", "train", "weights", "best.pt")
        if os.path.exists(alternate_model_path):
            model_path = alternate_model_path
        else:
            print(f"错误：模型文件不存在 {model_path}")
            print("请确保模型文件位于正确的位置")
            sys.exit(1)
    
    model = YOLO(model_path)
    print(f"已加载模型：{model_path}")
except Exception as e:
    print(f"模型加载失败: {e}")
    sys.exit(1)

# 判断是否为录制模式
is_recording = args.record or args.record_no_match  # 任意一个为 True 即进入录制模式

# 录制模式生成保存路径
if is_recording:
    # 使用相对路径
    output_dir = os.path.join(PROJECT_ROOT, "testcase")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    save_path = os.path.join(output_dir, f"scene1_{timestamp}.json")
    print(f"录制文件将保存至: {save_path}")

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
    t = Thread(target=capture_and_analyze_device, args=(device, screenshot_queue), daemon=True)
    t.start()
    threads.append(t)

# 主循环显示所有设备
windows = {}
for d in devices:
    # 为主设备添加[Main]标识
    if d.serial == main_device.serial:
        windows[d.serial] = f"[Main] Device {get_device_name(d)}"
    else:
        windows[d.serial] = f"Device {get_device_name(d)}"
        
frame_buffers = {d.serial: None for d in devices}
results_buffers = {d.serial: None for d in devices}

while True:
    try:
        serial, frame, results = screenshot_queue.get(timeout=1)
        frame_for_detection = cv2.resize(frame, (640, 640))
        results_for_detection = model.predict(source=frame_for_detection, device="mps", imgsz=640, conf=0.6)

        # 更新缓冲区
        frame_buffers[serial] = frame
        results_buffers[serial] = results_for_detection

        annotated_frame = frame.copy()
        if results_for_detection:
            orig_h, orig_w = frame.shape[:2]
            scale_x, scale_y = orig_w / 640, orig_h / 640
            for box in results_for_detection[0].boxes:
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
        cv2.setMouseCallback(windows[serial], on_mouse, param={"serial": serial, "frame": frame, "results": results_for_detection})

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