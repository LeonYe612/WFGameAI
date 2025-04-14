from airtest.core.api import touch, exists, snapshot, set_logdir, connect_device, log
from airtest.report.report import LogToHtml
import cv2
import numpy as np
from ultralytics import YOLO
import json
import time
import os
import subprocess
from threading import Thread, Event
import queue
import sys
import argparse
import logging
import shutil
from adbutils import adb
from jinja2 import Environment, FileSystemLoader
import traceback

# 禁用 Ultralytics 的日志输出
logging.getLogger("ultralytics").setLevel(logging.CRITICAL)

# 全局变量
model = None
devices = []
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_TIME = "_" + time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time.time()))
output_dir = "outputs/replaylogs"
report_dir = "outputs/replay_reports"
template_dir = "templates"  # 假设 report_tpl.html 位于项目根目录的 templates 文件夹
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

# 获取设备日志目录
def get_log_dir(dev):
    device_dir = dev.replace(".", "_").replace(":", "_") + CURRENT_TIME
    log_dir = os.path.normpath(os.path.join(output_dir, device_dir))
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "log.txt")
    if not os.path.exists(log_file):
        with open(log_file, "w", encoding="utf-8") as f:
            pass
    return log_dir

# 清理日志目录
def clear_log_dir():
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

# 加载测试进度数据
def load_json_data(run_all):
    json_file = os.path.join(BASE_DIR, 'data.json')
    if not run_all and os.path.isfile(json_file):
        data = json.load(open(json_file))
        data['start'] = time.time()
        return data
    else:
        print(f"清理日志目录: {output_dir}")
        clear_log_dir()
        return {
            'start': time.time(),
            'script': "replay_script",
            'tests': {}
        }

# 单设备回放任务
def replay_device(device, scripts, screenshot_queue, click_queue, result_queue, stop_event, device_name, log_dir):
    if not check_device_status(device, device_name):
        print(f"设备 {device_name} 不可用，跳过回放")
        stop_event.set()
        result_queue.put((device_name, "completed_steps", 0, 0))
        return

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

        print(f"设备 {device_name} 开始执行脚本: {script_path} (循环次数: {loop_count}, 最长运行时间: {max_duration if max_duration != float('inf') else '无限制'}s)")
        log({"msg": f"Start script {script_path}", "success": True})

        start_time = time.time()
        has_max_duration = max_duration != float("inf")
        loops_completed = 0

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

                    log({"msg": f"Step {step_num}: Click {detected_class} at ({x:.1f}, {y:.1f}) - {step_remark}", "success": True})
                    touch([x, y])
                    action_queue.put((device_name, step_num, detected_class, x, y, time.time()))
                    result_queue.put((device_name, step_num, "click", True))
                    completed_steps += 1

                    time.sleep(0.5)
                    disappeared = verify_target_disappeared(device, detected_class)
                    log({"msg": f"Step {step_num}: After click {detected_class} - {'Disappeared' if disappeared else 'Not Disappeared'}", "success": disappeared})
                    snapshot(msg=f"Step {step_num}: After click {detected_class} - {'Disappeared' if disappeared else 'Not Disappeared'}")

                    if script_idx < len(scripts) - 1 and step == steps[-1]:
                        if not disappeared:
                            print(f"设备 {device_name} 脚本 {script_path} 最后一步 {step_num} 执行失败，停止后续脚本")
                            log({"msg": f"Step {step_num}: Failed - Target {detected_class} did not disappear", "success": False})
                            stop_event.set()
                            return
                else:
                    if step_class == "unknown":
                        step_counter += 1
                        step_num = step_counter
                        h, w = frame.shape[:2]
                        x, y = step.get("relative_x", 0.5) * w, step.get("relative_y", 0.5) * h

                        log({"msg": f"Step {step_num}: Click unknown at ({x:.1f}, {y:.1f}) - {step_remark}", "success": True})
                        touch([x, y])
                        action_queue.put((device_name, step_num, "unknown", x, y, time.time()))
                        result_queue.put((device_name, step_num, "click", True))
                        completed_steps += 1
                        time.sleep(3)
                        snapshot(msg=f"Step {step_num}: Click unknown at ({x:.1f}, {y:.1f})")
                    else:
                        print(f"设备 {device_name} 未检测到目标按钮 {step_class}，等待下一轮检测")
                        log({"msg": f"Step {step_counter + 1}: No target {step_class} detected, waiting for next detection", "success": False})
                        cv2.imwrite(os.path.join(log_dir, f"failed_detection_step_{step_counter + 1}_{timestamp}.jpg"), frame)
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

# 为单台设备生成测试报告
def run_one_report(dev, device_name):
    try:
        log_dir = get_log_dir(device_name)
        log_file = os.path.join(log_dir, 'log.txt')

        print(f"log_dir: {log_dir}")
        print(f"log_file: {log_file}")

        report_file = os.path.join(log_dir, "report", "log.html")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)

        if os.path.isfile(log_file):
            # 使用 LogToHtml 直接生成报告
            # 创建临时 .air 目录（模仿 Airtest 的脚本目录结构）
            temp_air_dir = os.path.join(log_dir, "temp_script.air")
            os.makedirs(temp_air_dir, exist_ok=True)
            # 在目录下创建 main.py 文件
            with open(os.path.join(temp_air_dir, "temp_script.py"), "w") as f:
                f.write("")  # 空文件即可，LogToHtml 只需文件存在

            # 使用 temp_air_dir 作为 script_root
            report = LogToHtml(script_root=temp_air_dir, log_root=log_dir)
            report.report(output_file=report_file)

            # 清理临时目录
            if os.path.exists(temp_air_dir):
                shutil.rmtree(temp_air_dir)

            return {
                'status': 0 if os.path.exists(report_file) else 1,  # 0: success, 1: failed
                'path': report_file if os.path.exists(report_file) else ''
            }
        else:
            print(f"Report build failed. File not found in dir {log_file}")
    except Exception as e:
        print(f"设备 {device_name} 的报告生成失败: {e}")
        traceback.print_exc()
    return {'status': -1, 'device': dev, 'path': ''}

# 生成汇总报告
def run_summary(data):
    report_url = f"summary_report{CURRENT_TIME}.html"
    report_url_dir = os.path.join(report_dir, report_url)

    try:
        summary = {
            'time': "%.3f" % (time.time() - data['start']),
            'success': sum(1 for item in data['tests'].values() if item['status'] == 0),
            'count': len(data['tests'])
        }
        summary.update(data)
        summary['start'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data['start']))

        # 将单设备报告路径转换为相对路径，并确保 path 始终有值
        for device, report_info in summary['tests'].items():
            if 'path' in report_info and report_info['path']:
                # 计算从 summary_report 到 log.html 的相对路径
                abs_report_path = report_info['path']
                rel_path = os.path.relpath(abs_report_path, start=report_dir)
                report_info['path'] = rel_path
            else:
                report_info['path'] = "#"  # 如果路径为空，设置为占位符，避免跳转失败

        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('report_tpl.html')

        with open(report_url_dir, "w", encoding="utf-8") as f:
            html_content = template.render(data=summary)
            f.write(html_content)
        print(f"汇总报告生成: {report_url_dir}")
        return report_url_dir
    except Exception as e:
        print(f"汇总报告生成失败: {e}")
        traceback.print_exc()
        return ""

# 在多台设备上并行运行测试
def run_on_multi_device(devices, scripts, results, run_all, device_names):
    tasks = []
    for device in devices:
        serial = device.serial
        device_name = device_names[serial]
        print(f"⚠️ 当前测试设备: {device_name}")
        if not run_all and device_name in results['tests'] and results['tests'][device_name]['status'] == 0:
            print(f"❌ 跳过设备 {device_name}")
            continue

        log_dir = get_log_dir(device_name)
        t = Thread(target=replay_device, args=(
            device, scripts, screenshot_queue, action_queue, queue.Queue(), Event(), device_name, log_dir))
        t.daemon = True
        t.start()
        tasks.append({
            'thread': t,
            'dev': device_name,
            'log_dir': log_dir
        })
    return tasks

# 主测试流程
def run(devices, scripts, device_names, run_all=False):
    results = load_json_data(run_all)
    tasks = run_on_multi_device(devices, scripts, results, run_all, device_names)
    success_count = 0

    for task in tasks:
        task['thread'].join()
        device_report = run_one_report(task['dev'], task['dev'])
        results['tests'][task['dev']] = device_report
        if device_report['status'] == 0:
            success_count += 1

    summary_report_url = run_summary(results)
    result_str = f"成功 {success_count}/{len(tasks)}"
    return result_str, summary_report_url

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

    try:
        result, report_url = run(devices, loaded_scripts, device_names, run_all=False)
        print(f"执行结果: {result}, 报告地址: {report_url}")
        return True
    except Exception as e:
        print(f"回放失败: {e}")
        return False

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
                script_config["loop_count"] = loop_counts[i]
            if i < len(max_durations):
                script_config["max_duration"] = max_durations[i]
            scripts.append(script_config)

    if not scripts:
        parser.error("必须使用 --steps 指定至少一个脚本文件")

    global devices, model
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