# Priority检测问题调试指南

## 概述

为了解决Priority机制中AI检测问题，我们创建了以下调试工具：

1. **test_summary_fix.py** - 测试汇总报告修复效果
2. **monitor_priority_detection.py** - 实时监控Priority检测状态
3. **debug_priority_detection.py** - 分析Priority检测日志

## 使用步骤

### 第一步：验证汇总报告修复

首先确认汇总报告修复是否生效：

```bash
cd C:\Users\Administrator\PycharmProjects\WFGameAI
python test_summary_fix.py
```

**预期结果：**
- ✅ 汇总报告只包含当前测试会话的设备
- ❌ 如果仍包含其他会话设备，需要进一步检查代码

### 第二步：开始测试并实时监控

1. **启动实时监控（在第一个终端窗口）：**
```bash
python monitor_priority_detection.py
```

2. **开始执行测试（在第二个终端窗口）：**
```bash
# 启动您的测试脚本
# 监控工具会自动检测最新的日志文件
```

**监控界面说明：**
```
🔍 [14:30:15] 开始检测: navigation-fight
❌ [14:30:25] 检测失败: 期望 navigation-fight, 实际 None
🔄 [14:30:26] 执行Priority 9的备选步骤: 点击坐标(0.5, 0.9)

⏱️  运行时间: 0:02:30 | 🔍 检测: 15 | ✅ 成功: 3 (20.0%) | 🔄 Fallback: 5
```

### 第三步：测试完成后分析日志

测试完成后，使用日志分析工具：

```bash
python debug_priority_detection.py
```

或者分析特定日志文件：

```bash
python debug_priority_detection.py "path\to\specific\log.txt"
```

## 问题诊断指南

### 1. AI检测超时问题

**症状：**
- 监控显示：检测开始但没有结果
- 日志显示：`检测 navigation-fight 超时`

**可能原因：**
- AI检测服务异常
- 网络连接问题
- 图像处理耗时过长

**解决方案：**
- 检查AI服务状态
- 增加检测超时时间（当前10秒）
- 优化图像预处理

### 2. AI检测失败问题

**症状：**
- 监控显示：`检测失败: 期望 navigation-fight, 实际 None`
- 经常执行fallback

**可能原因：**
- 目标元素不在屏幕上
- AI模型未训练相关类别
- 截图质量问题

**解决方案：**
- 确认界面元素可见性
- 检查class名称是否正确
- 调整AI模型或训练数据

### 3. 类别不匹配问题

**症状：**
- 监控显示：`检测失败: 期望 navigation-fight, 实际 button`
- AI检测到目标但类别错误

**可能原因：**
- JSON脚本中class名称不准确
- AI模型类别映射问题

**解决方案：**
- 使用更通用的class名称（如 `button`）
- 更新AI模型的类别定义

### 4. 频繁执行Fallback

**症状：**
- 监控显示频繁的fallback执行
- 成功率很低（<30%）

**可能原因：**
- 界面变化导致元素位置改变
- 检测精度不足
- 优先级设置不合理

**解决方案：**
- 调整优先级顺序
- 使用相对坐标
- 增加等待时间

## 调试输出说明

### 关键日志内容

1. **AI检测开始：**
```
正在等待AI检测结果: navigation-fight
```

2. **AI检测结果：**
```
AI检测完成 - success: False, detected_class: None, expected_class: navigation-fight
```

3. **Fallback执行：**
```
[FALLBACK] - 所有优先级步骤都未检测到目标
[FALLBACK] - 执行Priority 9的备选步骤: 点击坐标(0.5, 0.9)
```

### 性能指标

- **检测成功率：** 应该 > 70%
- **平均检测时间：** 应该 < 5秒
- **Fallback频率：** 应该 < 10%

## 常见问题解决

### Q1: 监控工具找不到日志文件
**A:** 确认测试已开始，或手动指定日志文件路径：
```bash
python monitor_priority_detection.py "wfgame-ai-server/staticfiles/reports/device_xxx/log.txt"
```

### Q2: 分析工具显示"没有找到AI检测结果"
**A:** 可能是：
- 日志格式改变
- AI检测进程崩溃
- 日志文件损坏

### Q3: 成功率很低但界面元素可见
**A:** 检查：
- AI模型是否适合当前界面
- class名称是否与训练数据匹配
- 截图分辨率是否合适

## 下一步优化建议

基于调试结果，可以考虑以下优化：

1. **调整检测策略：**
   - 使用更通用的class名称
   - 增加多个fallback选项
   - 实现自适应超时

2. **改进AI模型：**
   - 使用当前应用界面重新训练
   - 增加数据增强
   - 优化后处理逻辑

3. **优化执行逻辑：**
   - 实现智能重试机制
   - 添加界面状态检测
   - 使用置信度阈值动态调整

## 联系支持

如果问题仍未解决，请提供：
1. 监控工具的输出截图
2. 分析工具的诊断报告
3. 相关的截图文件
4. JSON脚本配置

这将帮助进一步定位和解决问题。
