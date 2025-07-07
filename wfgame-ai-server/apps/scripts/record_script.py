# 完全抑制所有不必要的输出
import warnings
import logging
import sys
import os

warnings.filterwarnings("ignore")
os.environ["YOLO_VERBOSE"] = "False"
os.environ["ULTRALYTICS_VERBOSE"] = "False"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["PYTHONIOENCODING"] = "utf-8"

# 设置所有相关日志级别为ERROR
logging.getLogger().setLevel(logging.ERROR)
logging.getLogger("ultralytics").setLevel(logging.ERROR)
logging.getLogger("utils").setLevel(logging.ERROR)
logging.getLogger("yolov5").setLevel(logging.ERROR)
logging.getLogger("PIL").setLevel(logging.ERROR)
logging.getLogger("matplotlib").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)
logging.getLogger("torchvision").setLevel(logging.ERROR)



import cv2
import numpy as np
from ultralytics import YOLO
import json
import time
import tempfile  # 添加tempfile导入用于临时文件处理
from datetime import datetime
from adbutils import adb
import argparse
import os
import signal
import sys
import traceback
from threading import Thread
import queue
import subprocess
import importlib.util
import warnings
import logging

# 完全抑制所有不必要的输出
warnings.filterwarnings("ignore")
os.environ["YOLO_VERBOSE"] = "False"
os.environ["ULTRALYTICS_VERBOSE"] = "False"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# 设置日志级别
logging.getLogger().setLevel(logging.ERROR)
logging.getLogger("ultralytics").setLevel(logging.ERROR)
logging.getLogger("utils").setLevel(logging.ERROR)
logging.getLogger("yolov5").setLevel(logging.ERROR)
logging.getLogger("PIL").setLevel(logging.ERROR)
logging.getLogger("matplotlib").setLevel(logging.ERROR)


# 确保项目根目录在sys.path中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 统一只从项目根目录导入utils模块
try:
    # 直接从项目根目录导入所有需要的工具函数
    from utils import get_project_root, get_weights_dir, get_scripts_dir, get_testcase_dir, load_yolo_model
    print("从项目根目录utils.py导入了所需函数")

    # 使用配置文件中的路径
    WEIGHTS_DIR = get_weights_dir()
    PROJECT_ROOT = get_project_root()
    SCRIPTS_DIR = get_scripts_dir()
    TESTCASE_DIR = get_testcase_dir()
    print(f"使用路径配置: PROJECT_ROOT={PROJECT_ROOT}, SCRIPTS_DIR={SCRIPTS_DIR}, TESTCASE_DIR={TESTCASE_DIR}, WEIGHTS_DIR={WEIGHTS_DIR}")
except ImportError as e:
    print(f"从项目根目录导入utils模块失败: {e}")
    print("此功能依赖于项目根目录中的utils.py，请确保其存在并包含所需功能")
    sys.exit(1)

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
# 滑动相关变量
drag_start_pos = {}  # 存储每个设备的拖拽起始位置 {serial: (x, y, time)}
is_dragging = {}  # 存储每个设备的拖拽状态 {serial: bool}
DRAG_MIN_DISTANCE = 10  # 最小拖拽距离(像素)，小于此距离视为点击
SWIPE_DURATION = 300  # 默认滑动持续时间(毫秒)
prev_frames = {}  # 存储每个设备的前一帧
STATE_CHANGE_THRESHOLD = 5.0  # 界面变化判断阈值
AUTO_INTERACTION = False  # 是否启用自动交互
WINDOWS_DISPLAY_SCALE = 0.5 if sys.platform == "win32" else 1.0  # Windows下显示缩放比例调整为50%
WINDOW_SIZES = {}  # 存储每个窗口的固定显示尺寸
USER_WINDOW_SIZES = {}  # 存储用户调整后的窗口尺寸
# 选择正确的推理设备
DEVICE = "cuda" if sys.platform == "win32" else "mps" if sys.platform == "darwin" else "cpu"
print(f"使用推理设备: {DEVICE}")

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

# 在系统信号处理中添加安全清理
def safe_cleanup():
    """程序退出时安全清理资源"""
    try:
        print("\n执行安全清理...")

        # 保存录制文件
        if is_recording and script["steps"]:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(script, f, indent=4, ensure_ascii=False)
                print(f"脚本已保存至: {save_path}")
            except Exception as save_err:
                print(f"保存脚本失败: {save_err}")

        # 关闭所有窗口
        try:
            cv2.destroyAllWindows()
        except:
            pass        # 重置ADB连接
        try:
            for device in devices:
                try:
                    # 尝试断开连接，确保下次连接正常
                    device_id = device.serial
                    if device_id and ":" in device_id:  # 无线设备
                        subprocess.run(['adb', 'disconnect', device_id], check=False)
                except:
                    pass
        except:
            pass
    except Exception as cleanup_err:
        print(f"清理过程出错: {cleanup_err}")

# 优雅退出处理
def signal_handler(sig, frame):
    print("\n收到 Ctrl+C，正在安全退出...")
    safe_cleanup()
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
        boxes = detection_results[0].boxes        # 检查是否有加载图标
        for box in boxes:
            cls_id = int(box.cls.item())
            if not model or not hasattr(model, 'names') or model.names is None:
                continue  # 跳过无效的模型
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
            if not model or not hasattr(model, 'names') or model.names is None:
                continue  # 跳过无效的模型
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

# 添加设备健康检查函数
def check_device_health(device):
    """检查设备健康状态并尝试恢复"""
    try:
        # 基本连接测试
        result = device.shell("echo health_check", timeout=2)
        if result:
            return True

        return False
    except Exception as e:
        print(f"设备 {get_device_name(device)} 健康检查失败: {e}")

        # 尝试重连
        try:
            print(f"尝试重新连接设备 {get_device_name(device)}...")            # 使用adb命令重新连接
            device_id = device.serial
            if device_id and ":" in device_id:  # 无线设备
                subprocess.run(['adb', 'disconnect', device_id], check=False)
                time.sleep(1)
                subprocess.run(['adb', 'connect', device_id], check=False)
            time.sleep(2)

            # 再次测试
            try:
                if device.shell("echo reconnected", timeout=2):
                    print(f"设备 {get_device_name(device)} 重连成功")
                    return True
            except:
                pass
        except:
            pass

        return False

# 修改执行点击函数，增加错误处理
def execute_tap(device, x, y, button_class=None):
    """
    以非阻塞方式执行点击，增强错误处理
    """
    try:
        # 确保设备连接正常
        try:
            device.shell("echo tap_check", timeout=1)
        except Exception as conn_err:
            print(f"点击前设备连接检查失败: {conn_err}")
            # 尝试重连
            if not check_device_health(device):
                print(f"设备 {get_device_name(device)} 不可用，点击操作取消")
                return False

        # 确保坐标在有效范围内
        res = device_resolutions.get(device.serial, {"width": 1080, "height": 2400})
        x = max(0, min(int(x), res["width"]))
        y = max(0, min(int(y), res["height"]))

        # 直接执行adb shell命令
        device.shell(f"input tap {x} {y}")        # 可选的点击日志输出
        if button_class:
            print(f"点击设备 {get_device_name(device)}: {button_class} at ({x}, {y})")
        else:
            print(f"点击设备 {get_device_name(device)}: 未识别按钮 at ({x}, {y})")

        return True
    except Exception as e:
        print(f"点击设备 {get_device_name(device)} 失败: {e}")
        return False

def execute_swipe(device, start_x, start_y, end_x, end_y, duration=300):
    """
    以非阻塞方式执行滑动，增强错误处理
    """
    try:
        # 确保设备连接正常
        try:
            device.shell("echo swipe_check", timeout=1)
        except Exception as conn_err:
            print(f"滑动前设备连接检查失败: {conn_err}")
            # 尝试重连
            if not check_device_health(device):
                print(f"设备 {get_device_name(device)} 不可用，滑动操作取消")
                return False

        # 确保坐标在有效范围内
        res = device_resolutions.get(device.serial, {"width": 1080, "height": 2400})
        start_x = max(0, min(int(start_x), res["width"]))
        start_y = max(0, min(int(start_y), res["height"]))
        end_x = max(0, min(int(end_x), res["width"]))
        end_y = max(0, min(int(end_y), res["height"]))

        # 确保持续时间在合理范围内
        duration = max(100, min(int(duration), 5000))  # 100ms到5000ms之间

        # 执行adb shell滑动命令
        device.shell(f"input swipe {start_x} {start_y} {end_x} {end_y} {duration}")

        print(f"滑动设备 {get_device_name(device)}: ({start_x}, {start_y}) -> ({end_x}, {end_y}), {duration}ms")

        return True
    except Exception as e:
        print(f"滑动设备 {get_device_name(device)} 失败: {e}")
        return False

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
    global drag_start_pos, is_dragging

    if event == cv2.EVENT_LBUTTONDOWN:
        serial = param["serial"]
        frame = param["frame"]
        results = param["results"]
        device = next(d for d in devices if d.serial == serial)

        # 获取当前显示尺寸
        window_name = windows[serial]
        current_size = get_window_size(window_name)
        if not current_size:
            current_size = USER_WINDOW_SIZES[serial]

        # 计算点击坐标相对于原始图像的位置
        orig_h, orig_w = frame.shape[:2]
        display_w, display_h = current_size

        # 转换点击坐标到原始图像坐标
        orig_x = int(x * (orig_w / display_w))
        orig_y = int(y * (orig_h / display_h))

        # 记录拖拽起始位置
        drag_start_pos[serial] = (orig_x, orig_y, time.time())
        is_dragging[serial] = False

        # 防止点击过于频繁导致设备反应不过来
        current_time = time.time()
        if not hasattr(on_mouse, 'last_click_time'):
            on_mouse.last_click_time = 0
        if current_time - on_mouse.last_click_time < MIN_CLICK_INTERVAL:
            return
        on_mouse.last_click_time = current_time

        matched = False

        # 清理已完成的点击线程
        click_threads = [t for t in click_threads if t.is_alive()]

        if results and len(results[0].boxes) > 0:
            for box in results[0].boxes:
                box_x, box_y, box_w, box_h = box.xywh[0].tolist()
                box_x, box_y, box_w, box_h = box_x * orig_w/640, box_y * orig_h/640, box_w * orig_w/640, box_h * orig_h/640
                left, top = int(box_x - box_w/2), int(box_y - box_h/2)
                right, bottom = int(box_x + box_w/2), int(box_y + box_h/2)                # 使用转换后的坐标进行碰撞检测
                if left <= orig_x <= right and top <= orig_y <= bottom:
                    cls_id = int(box.cls.item())
                    conf = box.conf.item()
                    if not model or not hasattr(model, 'names') or model.names is None:
                        continue  # 跳过无效的模型
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
                            "action": "click",  # 默认动作类型
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

                    # 执行点击
                    if multi_devices_control and device.serial == main_device.serial:
                        # 首先处理主设备自身的点击
                        t = Thread(target=execute_tap, args=(device, box_x, box_y, button_class))
                        t.daemon = True
                        t.start()
                        click_threads.append(t)

                        # 并行处理其他设备的点击
                        for dev in devices:
                            if dev.serial != device.serial:
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
        if args.record_no_match:  # 只在增强录制模式下记录未识别按钮
            rel_x, rel_y = x / orig_w, y / orig_h
            step = {
                "step": len(script["steps"]) + 1,
                "action": "click",  # 默认动作类型
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
            # 首先处理主设备自身的点击
            t = Thread(target=execute_tap, args=(device, orig_x, orig_y))
            t.daemon = True
            t.start()
            click_threads.append(t)

            # 并行处理其他设备的点击
            for dev in devices:
                if dev.serial != device.serial:
                    target_x, target_y = adapt_coordinates(device.serial, dev.serial, orig_x, orig_y)
                    t = Thread(target=execute_tap, args=(dev, target_x, target_y))
                    t.daemon = True
                    t.start()
                    click_threads.append(t)
        else:
            # 单设备操作
            t = Thread(target=execute_tap, args=(device, orig_x, orig_y))
            t.daemon = True
            t.start()
            click_threads.append(t)

    elif event == cv2.EVENT_MOUSEMOVE:
        # 处理鼠标移动事件，检测拖拽
        serial = param["serial"]
        if serial in drag_start_pos and not is_dragging[serial]:
            # 计算移动距离
            start_x, start_y, start_time = drag_start_pos[serial]

            # 获取当前显示尺寸并转换坐标
            frame = param["frame"]
            window_name = windows[serial]
            current_size = get_window_size(window_name)
            if not current_size:
                current_size = USER_WINDOW_SIZES[serial]

            orig_h, orig_w = frame.shape[:2]
            display_w, display_h = current_size
            orig_x = int(x * (orig_w / display_w))
            orig_y = int(y * (orig_h / display_h))

            distance = ((orig_x - start_x) ** 2 + (orig_y - start_y) ** 2) ** 0.5

            if distance >= DRAG_MIN_DISTANCE:
                is_dragging[serial] = True
                print(f"检测到拖拽开始: {serial}, 距离: {distance:.1f}")

    elif event == cv2.EVENT_LBUTTONUP:
        # 处理鼠标松开事件，完成拖拽或点击
        serial = param["serial"]
        if serial in drag_start_pos:
            start_x, start_y, start_time = drag_start_pos[serial]

            # 获取当前显示尺寸并转换坐标
            frame = param["frame"]
            window_name = windows[serial]
            current_size = get_window_size(window_name)
            if not current_size:
                current_size = USER_WINDOW_SIZES[serial]

            orig_h, orig_w = frame.shape[:2]
            display_w, display_h = current_size
            orig_x = int(x * (orig_w / display_w))
            orig_y = int(y * (orig_h / display_h))

            # 如果是拖拽操作
            if is_dragging.get(serial, False):
                end_time = time.time()
                duration = int((end_time - start_time) * 1000)  # 转换为毫秒
                if duration < 100:  # 最小持续时间
                    duration = SWIPE_DURATION

                # 录制滑动操作
                if is_recording:
                    step = {
                        "step": len(script["steps"]) + 1,
                        "action": "swipe",
                        "start_x": start_x,
                        "start_y": start_y,
                        "end_x": orig_x,
                        "end_y": orig_y,
                        "duration": duration,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "remark": "滑动操作"
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
                    print(f"【滑动操作录入】: ({start_x}, {start_y}) -> ({orig_x}, {orig_y}), 持续{duration}ms")
                    print(f"步骤 {step['step']} 已保存至 {save_path}")
                    print("=" * 50 + "\n")

                # 执行滑动操作
                device = next(d for d in devices if d.serial == serial)
                if multi_devices_control and device.serial == main_device.serial:
                    # 首先处理主设备自身的滑动
                    t = Thread(target=execute_swipe, args=(device, start_x, start_y, orig_x, orig_y, duration))
                    t.daemon = True
                    t.start()
                    click_threads.append(t)

                    # 并行处理其他设备的滑动
                    for dev in devices:
                        if dev.serial != device.serial:
                            target_start_x, target_start_y = adapt_coordinates(device.serial, dev.serial, start_x, start_y)
                            target_end_x, target_end_y = adapt_coordinates(device.serial, dev.serial, orig_x, orig_y)
                            t = Thread(target=execute_swipe, args=(dev, target_start_x, target_start_y, target_end_x, target_end_y, duration))
                            t.daemon = True
                            t.start()
                            click_threads.append(t)
                else:
                    # 单设备操作
                    t = Thread(target=execute_swipe, args=(device, start_x, start_y, orig_x, orig_y, duration))
                    t.daemon = True
                    t.start()
                    click_threads.append(t)

            # 清理拖拽状态
            if serial in drag_start_pos:
                del drag_start_pos[serial]
            if serial in is_dragging:
                del is_dragging[serial]

# 全局退出标志
exit_flag = False

# 设备屏幕捕获和分析线程
def capture_and_analyze_device(device, screenshot_queue):
    global exit_flag
    last_time = time.time()
    error_count = 0  # 添加错误计数器
    last_error_time = time.time()  # 记录上次错误时间
    consecutive_errors = 0  # 连续错误计数

    while not exit_flag:
        try:
            # 检查退出标志
            if exit_flag:
                print(f"设备 {get_device_name(device)} 收到退出信号，停止捕获线程")
                break

            # 检查设备连接状态（不使用device.connected属性，改用shell命令测试）
            try:
                device.shell("echo connectivity_check", timeout=1)
                # 如果命令成功执行，设备处于连接状态
            except Exception as conn_err:
                # 命令执行失败，可能是设备已断开
                consecutive_errors += 1
                if consecutive_errors > 5:
                    print(f"设备 {get_device_name(device)} 连接检查失败 {consecutive_errors} 次，停止捕获线程")
                    break
                time.sleep(1)
                continue

            # 添加心跳检测机制
            try:
                device.shell("echo heartbeat", timeout=2)
                # 成功获取心跳响应，重置连续错误计数
                consecutive_errors = 0
            except Exception as hb_err:
                print(f"设备 {get_device_name(device)} 心跳检测失败: {str(hb_err)[:50]}")
                consecutive_errors += 1
                if consecutive_errors > 5:  # 连续5次心跳失败才认为设备断开
                    # 在认为设备彻底断开前尝试重连
                    try:
                        # 尝试重启ADB连接
                        if ":" in device.serial:  # 无线设备
                            print(f"尝试重新连接无线设备 {device.serial}...")
                            subprocess.run(['adb', 'disconnect', device.serial], check=False)
                            time.sleep(1)
                            subprocess.run(['adb', 'connect', device.serial], check=False)
                            time.sleep(2)
                            # 再次测试连接
                            try:
                                if device.shell("echo reconnected", timeout=2):
                                    print(f"设备 {get_device_name(device)} 重连成功")
                                    consecutive_errors = 0
                                    continue
                            except:
                                pass
                    except:
                        pass

                    print(f"设备 {get_device_name(device)} 连接丢失，终止捕获线程")
                    break  # 不抛出异常，直接退出循环
                time.sleep(1)  # 等待一秒再重试
                continue

            # 计算是否需要暂停来控制速率
            current_time = time.time()
            elapsed = current_time - last_time
            if elapsed < 0.03:  # 约30FPS
                time.sleep(0.01)  # 短暂休眠，避免CPU过度使用
                continue

            last_time = current_time

            # 队列已满处理
            if screenshot_queue.full():
                try:
                    # 尝试清除最旧的一帧，确保新帧可以加入
                    screenshot_queue.get_nowait()
                except queue.Empty:
                    pass  # 队列已经被清空，不做处理

            # 获取屏幕截图
            try:
                screenshot = device.screenshot()
                if screenshot is None:
                    raise Exception("获取截图为空")

                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            except Exception as ss_err:
                print(f"获取设备 {get_device_name(device)} 截图失败: {str(ss_err)[:50]}")
                # 截图失败，尝试重置ADB连接
                if consecutive_errors > 3:
                    try:
                        print(f"尝试重置设备 {get_device_name(device)} 的ADB连接...")
                        if ":" in device.serial:  # 无线设备
                            subprocess.run(['adb', 'disconnect', device.serial], check=False)
                            time.sleep(1)
                            subprocess.run(['adb', 'connect', device.serial], check=False)
                        else:  # USB设备
                            subprocess.run(['adb', '-s', device.serial, 'reconnect'], check=False)
                        time.sleep(2)
                    except Exception as reset_err:
                        print(f"重置ADB连接失败: {reset_err}")

                raise  # 重新抛出异常，让外部处理

            # 检测屏幕变化和UI状态
            has_changed = detect_screen_change(device.serial, frame)

            # 只有在屏幕变化或没有之前的帧时才执行完整分析
            if has_changed or device.serial not in prev_frames:                # 使用YOLO模型预测 - 修复检测问题
                # 不再使用cv2.resize，直接保存原始图像让YOLO自己处理
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    temp_path = temp_file.name
                    cv2.imwrite(temp_path, frame)

                try:
                    if model and hasattr(model, 'predict'):                        # 导入ThresholdConfig以使用统一的阈值管理
                        try:
                            sys.path.append(os.path.join(get_project_root(), 'train_model'))
                            from infer import ThresholdConfig
                            conf_threshold = ThresholdConfig.get_conf_threshold("default")
                        except:
                            conf_threshold = 0.5  # 备用阈值

                        results_for_detection = model.predict(
                            source=temp_path,  # 传入图像路径而不是numpy数组
                            device=DEVICE,
                            imgsz=640,
                            conf=conf_threshold,  # 使用统一的置信度阈值
                            iou=0.6,   # 添加NMS IoU阈值
                            half=True if DEVICE == "cuda" else False,  # 半精度推理
                            max_det=300,  # 最大检测数量
                            verbose=False
                        )
                    else:
                        results_for_detection = None
                except Exception as model_err:
                    print(f"模型预测失败: {model_err}")
                    results_for_detection = None
                finally:
                    # 清理临时文件
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

                # 分析界面状态
                current_state = analyze_ui_state(device.serial, frame, results_for_detection)

                # 提取界面元素
                elements = extract_ui_elements(frame, results_for_detection)

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
                try:
                    screenshot_queue.put((device.serial, frame, results_for_detection), block=False)
                except queue.Full:
                    # 队列满了，尝试再次清理后添加
                    try:
                        screenshot_queue.get_nowait()
                        screenshot_queue.put((device.serial, frame, results_for_detection), block=False)
                    except:
                        pass  # 如果仍然失败，放弃这一帧
            else:
                # 如果屏幕没有变化，只传递帧，不包含分析结果
                try:
                    screenshot_queue.put((device.serial, frame, None), block=False)
                except queue.Full:
                    pass  # 队列满了，放弃这一帧

            # 处理设备的动作队列
            if device.serial in device_states and not device_states[device.serial]["action_queue"].empty():
                try:
                    action = device_states[device.serial]["action_queue"].get(block=False)
                    execute_action(device, action)
                except queue.Empty:
                    pass  # 队列可能在检查和获取之间变空
                except Exception as action_err:
                    print(f"执行设备 {get_device_name(device)} 动作失败: {action_err}")

            # 成功获取和处理一帧，重置错误计数
            if error_count > 0:
                print(f"设备 {get_device_name(device)} 恢复正常")
            error_count = 0
            consecutive_errors = 0

        except RuntimeError as e:
            print(f"设备 {get_device_name(device)} 连接丢失，终止捕获线程")
            break  # 退出循环终止线程
        except Exception as e:
            # 修改错误处理逻辑，限制最大错误次数
            error_count += 1
            consecutive_errors += 1
            current_time = time.time()

            # 控制错误输出频率
            if current_time - last_error_time > 5:
                print(f"设备 {get_device_name(device)} 捕获异常 ({error_count}/20): {str(e)[:100]}")
                last_error_time = current_time

            # 只有在连续错误超过阈值时才退出线程
            if consecutive_errors > 10 or error_count > 20:
                print(f"设备 {get_device_name(device)} 达到最大错误次数，停止捕获线程")
                print(f"连续错误: {consecutive_errors}，总错误: {error_count}")
                break

            # 根据错误次数动态调整等待时间
            wait_time = min(0.5 * consecutive_errors, 5.0)
            time.sleep(wait_time)

# 添加窗口尺寸初始化函数
def init_window_size(device_serial):
    """初始化并固定窗口尺寸"""
    if device_serial not in device_resolutions:
        return (1080, 2400)  # 默认尺寸

    dev_res = device_resolutions[device_serial]
    # 计算显示尺寸
    display_w = int(dev_res["width"] * WINDOWS_DISPLAY_SCALE)
    display_h = int(dev_res["height"] * WINDOWS_DISPLAY_SCALE)
    return (display_w, display_h)

# 移除on_window_resize回调函数，改用更简单的方式
def get_window_size(window_name):
    """获取窗口当前大小"""
    try:
        # 使用cv2.getWindowProperty替代已弃用的getWindowImageSize
        width = int(cv2.getWindowProperty(window_name, cv2.WND_PROP_AUTOSIZE))
        height = int(cv2.getWindowProperty(window_name, cv2.WND_PROP_ASPECT_RATIO))
        if width > 0 and height > 0:
            return (width, height)
        else:
            # 如果无法获取，返回默认大小
            return (800, 600)
    except:
        return None

# 添加设备监控线程
def device_monitor_thread():
    """增强版设备监控线程"""
    last_check_time = time.time()
    adb_restart_time = time.time() - 300  # 初始化为5分钟前，允许立即重启

    while not exit_flag:
        try:
            # 动态更新设备列表
            global devices
            current_devices = adb.device_list()
            active_serials = [d.serial for d in current_devices]

            # 移除已断开设备
            for d in devices[:]:
                if d.serial not in active_serials:
                    print(f"设备 {get_device_name(d)} 已断开，移出设备列表")
                    devices.remove(d)

                    # 清理相关资源
                    if d.serial in device_states:
                        del device_states[d.serial]
                    if d.serial in prev_frames:
                        del prev_frames[d.serial]

                    # 关闭对应窗口
                    try:
                        if d.serial in windows:
                            cv2.destroyWindow(windows[d.serial])
                    except Exception as win_err:
                        print(f"关闭窗口失败: {win_err}")

            # 实现健康检查逻辑
            current_time = time.time()
            if current_time - last_check_time > 30:  # 每30秒执行一次健康检查
                last_check_time = current_time
                print("执行设备健康检查...")

                # 检查每个设备的健康状态
                unhealthy_devices = 0
                for device in devices:
                    try:
                        # 简单的健康检查
                        if not check_device_health(device):
                            print(f"设备 {get_device_name(device)} 健康检查失败")
                            unhealthy_devices += 1
                    except Exception as health_err:
                        print(f"设备 {get_device_name(device)} 健康检查异常: {health_err}")
                        unhealthy_devices += 1

                # 如果所有设备都不健康，尝试重启ADB
                if unhealthy_devices == len(devices) and devices and current_time - adb_restart_time > 300:
                    print("所有设备健康检查失败，尝试重启ADB服务...")
                    try:
                        subprocess.run(['adb', 'kill-server'], check=False)
                        time.sleep(2)
                        subprocess.run(['adb', 'start-server'], check=False)
                        adb_restart_time = current_time
                    except Exception as adb_err:
                        print(f"重启ADB服务失败: {adb_err}")

        except Exception as e:
            print(f"设备监控线程异常: {e}")
            time.sleep(10)

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
    # 先尝试重启ADB服务以确保良好的连接状态
    try:
        print("启动前重置ADB服务...")
        subprocess.run(['adb', 'kill-server'], check=False)
        time.sleep(1)
        subprocess.run(['adb', 'start-server'], check=False)
        time.sleep(2)
    except Exception as adb_err:
        print(f"ADB服务重置失败，但将继续尝试: {adb_err}")

    devices = adb.device_list()
    if not devices:
        raise Exception("未检测到 ADB 设备，请检查连接和 USB 调试")

    # 获取设备信息和分辨率
    device_names = {}
    healthy_devices = []

    print("检查设备连接状态...")
    for d in devices:
        try:
            # 测试设备连接
            if check_device_health(d):
                device_names[d.serial] = get_device_name(d)
                # 在这里get_device_name函数已经将分辨率存入了device_resolutions字典

                # 初始化设备状态
                init_device_state(d.serial)
                healthy_devices.append(d)
            else:
                print(f"设备 {d.serial} 连接不稳定，已排除")
        except Exception as dev_err:
            print(f"设备 {d.serial} 初始化失败: {dev_err}")

    # 更新设备列表为健康设备
    devices = healthy_devices

    if not devices:
        raise Exception("所有检测到的设备都无法正常通信，请检查连接和权限")

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

    print(f"已连接可用设备: {[device_names[d.serial] for d in devices]}")
    print(f"主设备: {device_names[main_device.serial]}" + (" [Main]" if multi_devices_control else ""))
    if multi_devices_control:
        print("已启用一机多控功能: 主设备的操作将同步到所有设备")
        print("设备分辨率信息:")
        for serial, res in device_resolutions.items():
            if serial in [d.serial for d in devices]:  # 只显示活跃设备
                device = next(d for d in devices if d.serial == serial)
                print(f"  - {device_names[serial]}: {res['resolution_str']}")

    # 添加自动交互模式状态
    AUTO_INTERACTION = args.auto_interaction
    if AUTO_INTERACTION:
        print("已启用自动交互功能: 将自动处理常见界面事件")

    # 强制设置较小的截图队列大小，防止内存溢出
    screenshot_queue = queue.Queue(maxsize=5 * len(devices))  # 每个设备5帧
    print(f"截图队列大小: {5 * len(devices)}")

except Exception as e:
    print(f"ADB 初始化失败: {e}")
    sys.exit(1)

# 加载模型
try:
    from utils import get_weights_path
    # 使用项目根目录中的模型加载函数，从配置文件读取模型路径
    print(f"即将加载的模型路径: {get_weights_path()}")

    # 简化参数调用，直接使用工具函数中的配置管理器
    model = load_yolo_model(
        device=DEVICE,  # 只需要指定设备类型
        model_class=YOLO
    )

    if not model:
        print("错误：未能加载模型")
        sys.exit(1)
    print(f"模型加载成功")
except Exception as e:
    print(f"模型加载失败: {e}")
    traceback.print_exc()
    sys.exit(1)

# 判断是否为录制模式
is_recording = args.record or args.record_no_match  # 任意一个为 True 即进入录制模式

# 录制模式生成保存路径
if is_recording:
    # 使用配置中的测试用例目录
    output_dir = TESTCASE_DIR
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    save_path = os.path.join(output_dir, f"scene1_{timestamp}.json")
    print(f"录制文件将保存至: {save_path}")
    # 修改后的启动提示
    print("启动脚本，按 'q' 退出")
    if args.record_no_match:
        print("已进入录制模式，未识别按钮点击将被记录为比例坐标")
    else:
        print("已进入录制模式，仅记录匹配的按钮点击")
else:
    print("已进入调试交互模式，点击窗口直接操作设备，不生成 JSON")

# 启动设备捕获线程
threads = []
for device in devices:
    t = Thread(target=capture_and_analyze_device, args=(device, screenshot_queue), daemon=True)
    t.start()
    threads.append(t)

# 主循环显示所有设备
windows = {}
for d in devices:
    # 初始化窗口尺寸
    WINDOW_SIZES[d.serial] = init_window_size(d.serial)
    USER_WINDOW_SIZES[d.serial] = WINDOW_SIZES[d.serial]  # 初始化用户尺寸

    # 为主设备添加[Main]标识
    if d.serial == main_device.serial:
        windows[d.serial] = f"[Main] Device {get_device_name(d)}"
    else:
        windows[d.serial] = f"Device {get_device_name(d)}"

    # 创建可调整大小的窗口
    cv2.namedWindow(windows[d.serial], cv2.WINDOW_NORMAL)
    cv2.resizeWindow(windows[d.serial], *WINDOW_SIZES[d.serial])

frame_buffers = {d.serial: None for d in devices}
results_buffers = {d.serial: None for d in devices}

# 启动设备监控线程
monitor_thread = Thread(target=device_monitor_thread, daemon=True)
monitor_thread.start()

# 初始化主循环心跳检测时间戳
last_heartbeat = time.time()

while not exit_flag:
    try:
        # 增加主循环心跳检测
        if time.time() - last_heartbeat > 5:
            print("主循环运行中...")
            last_heartbeat = time.time()        # 修改队列获取逻辑，增加超时处理
        try:
            serial, frame, results = screenshot_queue.get(timeout=1)  # 减少超时时间以提高响应速度
        except queue.Empty:
            # 检查退出标志
            if exit_flag:
                print("收到退出信号，退出主循环")
                break

            # 检查设备线程是否存活
            alive_threads = [t.is_alive() for t in threads]
            if not any(alive_threads):
                print("所有设备线程已停止，退出主循环")
                break
            continue        # 修复检测问题：不使用cv2.resize，直接保存原始图像
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_path = temp_file.name
            cv2.imwrite(temp_path, frame)

        try:
            # 导入ThresholdConfig以使用统一的阈值管理
            try:
                import sys
                import os
                sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'train_model'))
                from infer import ThresholdConfig
                conf_threshold = ThresholdConfig.get_conf_threshold("default")
            except ImportError:
                conf_threshold = 0.5  # 后备默认值

            # 使用优化的YOLO参数进行检测
            if model and hasattr(model, 'predict'):
                results_for_detection = model.predict(
                    source=temp_path,  # 传入图像路径
                    device=DEVICE,
                    imgsz=640,
                    conf=conf_threshold,  # 使用统一配置的置信度阈值
                    iou=0.6,   # NMS IoU阈值
                    half=True if DEVICE == "cuda" else False,
                    max_det=300,
                    verbose=False
                )
            else:
                results_for_detection = None
        except Exception as model_err:
            print(f"模型预测失败: {model_err}")
            results_for_detection = None
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
            # 继续执行，使用空结果

        # 检查并更新窗口大小
        window_name = windows[serial]
        current_size = get_window_size(window_name)
        if current_size:
            USER_WINDOW_SIZES[serial] = current_size

        # 使用当前窗口大小显示
        try:
            display_frame = cv2.resize(frame, USER_WINDOW_SIZES[serial])
        except Exception as resize_err:
            print(f"调整图像大小失败: {resize_err}")
            # 使用原始帧
            display_frame = frame

        # 更新缓冲区
        frame_buffers[serial] = display_frame
        results_buffers[serial] = results_for_detection

        try:
            annotated_frame = display_frame.copy()
            if results_for_detection:
                # 使用当前显示尺寸计算检测框
                display_w, display_h = USER_WINDOW_SIZES[serial]

                for box in results_for_detection[0].boxes:
                    x, y, w, h = box.xywh[0].tolist()                    # 转换检测框坐标到显示尺寸
                    x = x * display_w/640
                    y = y * display_h/640
                    w = w * display_w/640
                    h = h * display_h/640

                    cls_id = int(box.cls.item())
                    conf = box.conf.item()
                    cv2.rectangle(annotated_frame,
                                (int(x - w/2), int(y - h/2)),
                                (int(x + w/2), int(y + h/2)),
                                (0, 255, 0), 2)
                    if model and hasattr(model, 'names') and model.names is not None and cls_id < len(model.names):
                        cv2.putText(annotated_frame, f"{model.names[cls_id]} {conf:.2f}",
                                    (int(x - w/2), int(y - h/2 - 10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    else:
                        cv2.putText(annotated_frame, f"Unknown {conf:.2f}",
                                    (int(x - w/2), int(y - h/2 - 10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        except Exception as annotate_err:
            print(f"标注图像失败: {annotate_err}")
            # 使用未标注的帧
            annotated_frame = display_frame

        try:
            cv2.imshow(windows[serial], annotated_frame)
            cv2.setMouseCallback(windows[serial], on_mouse, param={"serial": serial, "frame": frame, "results": results_for_detection})
        except Exception as display_err:
            print(f"显示图像失败: {display_err}")
            # 尝试重新创建窗口
            try:
                cv2.destroyWindow(windows[serial])
                cv2.namedWindow(windows[serial], cv2.WINDOW_NORMAL)
                cv2.resizeWindow(windows[serial], *WINDOW_SIZES[serial])
                cv2.imshow(windows[serial], display_frame)
                cv2.setMouseCallback(windows[serial], on_mouse, param={"serial": serial, "frame": frame, "results": results_for_detection})
            except:
                pass  # 如果重建窗口失败，忽略本次显示

        key = cv2.waitKey(50) & 0xFF
        if key == ord("q"):
            print("退出程序")
            exit_flag = True  # 设置退出标志
            break

        # 检查退出标志
        if exit_flag:
            print("收到退出信号，退出主循环")
            break

    except Exception as e:
        print(f"主循环异常: {str(e)[:200]}")  # 截断过长错误信息
        traceback.print_exc(limit=1)  # 仅打印最后一级堆栈
        time.sleep(1)  # 防止错误循环

        # 检查是否所有设备都已断开
        if not devices:
            print("所有设备已断开，退出程序")
            break

        # 检查退出标志
        if exit_flag:
            print("收到退出信号，退出主循环")
            break

# 修改后的结束逻辑
try:
    if is_recording and script["steps"]:  # 录制模式且有记录时保存
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(script, f, indent=4, ensure_ascii=False)
        print(f"程序结束，最终脚本保存至: {save_path}")
    elif is_recording:  # 录制模式但没记录
        print("程序结束，录制模式未记录任何操作，未生成 JSON")
    else:  # 非录制模式
        print("程序结束，非录制模式，未生成 JSON")

    # 执行资源释放
    print("正在释放资源...")

    # 设置退出标志，强制所有线程退出
    exit_flag = True

    # 等待所有线程结束
    print("等待线程结束...")
    for t in threads:
        if t.is_alive():
            t.join(timeout=3)  # 最多等待3秒

    # 强制清理模型资源，抑制后续输出
    try:
        import gc
        if 'model' in globals():
            del model
        gc.collect()
    except:
        pass

    # 清理所有线程
    try:
        # 向所有队列写入退出信号，确保线程可以安全退出
        for _ in range(len(devices)):
            try:
                screenshot_queue.put(None, block=False)
            except:
                pass
    except:
        pass

    # 释放设备连接
    for device in devices:
        try:
            # 断开无线设备连接
            if ":" in device.serial:
                subprocess.run(['adb', 'disconnect', device.serial], check=False)
        except:
            pass

    # 清空所有队列
    try:
        while not screenshot_queue.empty():
            screenshot_queue.get_nowait()
    except:
        pass

    # 释放OpenCV资源
    for serial in windows:
        try:
            # 尝试关闭特定窗口
            cv2.destroyWindow(windows[serial])
        except:
            pass

finally:
    # 确保窗口被关闭
    cv2.destroyAllWindows()
    print("程序已安全退出")

cv2.destroyAllWindows()