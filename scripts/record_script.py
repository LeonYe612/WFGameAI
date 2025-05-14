def on_mouse(event, x, y, flags, param):
    pass

# 设备屏幕捕获线程
def capture_device(device, screenshot_queue):
    pass

# 控制刷新率
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