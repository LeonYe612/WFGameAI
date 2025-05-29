# WFGameAI 滑动功能实现文档

## 概述
WFGameAI 自动化测试框架现已支持滑动手势的录制和回放功能。本文档描述了滑动功能的实现细节和使用方法。

## 功能特性

### 录制功能 (record_script.py)
1. **鼠标拖拽检测**: 监听鼠标的 `EVENT_MOUSEMOVE` 和 `EVENT_LBUTTONUP` 事件
2. **最小拖拽距离**: 设置了 `DRAG_MIN_DISTANCE = 10` 像素的阈值，避免误判点击为滑动
3. **自动持续时间计算**: 根据实际拖拽时间计算滑动持续时间，最小值为100ms
4. **多设备支持**: 支持一机多控模式下的滑动操作同步

### 回放功能 (replay_script.py)
1. **ADB滑动命令**: 使用 `input swipe start_x start_y end_x end_y duration` 命令执行滑动
2. **JSON格式支持**: 解析录制生成的滑动步骤JSON数据
3. **日志记录**: 完整的滑动操作日志，兼容Airtest报告格式

## JSON数据结构

### 滑动步骤格式
```json
{
    "step": 1,
    "action": "swipe",
    "start_x": 500,
    "start_y": 800,
    "end_x": 500,
    "end_y": 400,
    "duration": 300,
    "timestamp": "2025-05-29 12:00:00.000000",
    "remark": "向上滑动"
}
```

### 字段说明
- `action`: 固定值 "swipe"，标识为滑动操作
- `start_x`, `start_y`: 滑动起始坐标
- `end_x`, `end_y`: 滑动结束坐标
- `duration`: 滑动持续时间(毫秒)
- `remark`: 操作备注描述

## 代码实现

### 全局变量 (record_script.py)
```python
drag_start_pos = {}  # 存储每个设备的拖拽起始位置 {serial: (x, y, time)}
is_dragging = {}     # 存储每个设备的拖拽状态 {serial: bool}
DRAG_MIN_DISTANCE = 10  # 最小拖拽距离(像素)
SWIPE_DURATION = 300    # 默认滑动持续时间(毫秒)
```

### 鼠标事件处理 (record_script.py)
```python
def on_mouse(event, x, y, flags, param):
    # EVENT_LBUTTONDOWN: 记录拖拽起始位置
    # EVENT_MOUSEMOVE: 检测拖拽状态
    # EVENT_LBUTTONUP: 完成滑动并录制
```

### 滑动执行函数 (record_script.py)
```python
def execute_swipe(device, start_x, start_y, end_x, end_y, duration=300):
    """执行ADB滑动命令，支持坐标边界检查和错误处理"""
    device.shell(f"input swipe {start_x} {start_y} {end_x} {end_y} {duration}")
```

### 滑动回放处理 (replay_script.py)
```python
elif step.get("action") == "swipe":
    # 解析滑动参数
    # 执行ADB滑动命令
    # 记录操作日志
```

## 使用方法

### 录制滑动操作
1. 启动录制模式: `python record_script.py --record`
2. 在设备屏幕上执行拖拽操作
3. 滑动操作会自动保存到JSON文件中

### 回放滑动操作
1. 确保JSON文件包含滑动步骤
2. 启动回放: `python replay_script.py --script test_swipe.json`
3. 系统会自动执行所有滑动操作

## 技术细节

### 坐标转换
- 录制时自动转换显示坐标到设备实际坐标
- 支持不同分辨率设备的坐标适配

### 错误处理
- 设备连接检查
- 坐标边界验证
- 持续时间范围限制 (100ms-5000ms)

### 性能优化
- 非阻塞线程执行
- 合理的等待时间设置
- 内存使用优化

## 测试验证

使用提供的测试文件 `test_swipe.json` 可以验证滑动功能:
```bash
python replay_script.py --script test_swipe.json
```

## 注意事项

1. **最小拖拽距离**: 小于10像素的拖拽会被视为点击操作
2. **持续时间限制**: 滑动持续时间限制在100ms-5000ms之间
3. **设备兼容性**: 需要Android设备支持input swipe命令
4. **坐标精度**: 坐标会自动转换为整数值

## 后续优化

1. 支持曲线滑动路径
2. 添加滑动速度控制
3. 支持多点触控滑动
4. 增加滑动模式预设(快速滑动、慢速滑动等)
