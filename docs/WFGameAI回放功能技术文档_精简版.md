# WFGameAI 回放功能技术文档（精简版）

> **快速技术指南** | **版本**: 2.0 | **更新**: 2025-06-24
> **相关文档**: [Action使用手册（精简版）](./WFGameAI_Action_使用手册_精简版.md)

---

## 🎯 核心功能

WFGameAI回放功能是基于AI视觉识别的Android自动化测试执行引擎，支持：

- ✅ **多设备并行**: 同时在多台设备执行脚本
- ✅ **AI智能检测**: YOLO11m模型进行元素识别
- ✅ **动作丰富**: 20+种操作类型（点击、输入、滑动等）
- ✅ **账号参数化**: 支持 `${account:username}` 变量替换
- ✅ **实时报告**: 生成HTML测试报告和截图

---

## 📁 核心文件结构

```
WFGameAI/
├── wfgame-ai-server/apps/scripts/
│   ├── replay_script.py          # 🔥 主回放引擎
│   ├── action_processor.py       # 🔥 动作处理器
│   ├── enhanced_input_handler.py # 设备脚本回放器
│   ├── account_manager.py        # 账号管理
│   ├── views.py                  # Web API
│   └── testcase/                 # JSON脚本存放
├── models/best.pt                # YOLO11m检测模型
└── config.ini                    # 全局配置
```

---

## ⚡ 快速开始

### 1. 脚本执行流程

```mermaid
graph LR
    A[加载脚本] --> B[设备连接]
    B --> C[账号分配]
    C --> D[AI模型加载]
    D --> E[逐步执行]
    E --> F[生成报告]
```

### 2. 基础脚本格式

```json
{
  "name": "登录测试",
  "description": "自动登录流程",
  "steps": [
    {
      "step": 1,
      "action": "wait_if_exists",
      "class": "system-newResources",
      "max_duration": 300,
      "remark": "等待热更新"
    },
    {
      "step": 2,
      "action": "click_target",
      "target_selector": {
        "text_hints": ["其他登录方式", "账号登录"]
      },
      "remark": "切换登录方式"
    },
    {
      "step": 3,
      "action": "input",
      "text": "${account:username}",
      "target_selector": {"placeholder": "请输入用户名"},
      "remark": "输入用户名"
    }
  ]
}
```

### 3. 执行命令

```bash
# Web API调用
POST /api/scripts/replay/
{
  "scripts": [{"path": "testcase/login_test.json"}],
  "show_screens": true
}
```

---

## 🔧 核心组件

### ActionProcessor - 动作处理器

**功能**: 统一处理所有Action类型，支持新旧接口兼容

```python
class ActionProcessor:
    def process_action(self, step, context):
        """统一动作处理入口"""
        action_type = step.get('action', step.get('class'))

        if action_type == 'click_target':
            return self._handle_click_target(step)
        elif action_type == 'input':
            return self._handle_input(step)
        elif action_type == 'wait_if_exists':
            return self._handle_wait_if_exists(step)
        # ... 其他action处理
```

**支持的Action类型**: 详见 [Action使用手册](./WFGameAI_Action_使用手册_精简版.md)

### 账号参数化

**变量替换机制**:
```python
# 脚本中使用变量
"text": "${account:username}"

# 运行时自动替换为
"text": "actual_username_123"
```

**支持的变量**:
- `${account:username}` - 用户名
- `${account:password}` - 密码
- `${account:phone}` - 手机号

---

## 🔗 Web API接口

### 核心API端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/scripts/` | POST | 获取脚本列表 |
| `/api/scripts/replay/` | POST | 执行脚本回放 |
| `/api/scripts/import/` | POST | 导入脚本文件 |
| `/api/scripts/reports/` | GET | 获取报告列表 |

### 执行脚本示例

```http
POST /api/scripts/replay/
Content-Type: application/json

{
  "scripts": [
    {
      "path": "testcase/login_test.json",
      "loop_count": 1,
      "max_duration": 300
    }
  ],
  "show_screens": true,
  "device_filter": ["device1", "device2"]
}
```

### 响应格式

```json
{
  "status": "success",
  "message": "脚本执行成功",
  "report_url": "/reports/replay_20250624_153045.html",
  "devices": [
    {
      "device_id": "device1",
      "status": "completed",
      "steps_executed": 5,
      "execution_time": "45.2s"
    }
  ]
}
```

---

## 📊 报告系统

### 报告生成

执行完成后自动生成HTML报告，包含：

- ✅ 执行概况（成功率、耗时）
- ✅ 详细步骤日志
- ✅ 每步骤截图
- ✅ 错误信息和堆栈
- ✅ 设备状态信息

### 报告文件结构

```
reports/
├── replay_20250624_153045.html          # 主报告
├── replay_20250624_153045_screenshots/  # 截图目录
│   ├── device1_step1.png
│   ├── device1_step2.png
│   └── ...
└── replay_20250624_153045.log          # 详细日志
```

---

## 🛠️ 配置文件

### config.ini 主要配置

```ini
[DETECTION]
confidence_threshold = 0.7
model_path = models/best.pt

[DEVICES]
default_timeout = 30
screenshot_interval = 1

[ACCOUNTS]
account_pool = accounts.json
assignment_strategy = round_robin

[REPORTS]
output_dir = reports/
template_path = templates/report_template.html
include_screenshots = true
```

---

## 🚀 性能优化

### 执行效率优化

1. **并行执行**: 多设备同时运行，提高测试覆盖
2. **AI模型缓存**: 避免重复加载模型
3. **智能等待**: 使用 `wait_if_exists` 替代固定延时
4. **截图优化**: 按需截图，减少IO开销

### 稳定性优化

1. **重试机制**: Action级别的重试配置
2. **降级策略**: AI检测失败时坐标点击
3. **容错设计**: `skip_if_not_found` 跳过可选步骤
4. **状态检查**: 执行前检查设备连接状态

---

## 🔍 故障排除

### 常见问题解决

| 问题 | 症状 | 解决方案 |
|------|------|----------|
| **AI检测失败** | 找不到元素 | 调整confidence阈值，增加text_hints |
| **设备连接断开** | 执行中断 | 检查USB连接，重启ADB服务 |
| **界面未稳定** | 点击错误位置 | 增加delay时间，使用wait_if_exists |
| **账号变量未替换** | 输入字面量 | 检查账号分配，验证变量格式 |
| **权限弹窗阻塞** | 脚本卡住 | 启用handle_permission参数 |

### 调试技巧

1. **详细日志**: 在action中添加详细的 `remark`
2. **分步测试**: 拆分复杂脚本为小片段测试
3. **截图验证**: 查看每步执行后的屏幕截图
4. **置信度调试**: 从低到高调整 `confidence` 值

---

## 📚 扩展开发

### 添加新Action类型

1. 在 `ActionProcessor` 中添加处理方法
2. 实现具体的执行逻辑
3. 添加参数验证和错误处理
4. 更新文档和示例

### 集成第三方工具

- **Appium**: 可集成Appium Driver作为备选方案
- **UI Automator**: 利用Android原生自动化能力
- **云测试平台**: 对接云设备进行大规模测试

---

## 📖 文档导航
- [技术文档](./WFGameAI回放功能技术文档_精简版.md) ⬅️ 当前文档
- [Action使用手册](./WFGameAI_Action_使用手册_精简版.md)
- [API快速参考](./API快速参考.md)

## ⚠️ 【非常重要！必须遵守】step 和 Priority 关键字执行逻辑规则

### 🎯 核心执行逻辑

WFGameAI回放系统基于脚本中是否包含`Priority`字段自动选择执行模式：

```python
# 脚本类型检测逻辑
is_priority_based = any("Priority" in step for step in steps)
```

### 📋 1. step字段执行逻辑（顺序执行模式）

**适用场景：** 脚本中所有步骤都不包含`Priority`字段

**执行方式：** `process_sequential_script()` 函数

**关键规则：**
1. **严格顺序执行**：按照step字段数值从小到大顺序执行
2. **支持小数编号**：支持step 1, step 1.5, step 2等编号，用于后期插入中间步骤
3. **单次遍历**：每个步骤只执行一次，按列表索引顺序处理
4. **失败处理**：某步骤失败时继续执行下一步，不会停止整个流程
5. **超时控制**：支持`max_duration`参数控制整个脚本最大执行时间

**执行流程：**
```
开始 → 读取steps → 按索引顺序遍历 → 执行step[0] → 执行step[1] → ... → 结束
```

### 🎯 2. Priority字段执行逻辑（优先级执行模式）

**适用场景：** 脚本中任意步骤包含`Priority`字段

**执行方式：** `process_priority_based_script()` 函数

**关键规则：**
1. **优先级排序**：首先按Priority数值排序（Priority 1 > Priority 2 > ...）
2. **持续循环检测**：不断轮询检测所有优先级步骤，直到匹配目标或超时
3. **AI视觉检测**：每个步骤使用YOLO模型进行屏幕目标检测
4. **匹配即执行**：一旦检测到匹配目标，立即执行并重新开始检测循环
5. **Fallback机制**：如果所有优先级步骤都未匹配，执行class为"unknown"的备选步骤
6. **超时保护**：连续30秒未检测到任何步骤时自动停止

**执行流程：**
```
开始 → 按Priority排序 → 循环检测P1,P2,...Pn →
  └─ 匹配成功 → 执行操作 → 重新开始循环
  └─ 无匹配 → 执行unknown备选 → 继续循环
  └─ 超时 → 停止执行
```

### 🔄 3. 执行模式对比

| 特性 | step字段模式 | Priority字段模式 |
|------|-------------|------------------|
| **执行方式** | 线性顺序执行 | 循环动态检测 |
| **检测机制** | 无AI检测   | YOLO视觉检测 |
| **失败处理** | 继续下一步 | 重试或fallback |
| **执行次数** | 每步仅一次 | 持续检测直到匹配 |
| **适用场景** | 固定流程操作 | 动态UI响应 |
| **时间控制** | 总体超时 | 检测间隔+总体超时 |

### ⚡ 4. 关键技术细节

**Priority排序规则：**
```python
steps.sort(key=lambda s: s.get("Priority", 999))
```
- 未指定Priority的步骤默认优先级为999（最低）
- 数值越小优先级越高

**检测循环机制：**
```python
while max_duration is None or (time.time() - priority_start_time) <= max_duration:
    # 对每个Priority步骤进行AI检测
    for step in sorted_steps:
        if ai_detection_success:
            execute_step()
            break  # 跳出内层循环，重新开始检测
```
- 每个步骤的执行间隔为0.5秒：`time.sleep(0.5)`

**超时机制：**
- `max_duration`: 脚本级别的最大执行时间
- 30秒无检测保护：`time.time() - priority_start_time > 30`
- 检测间隔：`time.sleep(0.5)` 每轮检测间暂停0.5秒

### 🚨 5. 必须遵守的编写约束

**step模式脚本要求：**
- 所有步骤都不能包含`Priority`字段
- 建议使用连续的step编号：1, 2, 3...
- 支持小数编号用于后期插入：1, 1.5, 2, 2.1, 3...

**Priority模式脚本要求：**
- 至少一个步骤必须包含`Priority`字段
- Priority值建议从1开始：1, 2, 3...
- 必须包含`class`字段用于AI检测目标类别
- 建议提供`remark`字段用于日志记录
- 可选提供class为"unknown"的fallback步骤

**混合模式限制：**
- 不支持在同一脚本中混用step和Priority模式
- 系统自动检测：有Priority字段即进入Priority模式

### 📝 6. 最佳实践建议

1. **选择合适的模式**：
   - 固定操作流程 → 使用step模式
   - 动态UI交互 → 使用Priority模式

2. **Priority模式优化**：
   - 高频操作设置低Priority数值
   - 提供unknown fallback步骤防止死循环
   - 合理设置max_duration避免无限等待

3. **脚本维护性**：
   - step编号预留空间（如：10, 20, 30）
   - Priority分组管理（如：登录1-10，游戏11-20）

---

## 📁 核心模块概述
