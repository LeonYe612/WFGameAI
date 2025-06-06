# Device Screen Analyzer - 使用指南

Device Screen Analyzer 是一个强大的实时设备屏幕元素识别工具，它结合了设备连接管理、截图捕获和 YOLO 模型推理功能，专门使用 best.pt 模型对连接设备的屏幕进行实时 UI 元素识别和分析。

## 主要功能

### 🔥 核心特性
- **自动设备检测**: 自动检测所有连接的 ADB 设备
- **实时截图捕获**: 使用 Airtest 框架进行高效截图
- **AI 元素识别**: 使用训练好的 best.pt YOLO 模型进行 UI 元素检测
- **可视化结果**: 在截图上标注识别结果，包括边界框、类别和置信度
- **多设备支持**: 支持同时分析多个连接的设备
- **连续监控**: 支持定时连续分析，实时监控设备状态
- **结果导出**: 自动保存分析结果、可视化图像和结构化数据

### 📊 输出内容
- 带标注的可视化结果图像
- 原始截图备份
- 详细的 JSON 格式检测数据
- 分析会话统计报告

## 安装要求

确保已安装以下依赖：
```bash
pip install ultralytics opencv-python adbutils airtest-selenium numpy
```

## 使用方法

### 1. 列出连接的设备
```bash
python device_screen_analyzer.py --list-devices
```

### 2. 单次截图分析
```bash
# 分析所有连接的设备
python device_screen_analyzer.py --single-shot

# 分析指定设备
python device_screen_analyzer.py --single-shot --device YOUR_DEVICE_ID

# 使用自定义模型和置信度
python device_screen_analyzer.py --single-shot --model path/to/custom.pt --confidence 0.7
```

### 3. 连续监控模式
```bash
# 每2秒分析一次所有设备
python device_screen_analyzer.py --continuous --interval 2

# 限制最大分析次数
python device_screen_analyzer.py --continuous --interval 1 --max-iterations 50

# 指定特定设备进行连续监控
python device_screen_analyzer.py --continuous --device YOUR_DEVICE_ID --interval 3
```

### 4. 自定义输出目录
```bash
python device_screen_analyzer.py --continuous --output-dir ./my_analysis_results
```

## 参数说明

### 基本参数
- `--model`: YOLO 模型路径（默认自动查找 best.pt）
- `--confidence`: 检测置信度阈值（默认 0.6）
- `--device`: 指定设备 ID，使用 "auto" 自动选择所有设备

### 操作模式
- `--list-devices`: 仅列出连接的设备，不执行分析
- `--single-shot`: 执行单次截图分析
- `--continuous`: 连续监控模式

### 连续模式选项
- `--interval`: 截图间隔时间（秒，默认 2.0）
- `--max-iterations`: 最大分析次数（可选）

### 输出选项
- `--save-results`: 保存分析结果（默认启用）
- `--output-dir`: 自定义结果输出目录

## 输出文件结构

分析结果会保存在 `screen_analysis_results/` 目录下（或自定义目录）：

```
screen_analysis_results/
├── DEVICE_ID_20250101_120000_result.jpg      # 带标注的可视化结果
├── DEVICE_ID_20250101_120000_original.jpg    # 原始截图
├── DEVICE_ID_20250101_120000_data.json       # 检测数据
└── analysis_report_20250101_120000.json      # 分析会话报告
```

### JSON 数据格式示例

#### 检测数据 (data.json)
```json
{
  "success": true,
  "device_id": "emulator-5554",
  "timestamp": "2025-01-01T12:00:00.000000",
  "screenshot_shape": [1920, 1080, 3],
  "total_detections": 5,
  "detections": [
    {
      "class_name": "button",
      "confidence": 0.85,
      "bbox": [100, 200, 300, 250],
      "center": [200, 225]
    },
    {
      "class_name": "text",
      "confidence": 0.92,
      "bbox": [400, 100, 600, 130],
      "center": [500, 115]
    }
  ]
}
```

#### 分析报告 (analysis_report.json)
```json
{
  "analysis_summary": {
    "total_devices": 2,
    "analysis_end_time": "2025-01-01T12:30:00.000000",
    "results_directory": "screen_analysis_results"
  },
  "device_sessions": {
    "emulator-5554": {
      "device_id": "emulator-5554",
      "start_time": "2025-01-01T12:00:00.000000",
      "total_screenshots": 15,
      "total_detections": 75,
      "average_detections_per_screenshot": 5.0
    }
  }
}
```

## 使用场景

### 🎮 游戏 UI 测试
监控游戏界面元素的出现和变化，用于自动化测试脚本的验证：
```bash
python device_screen_analyzer.py --continuous --interval 1 --device game_device
```

### 🔍 应用界面分析
分析应用的 UI 布局和元素分布：
```bash
python device_screen_analyzer.py --single-shot --confidence 0.8
```

### 📱 多设备兼容性测试
同时监控多个不同设备上的应用表现：
```bash
python device_screen_analyzer.py --continuous --device auto --interval 3
```

### 🚀 实时界面调试
开发过程中实时查看 AI 模型对界面元素的识别效果：
```bash
python device_screen_analyzer.py --continuous --model custom_model.pt --interval 0.5
```

## 注意事项

### 设备连接
1. 确保设备已启用 USB 调试
2. 首次连接需要在设备上确认 ADB 授权
3. 设备必须处于解锁状态

### 性能优化
1. 调整 `--interval` 参数控制 CPU 使用率
2. 使用 `--confidence` 过滤低置信度检测，减少误报
3. 连续模式下建议设置 `--max-iterations` 避免无限运行

### 模型要求
1. 默认使用项目中的 best.pt 模型
2. 自定义模型需要与 Ultralytics YOLO 兼容
3. 模型类别应与实际要检测的 UI 元素匹配

## 故障排除

### 常见问题

**Q: 提示"未发现连接的设备"**
A: 检查 ADB 连接状态：
```bash
adb devices
```

**Q: 模型加载失败**
A: 确认 best.pt 文件存在且路径正确：
```bash
python device_screen_analyzer.py --model /path/to/your/best.pt --list-devices
```

**Q: 截图捕获失败**
A: 确保设备屏幕处于解锁状态，并且没有其他应用占用截图权限

**Q: 检测结果不准确**
A: 调整置信度阈值或使用更适合的模型：
```bash
python device_screen_analyzer.py --confidence 0.4  # 降低阈值
```

### 日志分析
程序会生成详细的日志文件 `device_screen_analyzer.log`，包含：
- 设备连接状态
- 模型加载信息
- 截图和分析过程
- 错误和警告信息

## 扩展开发

该工具提供了完整的类结构，可以轻松扩展：

```python
from device_screen_analyzer import DeviceScreenAnalyzer

# 创建自定义分析器
analyzer = DeviceScreenAnalyzer(model_path="custom.pt", confidence_threshold=0.7)

# 连接设备
analyzer.connect_device("your_device_id")

# 执行分析
result = analyzer.analyze_single_screenshot("your_device_id")
print(f"检测到 {result['total_detections']} 个元素")
```

## 与现有 WFGameAI 框架集成

该工具与 WFGameAI 自动化测试框架完全兼容，可以作为：
- 录制脚本的预分析工具
- 回放脚本的实时验证工具
- 模型效果的验证和调试工具
- 设备状态的实时监控工具
