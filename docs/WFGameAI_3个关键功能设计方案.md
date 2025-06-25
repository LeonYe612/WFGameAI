# WFGameAI 3个关键功能设计方案

> **📋 设计目标**
> - 精简易懂的JSON格式
> - 清晰区分UI和AI识别方式
> - 统一的参数设计
> - 避免复杂的嵌套结构

---

## 🎯 核心设计原则

### 1. 识别方式标识
- **不可为空**: `detection_method`不能为空，但可以不写
- **默认**: `detection_method`没有值时，默认使用AI图像识别
- **AI识别**: `"detection_method": "ai"` + `"yolo_class": "operation-back"`
- **UI识别**: `"detection_method": "ui"` + `"ui_type": "username_field"`

### 2. 参数精简化
- 删除复杂的`target_selector`嵌套
- 直接在action级别定义识别参数
- 保持向后兼容

### 3. 易读性优先
- JSON结构扁平化
- 参数名称通俗易懂
- 减少不必要的配置项

---

## 📝 新的JSON格式设计

### 基础格式模板

```json
{
  "action": "功能名称",
  "detection_method": "yolo|ui",     // 可选，默认yolo
  "yolo_class": "YOLO类别",             // AI识别时使用
  "ui_type": "ElementPattern类型",     // UI识别时使用
  "timeout": 10,                   // 超时时间
  "remark": "操作说明"
}
```

---

## 🚀 三个关键功能详细设计

### 1. wait_for_appearance - 等待元素出现

**功能说明**: 等待指定元素从无到有的出现过程

#### AI识别方式 (默认)
```json
{
  "step": 1,
  "action": "wait_for_appearance",
  "yolo_class": "system-loginButton",
  "timeout": 15,
  "polling_interval": 2,
  "remark": "等待登录按钮出现"
}
```

#### UI识别方式
```json
{
  "step": 2,
  "action": "wait_for_appearance",
  "detection_method": "ui",
  "ui_type": "username_field",
  "timeout": 10,
  "remark": "等待用户名输入框出现"
}
```

#### 混合识别方式
```json
{
  "step": 3,
  "action": "wait_for_appearance",
  "detection_method": "ui",
  "ui_type": "login_button",
  "fallback_yolo_class": "operation-confirm",  // UI失败时使用AI备选
  "timeout": 12,
  "remark": "等待登录按钮出现(UI优先+AI备选)"
}
```

**完整参数列表**:
```json
{
  "action": "wait_for_appearance",
  "detection_method": "ai",        // ai|ui，默认ai
  "yolo_class": "operation-confirm",    // AI: YOLO类别
  "ui_type": "login_button",          // UI: ElementPattern类型
  "fallback_yolo_class": "备选类别",    // 备选方案
  "timeout": 10,                   // 超时时间(秒)
  "polling_interval": 1,           // 检查间隔(秒)
  "confidence": 0.8,               // 置信度阈值
  "fail_on_timeout": true,         // 超时是否失败
  "screenshot_on_timeout": true,   // 超时时截图
  "remark": "操作说明"
}
```

---

### 2. wait_for_stable - 等待界面稳定

**功能说明**: 等待界面连续N秒无变化，确保操作时机

#### 基础使用 (推荐)
```json
{
  "step": 1,
  "action": "wait_for_stable",
  "detection_method": "ai",        // ai|ui，默认ai
  "duration": 3,
  "max_wait": 10,
  "remark": "等待界面稳定"
}
```

#### 高级配置
```json
{
    "step": 2,
  "action": "wait_for_stable",
  "detection_method": "ui",
  "duration": 2,
  "max_wait": 8,
  "check_structure": true,   // 使用detection_method指定的方案（ui|ai）来检查UI结构稳定。默认 true
  "tolerance": 0.05,
  "remark": "等待UI结构稳定"
}
```

**完整参数列表**:
```json
{
  "step": 1,
  "action": "wait_for_stable",
  "detection_method": "ai",        // ai|ui，默认ai
  "duration": 2,                   // 稳定持续时间(秒)
  "max_wait": 10,                   // 最大等待时间(秒)
  "check_structure": true,      // 检查UI结构稳定
  "check_positions": true,         // 检查元素位置稳定
  "tolerance": 0.05,               // 变化容忍度(5%)
  "ignore_animations": true,       // 忽略动画效果
  "remark": "操作说明"
}
```

---

### 3. retry_until_success - 重试直到成功

**功能说明**: 对任意操作进行重试，直到成功或达到最大次数

#### AI操作重试 (默认)
```json
{
  "action": "retry_until_success",
  "retry_action": "click",
  "yolo_class": "operation-confirm",
  "max_retries": 3,
  "retry_interval": 1,
  "remark": "重试点击确认按钮"
}
```

#### UI操作重试
```json
{
  "action": "retry_until_success",
  "detection_method": "ui",
  "retry_action": "input",
  "ui_type": "username_field",
  "text": "${account:username}",
  "max_retries": 3,
  "remark": "重试输入用户名"
}
```

#### 复杂操作重试
```json
{
  "action": "retry_until_success",
  "retry_action": "click",
  "yolo_class": "system-loginSwitch",
  "max_retries": 5,
  "retry_strategy": "exponential",
  "initial_delay": 1,
  "max_delay": 8,
  "verify_success": true,
  "remark": "重试切换登录方式"
}
```

**完整参数列表**:
```json
{
  "action": "retry_until_success",
  "detection_method": "ai",        // ai|ui，默认ai
  "retry_action": "click",         // 要重试的操作: click|input|click_target(废弃)|checkbox
  "yolo_class": "operation-confirm",    // AI: YOLO类别
  "ui_type": "login_button",          // UI: ElementPattern类型
  "text": "输入内容",               // input操作的文本
  "max_retries": 5,                // 最大重试次数
  "retry_strategy": "fixed",       // fixed|exponential|adaptive
  "retry_interval": 1,             // 重试间隔(秒)
  "initial_delay": 1,              // 初始延迟(秒)
  "max_delay": 10,                 // 最大延迟(秒)
  "backoff_multiplier": 2,         // 指数退避倍数
  "verify_success": false,         // 是否验证操作成功
  "stop_on_success": true,         // 成功后是否停止
  "remark": "操作说明"
}
```

---

## 🎮 标准脚本示例

### 示例1: 登录流程优化 (精简版)

```json
{
  "name": "登录流程-使用3个关键功能",
  "steps": [
    {
      "step": 1,
      "detection_method": "ai",
      "action": "wait_for_appearance",
      "yolo_class": "system-loginSwitch",
      "timeout": 10,
      "remark": "等待登录切换按钮出现"
    },
    {
      "step": 2,
      "detection_method": "ai",
      "action": "retry_until_success",
      "retry_action": "click",
      "yolo_class": "system-loginSwitch",
      "max_retries": 3,
      "remark": "重试点击登录切换按钮"
    },
    {
      "step": 3,
      "detection_method": "ui",
      "action": "wait_for_stable",
      "duration": 2,
      "max_wait": 8,
      "remark": "等待界面稳定"
    },
    {
      "step": 4,
      "detection_method": "ui",
      "action": "wait_for_appearance",
      "ui_type": "username_field",
      "timeout": 8,
      "remark": "等待用户名输入框出现"
    },
    {
      "step": 5,
      "detection_method": "ui",
      "action": "retry_until_success",
      "retry_action": "input",
      "ui_type": "username_field",
      "text": "${account:username}",
      "max_retries": 3,
      "remark": "重试输入用户名"
    },
    {
      "step": 6,
      "detection_method": "ui",
      "action": "retry_until_success",
      "retry_action": "input",
      "ui_type": "password_field",
      "text": "${account:password}",
      "max_retries": 3,
      "remark": "重试输入密码"
    },
    {
      "step": 7,
      "detection_method": "ui",
      "action": "retry_until_success",
      "retry_action": "click",
      "ui_type": "operation-confirm",
      "max_retries": 3,
      "verify_success": true,
      "remark": "重试点击登录按钮"
    }
  ]
}
```

### 示例2: 界面导航优化

```json
{
  "name": "界面导航-智能等待",
  "steps": [
    {
      "step": 1,
      "action": "wait_for_stable",
      "duration": 3,
      "max_wait": 10,
      "remark": "等待主界面稳定"
    },
    {
      "step": 2,
      "action": "wait_for_appearance",
      "class": "navigation-fight",
      "timeout": 15,
      "remark": "等待战斗入口出现"
    },
    {
      "step": 3,
      "action": "retry_until_success",
      "retry_action": "click",
      "class": "navigation-fight",
      "max_retries": 5,
      "retry_strategy": "exponential",
      "remark": "重试进入战斗"
    }
  ]
}
```

---

## 📚 ElementPattern类型对照表

### UI识别可用的type值 (对应ElementPatterns)

| type值 | 对应模式 | 说明 |
|--------|----------|------|
| `username_field` | USERNAME_PATTERNS | 用户名输入框 |
| `password_field` | PASSWORD_PATTERNS | 密码输入框 |
| `agreement_checkbox` | CHECKBOX_PATTERNS | 协议勾选框 |
| `login_button` | LOGIN_BUTTON_PATTERNS | 登录按钮 |
| `skip_button` | SKIP_BUTTON_PATTERNS | 跳过按钮 |
| `login_switch_button` | LOGIN_SWITCH_BUTTON_PATTERNS | 登录方式切换 |

### AI识别可用的class值 (对应YOLO模型)

| class值 | 说明 | 使用场景 |
|---------|------|----------|
| `system-skip` | 跳过按钮 | 跳过引导/广告 |
| `system-loginSwitch` | 登录切换 | 切换登录方式 |
| `operation-back` | 返回按钮 | 页面返回 |
| `operation-confirm` | 确认按钮 | 确认操作 |
| `operation-close` | 关闭按钮 | 关闭弹窗 |
| `operation-challenge` | 挑战按钮 | 游戏挑战 |
| `navigation-fight` | 战斗导航 | 进入战斗 |
| `hint-guide` | 引导提示 | 新手引导 |

---

## 🔧 实现要点

### 1. 向后兼容处理
- 保持现有action正常工作
- 逐步迁移到新格式
- 同时支持新旧两种写法

### 2. 默认行为
- 不写`detection_method`时默认为`ai`
- 合理的默认超时时间
- 智能的重试策略

### 3. 错误处理
- 清晰的错误提示
- 失败时的截图保存
- 详细的日志记录

### 4. 性能优化
- 合理的轮询间隔
- 避免过度截图
- 智能的元素缓存

---

## 💡 使用建议


### 2. 参数选择建议
- **timeout**: 一般10-15秒，网络操作可用30秒
- **max_retries**: 一般3-5次，关键操作可用10次
- **duration**: 界面切换2-3秒，复杂加载5秒
- **polling_interval**: 一般1-2秒，快速响应用0.5秒

### 3. 性能优化建议
- 优先使用AI识别 (YOLO模型性能更好)
- UI识别适用于输入框等特定场景
- 避免过短的轮询间隔
- 合理设置超时时间

---

## 🎯 下一步开发计划

1. **第一阶段**: 在action_processor.py中实现3个新功能
2. **第二阶段**: 添加混合识别支持
3. **第三阶段**: 完善错误处理和日志
4. **第四阶段**: 性能优化和测试
5. **第五阶段**: 文档更新和示例完善

---

*📝 备注: 本文档作为开发的标准参考，所有实现都应严格按照此设计进行*
