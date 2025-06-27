# WFGameAI Action 使用手册（完整版）

> **📋 文档说明**
> 本文档整合了WFGameAI框架中所有可用的Action类型和Class类型，提供完整的参数说明和使用示例。
>
> **📖 文档导航**:
> - **精简版手册**: [WFGameAI Action 使用手册（精简版）](./WFGameAI_Action_使用手册_精简版.md) - 快速查找和常用示例
> - **技术文档**: [WFGameAI回放功能完整技术文档](./WFGameAI回放功能完整技术文档.md) - 完整技术实现

---

## 📖 目录

- [🎯 快速查找](#-快速查找)
- [⚡ 基础操作类](#-基础操作类)
- [🔍 智能检测类](#-智能检测类)
- [📱 应用管理类](#-应用管理类)
- [⏱️ 时间控制类](#️-时间控制类)
- [🎮 UI元素操作类](#-ui元素操作类)
- [📝 文本输入类](#-文本输入类)
- [🔄 等待机制类](#-等待机制类)
- [🚀 建议实现的Actions](#-建议实现的actions)
- [💡 最佳实践](#-最佳实践)

---

## 🎯 快速查找

### 按功能分类

| 分类 | Actions/Classes | 说明 |
|------|-----------------|------|
| **点击操作** | `click`, `click_target` | 基础点击、智能目标点击 |
| **文本操作** | `input` | 文本输入，支持变量替换 |
| **滑动操作** | `swipe` | 屏幕滑动操作 |
| **等待操作** | `delay`, `wait_if_exists`, `wait` | 延时、条件等待 |
| **应用管理** | `app_start`, `app_stop` | 应用启动停止 |
| **设备管理** | `device_preparation` | 设备预处理 |
| **界面元素** | `checkbox` | 复选框操作 |
| **自动化流程** | `auto_login` | 完整登录流程 |

### 按使用频率排序

| 优先级 | Action | 使用场景 | 示例脚本 |
|--------|--------|----------|----------|
| ⭐⭐⭐ | `click_target` | 智能元素点击 | 所有登录脚本 |
| ⭐⭐⭐ | `input` | 文本输入 | 用户名密码输入 |
| ⭐⭐⭐ | `delay` | 等待界面稳定 | 所有脚本 |
| ⭐⭐⭐ | `app_start` | 应用启动 | 启动脚本 |
| ⭐⭐ | `wait_if_exists` | 条件等待 | 热更新处理 |
| ⭐⭐ | `swipe` | 页面滑动 | 界面导航 |
| ⭐ | `auto_login` | 完整登录 | 复杂登录流程 |

---

## ⚡ 基础操作类

### 1. click - 基础点击操作

**功能**: 最基础的点击操作，支持坐标点击和元素点击

**格式**: 支持两种写法
```json
// 新格式（推荐）
{
  "action": "click",
  "class": "element-class"
}

// 旧格式（兼容）
{
  "class": "element-class"  // 默认为click操作
}
```

**参数说明**:
```json
{
  "action": "click",           // 可选，默认为click
  "class": "element-class",    // 元素类名
  "coordinates": [x, y],       // 可选，直接坐标点击
  "confidence": 0.8,           // 可选，识别置信度
  "remark": "操作说明"         // 可选，操作备注
}
```

**使用示例**:
```json
// 示例1: 通过class点击
{
  "step": 1,
  "action": "click",
  "class": "login-button",
  "remark": "点击登录按钮"
}

// 示例2: 旧格式兼容
{
  "step": 2,
  "class": "operation-close",
  "confidence": 0.93,
  "remark": "点击关闭按钮"
}
```

**适用场景**:
- ✅ 简单的按钮点击
- ✅ 固定位置的元素点击
- ❌ 复杂的元素定位（建议使用click_target）

---

### 2. click_target - 智能目标点击

**功能**: 智能元素定位点击，支持多种定位方式和容错机制

**参数说明**:
```json
{
  "action": "click_target",
  "target_selector": {
    "text_hints": ["文本1", "文本2"],           // 文本提示
    "resource_id_keywords": ["id1", "id2"],    // 资源ID关键词
    "class_types": ["类型1", "类型2"],          // 控件类型
    "content_desc_keywords": ["描述1"],         // 内容描述
    "skip_if_not_found": true,                 // 找不到时跳过
    "retry_count": 3,                          // 重试次数
    "retry_interval": 2                        // 重试间隔(秒)
  },
  "confidence": 0.9,
  "remark": "智能点击操作"
}
```

**使用示例**:
```json
{
  "step": 2,
  "action": "click_target",
  "target_selector": {
    "text_hints": ["其他登录方式", "切换登录", "账号登录"],
    "resource_id_keywords": ["other_login", "switch_login"],
    "class_types": ["android.widget.TextView", "android.widget.Button"],
    "skip_if_not_found": true,
    "retry_count": 3,
    "retry_interval": 2
  },
  "confidence": 0.9,
  "remark": "切换到账号密码登录模式"
}
```

**适用场景**:
- ✅ 复杂的元素定位
- ✅ 需要容错的操作
- ✅ 多种定位方式的组合

---

## 🔍 智能检测类

### 1. wait_if_exists - 条件等待

**功能**: 当指定元素存在时等待其消失，用于处理加载界面

**参数说明**:
```json
{
  "action": "wait_if_exists",
  "class": "loading-element",           // 等待的元素类名
  "polling_interval": 5000,            // 检查间隔(毫秒)
  "max_duration": 300,                 // 最大等待时间(秒)
  "confidence": 0.7,                   // 识别置信度
  "remark": "等待加载完成"
}
```

**使用示例**:
```json
{
  "step": 1,
  "action": "wait_if_exists",
  "class": "system-newResources",
  "polling_interval": 5000,
  "max_duration": 300,
  "confidence": 0.7,
  "remark": "判断启动APP后是否出现热更资源图标，等待加载完成"
}
```

**适用场景**:
- ✅ 应用启动后的热更新等待
- ✅ 加载界面的处理
- ✅ 不确定加载时间的情况

---

### 2. wait - 简单等待

**功能**: 等待指定元素出现或消失

**使用示例**:


```json
{
  "step": 1,
  "action": "wait",
  "class": "target-element",
  "remark": "等待目标元素"
}
```

---

## 📱 应用管理类

### 1. app_start - 应用启动

**功能**: 启动指定应用并处理权限弹窗

**参数说明**:
```json
{
  "class": "app_start",
  "params": {
    "app_name": "应用名称",              // 应用名称标识
    "package_name": "com.example.app",  // 应用包名
    "activity_name": "Activity路径",     // 可选，启动Activity
    "handle_permission": true,          // 是否处理权限弹窗
    "permission_wait": 15,              // 权限处理等待时间
    "allow_permission": true,           // 是否允许权限
    "first_only": true                  // 是否仅首次处理权限
  },
  "remark": "启动应用"
}
```


---

### 2. app_stop - 应用停止

**功能**: 停止指定应用

**参数说明**:
```json
{
  "class": "app_stop",
  "params": {
    "package_name": "com.example.app"   // 应用包名
  },
  "remark": "停止应用"
}
```


---

### 3. device_preparation - 设备预处理

**功能**: 设备环境预处理，包括权限配置、屏幕锁定处理等

**参数说明**:
```json
{
  "class": "device_preparation",
  "params": {    "check_usb": true,                  // 检查USB连接
    "setup_wireless": false,           // 设置无线连接
    "auto_handle_dialog": true,        // 自动处理弹窗
    "handle_screen_lock": true,        // 处理屏幕锁定
    "setup_input_method": true,        // 设置输入法
    "save_logs": false                 // 是否保存日志
  },
  "remark": "设备预处理"
}
```


---

## ⏱️ 时间控制类

### 1. delay - 延时等待

**功能**: 简单的延时等待操作

**参数说明**:
```json
{
  "class": "delay",               // 旧格式
  "params": {
    "seconds": 5                  // 等待秒数
  },
  "remark": "等待说明"
}
```

**新格式**:
```json
{
  "action": "delay",
  "params": {
    "seconds": 5
  },
  "remark": "等待说明"
}
```


---

## 🎮 UI元素操作类

### 1. checkbox - 复选框操作

**功能**: 复选框的勾选操作

**参数说明**:
```json
{
  "action": "checkbox",
  "target_selector": {
    "class_types": ["android.widget.CheckBox"],
    "type": "agreement_checkbox"
  },
  "confidence": 0.95,
  "remark": "复选框操作"
}
```

**使用示例**:
```json
{
  "step": 5,
  "action": "checkbox",
  "target_selector": {
    "class_types": ["android.widget.CheckBox"],
    "type": "agreement_checkbox"
  },
  "confidence": 0.95,
  "remark": "勾选用户协议"
}
```

---

### 2. swipe - 滑动操作

**功能**: 屏幕滑动操作，支持方向和自定义坐标

**参数说明**:
```json
{
  "action": "swipe",
  "start_x": 500,                      // 起始X坐标
  "start_y": 800,                      // 起始Y坐标
  "end_x": 500,                        // 结束X坐标
  "end_y": 400,                        // 结束Y坐标
  "duration": 1000,                    // 滑动持续时间(毫秒)
  "remark": "滑动操作说明"
}
```

**使用示例**:
```json
// 示例1: 向上滑动
{
  "step": 1,
  "action": "swipe",
  "start_x": 500,
  "start_y": 800,
  "end_x": 500,
  "end_y": 400,
  "duration": 500,
  "remark": "向上滑动页面"
}

// 示例2: 向右滑动
{
  "step": 2,
  "action": "swipe",
  "start_x": 200,
  "start_y": 600,
  "end_x": 800,
  "end_y": 600,
  "duration": 300,
  "remark": "向右滑动"
}
```

---

## 📝 文本输入类

### 1. input - 文本输入操作

**功能**: 文本输入操作，支持账号变量替换和输入框清理

**参数说明**:
```json
{
  "action": "input",
  "text": "输入内容",                    // 输入文本，支持${account:username}等变量
  "target_selector": {                 // 输入框定位
    "placeholder": "请输入用户名",
    "clear_previous_text": true        // 是否清除原有文本
  },
  "confidence": 0.95,
  "remark": "输入操作说明"
}
```

**支持的变量**:
- `${account:username}` - 用户名
- `${account:password}` - 密码
- `${account:phone}` - 手机号

**使用示例**:
```json
// 示例1: 用户名输入
{
  "step": 3,
  "action": "input",
  "text": "${account:username}",
  "target_selector": {
    "placeholder": "请输入手机号",
    "clear_previous_text": true
  },
  "confidence": 0.95,
  "remark": "输入登录用户名"
}

// 示例2: 密码输入
{
  "step": 4,
  "action": "input",
  "text": "${account:password}",
  "target_selector": {
    "placeholder": "请输入密码",
    "clear_previous_text": true
  },
  "confidence": 0.95,
  "remark": "输入登录密码"
}
```

---

## 🔄 等待机制类

### 高级等待操作

WFGameAI支持多种等待机制来处理复杂的界面交互：

#### 1. 热更新等待处理
```json
{
  "step": 1,
  "action": "wait_if_exists",
  "class": "system-newResources",
  "polling_interval": 5000,
  "max_duration": 300,
  "confidence": 0.7135645747184753,
  "remark": "判断启动APP后是否出现热更资源图标，如果存在则需要等待新资源加载完成"
}
```

#### 2. 界面稳定等待
```json
{
  "step": 1.5,
  "action": "delay",
  "params": {
    "seconds": 3
  },
  "remark": "等待热更新检测完成和界面稳定"
}
```

#### 3. 登录方式切换等待
```json
{
  "step": 2.5,
  "action": "delay",
  "params": {
    "seconds": 2
  },
  "remark": "等待登录方式切换完成，界面稳定后再进行下一步操作"
}
```

---

## 🎯 UI元素Class分类

### 系统级元素

| Class名称 | 功能说明 | 使用场景 |
|-----------|----------|----------|
| `system-newResources` | 热更新资源图标 | 应用启动后的热更新处理 |
| `system-cleanUpCache` | 清理缓存提示 | 缓存清理确认 |
| `system-skip` | 跳过按钮 | 跳过引导或广告 |

### 操作级元素

| Class名称 | 功能说明 | 使用场景 |
|-----------|----------|----------|
| `operation-close` | 关闭按钮 | 关闭弹窗或对话框 |
| `operation-confirm` | 确认按钮 | 确认操作 |
| `operation-back` | 返回按钮 | 页面返回 |
| `operation-challenge` | 挑战按钮 | 游戏挑战功能 |

### 导航级元素

| Class名称 | 功能说明 | 使用场景 |
|-----------|----------|----------|
| `navigation-fight` | 战斗导航 | 进入战斗界面 |
| `hint-guide` | 引导提示 | 新手引导 |

### 通用元素

| Class名称 | 功能说明 | 使用场景 |
|-----------|----------|----------|
| `unknown` | 未知元素 | 备选坐标点击 |

---

## 🚀 建议实现的Actions

> **💡 提示**: 以下Actions可以解决当前脚本执行中的时序问题

### 第一阶段 - 关键功能

#### 1. wait_for_appearance - 等待元素出现

**解决问题**: 界面状态转换时序问题

```json
{
  "action": "wait_for_appearance",
  "target_selector": {
    "text_hints": ["其他登录方式"]
  },
  "timeout": 10,
  "remark": "等待登录选项出现"
}
```

#### 2. wait_for_stable - 等待界面稳定

**解决问题**: 步骤间界面过渡时间不确定

```json
{
  "action": "wait_for_stable",
  "stability_duration": 2,             // 稳定持续时间
  "max_wait": 10,                      // 最大等待时间
  "remark": "等待界面稳定"
}
```

#### 3. retry_until_success - 重试直到成功

**解决问题**: 偶发性元素定位失败

```json
{
  "action": "retry_until_success",
  "target_action": {
    "action": "click_target",
    "target_selector": {"text_hints": ["登录"]}
  },
  "max_retries": 5,
  "retry_interval": 1,
  "remark": "重试点击直到成功"
}
```

### 第二阶段 - 增强功能

#### 1. wait_for_all - 等待多个条件

```json
{
  "action": "wait_for_all",
  "conditions": [
    {"type": "disappear", "target_selector": {"class": "loading"}},
    {"type": "appear", "target_selector": {"text_hints": ["登录"]}}
  ],
  "remark": "等待加载完成且登录按钮出现"
}
```

#### 2. fallback_actions - 备选操作

```json
{
  "action": "fallback_actions",
  "primary_action": {
    "action": "click_target",
    "target_selector": {"text_hints": ["其他登录方式"]}
  },
  "fallback_actions": [
    {"action": "click_target", "target_selector": {"text_hints": ["切换登录"]}}
  ],
  "remark": "主操作失败时的备选方案"
}
```

---

## 🎮 高级流程类

### 1. auto_login - 自动登录

**功能**: 完整的自动登录流程，包含账号切换和输入

**参数说明**:
```json
{
  "action": "auto_login",
  "params": {
    "login_type": "phone",             // 登录类型：phone/email/username
    "handle_switch": true,             // 是否处理登录方式切换
    "input_username": true,            // 是否输入用户名
    "input_password": true,            // 是否输入密码
    "click_login": true                // 是否点击登录按钮
  },
  "remark": "自动登录流程"
}
```

**使用示例**:
```json
{
  "step": 1,
  "action": "auto_login",
  "params": {
    "login_type": "phone",
    "handle_switch": true,
    "input_username": true,
    "input_password": true,
    "click_login": true
  },
  "remark": "执行完整的自动登录流程"
}
```

---

## 💡 最佳实践

### 时序问题解决方案

**问题**: 步骤1 (wait_if_exists) 完成后，步骤2 (click_target) 立即执行但界面还未稳定

**解决方案对比**:

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **方案1: 添加稳定性检查** | 可靠性高 | 执行时间稍长 | 界面频繁变化 |
| **方案2: 智能重试** | 执行效率高 | 可能掩盖真实问题 | 偶发性失败 |
| **方案3: 等待元素出现** | 逻辑清晰 | 需要明确知道目标元素 | 标准界面流程 |

**推荐的脚本结构**:
```json
{
  "steps": [
    {
      "step": 1,
      "action": "wait_if_exists",
      "class": "system-newResources",
      "remark": "等待热更新"
    },
    {
      "step": 1.5,
      "action": "delay",
      "params": {"seconds": 3},
      "remark": "等待界面稳定"
    },
    {
      "step": 2,
      "action": "click_target",
      "target_selector": {"text_hints": ["其他登录方式"]},
      "remark": "切换登录方式"
    },
    {
      "step": 2.5,
      "action": "delay",
      "params": {"seconds": 2},
      "remark": "等待登录方式切换完成"
    },
    {
      "step": 3,
      "action": "input",
      "text": "${account:username}",
      "remark": "输入用户名"
    }
  ]
}
```

### 脚本编写规范

#### 1. 步骤编号规范
```json
{
  "step": 1,     // 主要步骤
  "step": 1.5,   // 中间步骤（延时、等待）
  "step": 2      // 下一个主要步骤
}
```

#### 2. 容错处理
- 使用 `skip_if_not_found: true` 处理可选元素
- 设置合理的 `retry_count` 和 `retry_interval`
- 添加详细的 `remark` 说明

#### 3. 变量使用
- 统一使用 `${account:username}` 格式
- 确保账号管理器正确分配账号
- 在脚本开始前验证变量可用性

### 性能优化建议

1. **合理设置confidence值**
   - 简单元素: 0.7-0.8
   - 复杂元素: 0.8-0.9
   - 关键元素: 0.9+

2. **优化等待时间**
   - 短延时: 1-2秒（界面切换）
   - 中延时: 3-5秒（网络请求）
   - 长延时: 10+秒（热更新）

3. **减少不必要的操作**
   - 使用 `skip_if_not_found` 跳过可选步骤
   - 合并相似的连续操作
   - 避免重复的元素查找

---

## 📚 实际脚本示例

### 1. 完整登录流程

```json
{
  "type": "script",
  "name": "完整登录流程",
  "description": "包含热更新处理、登录方式切换、账号输入的完整流程",
  "steps": [
    {
      "step": 0.5,
      "class": "delay",
      "params": {"seconds": 5},
      "remark": "等待应用启动后界面稳定，避免热更新导致的黑屏影响检测"
    },
    {
      "step": 1,
      "action": "wait_if_exists",
      "class": "system-newResources",
      "polling_interval": 5000,
      "max_duration": 300,
      "confidence": 0.7135645747184753,
      "remark": "判断启动APP后是否出现热更资源图标，如果存在则需要等待新资源加载完成"
    },
    {
      "step": 1.5,
      "action": "delay",
      "params": {"seconds": 3},
      "remark": "等待热更新检测完成和界面稳定"
    },
    {
      "step": 2,
      "action": "click_target",
      "target_selector": {
        "text_hints": ["其他登录方式", "其他方式", "切换登录", "账号登录"],
        "resource_id_keywords": ["other_login", "switch_login", "login_method"],
        "class_types": ["android.widget.TextView", "android.widget.Button"],
        "skip_if_not_found": true,
        "retry_count": 3,
        "retry_interval": 2
      },
      "confidence": 0.9,
      "remark": "切换到账号密码登录模式，增加重试机制"
    },
    {
      "step": 2.5,
      "action": "delay",
      "params": {"seconds": 2},
      "remark": "等待登录方式切换完成，界面稳定后再进行下一步操作"
    },
    {
      "step": 3,
      "action": "input",
      "text": "${account:username}",
      "target_selector": {
        "placeholder": "请输入手机号",
        "clear_previous_text": true
      },
      "confidence": 0.95,
      "remark": "输入登录用户名"
    },
    {
      "step": 4,
      "action": "input",
      "text": "${account:password}",
      "target_selector": {
        "placeholder": "请输入密码",
        "clear_previous_text": true
      },
      "confidence": 0.95,
      "remark": "输入登录密码"
    },
    {
      "step": 5,
      "action": "checkbox",
      "target_selector": {
        "class_types": ["android.widget.CheckBox"],
        "type": "agreement_checkbox"
      },
      "confidence": 0.95,
      "remark": "勾选用户协议"
    },
    {
      "step": 6,
      "action": "click_target",
      "target_selector": {
        "text_hints": ["登录", "进入游戏", "立即登录"],
        "resource_id_keywords": ["login", "enter", "submit"],
        "class_types": ["android.widget.Button", "android.widget.TextView"],
        "skip_if_not_found": false
      },
      "confidence": 0.92,
      "remark": "点击登录按钮"
    }
  ]
}
```

### 2. 应用启动脚本

```json
{
  "type": "script",
  "name": "应用启动和权限处理",
  "description": "设备预处理和应用启动",
  "steps": [
    {
      "class": "device_preparation",
      "remark": "执行设备预处理：设备预处理示例、输入法检查，确保设备状态正常",      "params": {
        "check_usb": true,
        "setup_wireless": false,
        "auto_handle_dialog": true,
        "handle_screen_lock": true,
        "setup_input_method": true,
        "save_logs": false
      }
    },
    {
      "class": "app_start",
      "remark": "启动应用并处理权限",
      "params": {
        "app_name": "card2prepare-wetest",
        "package_name": "com.beeplay.card2prepare",
        "activity_name": "com.beeplay.card2prepare/com.beeplay.splash.launcher.SplashActivity",
        "handle_permission": true,
        "permission_wait": 15,
        "allow_permission": true,
        "first_only": true
      }
    }
  ]
}
```

### 3. 滑动操作脚本

```json
{
  "type": "script",
  "name": "界面滑动操作",
  "description": "演示各种滑动操作",
  "steps": [
    {
      "step": 1,
      "action": "swipe",
      "start_x": 500,
      "start_y": 1000,
      "end_x": 500,
      "end_y": 400,
      "duration": 800,
      "remark": "向上滑动屏幕"
    },
    {
      "step": 2,
      "action": "swipe",
      "start_x": 200,
      "start_y": 600,
      "end_x": 800,
      "end_y": 600,
      "duration": 500,
      "remark": "向右滑动"
    },
    {
      "step": 3,
      "action": "swipe",
      "start_x": 800,
      "start_y": 600,
      "end_x": 200,
      "end_y": 600,
      "duration": 500,
      "remark": "向左滑动返回"
    }
  ]
}
```

---

## 🔗 相关文档

- [WFGameAI回放功能完整技术文档](./WFGameAI回放功能完整技术文档.md) - 详细的技术实现文档
- [Action API参考](../wfgame-ai-server/apps/scripts/docs/wfgame_ai_action_api_reference.json) - API接口文档
- [项目开发规范](../.vscode/WFGameAI-Comprehensive-Dev-Standards.md) - 开发规范文档

---

## 🛡️ 系统弹窗自动处理参数化方案（2025-06-25补充）

### 方案说明
自动化回放过程中，常遇到系统权限、存储等弹窗。可通过 JSON 脚本参数灵活控制弹窗处理行为。

### JSON 脚本写法

**全局控制（meta 内）：**
```json
{
  "meta": {
    "auto_handle_dialog": true,
    "dialog_max_wait": 8,
    "dialog_retry_interval": 0.5,
    "dialog_duration": 1.0
  },
  "steps": [ ... ]
}
```

**单步控制（step 内，覆盖全局）：**
```json
{
  "step": 2,
  "action": "retry_until_success",
  "auto_handle_dialog": true,
  "dialog_max_wait": 6,
  "dialog_retry_interval": 0.3,
  "dialog_duration": 1.2,
  ...
}
```

**参数说明：**
- `auto_handle_dialog`：是否自动处理弹窗（true/false）
- `dialog_max_wait`：弹窗处理最大等待时间（秒）
- `dialog_retry_interval`：弹窗检测重试间隔（秒）
- `dialog_duration`：点击弹窗后等待消失的时间（秒）

如未指定，使用代码默认值。

### 代码调用 demo

```python
auto_handle = step.get('auto_handle_dialog', meta.get('auto_handle_dialog', False))
max_wait = step.get('dialog_max_wait', meta.get('dialog_max_wait', 5.0))
retry_interval = step.get('dialog_retry_interval', meta.get('dialog_retry_interval', 0.5))
duration = step.get('dialog_duration', meta.get('dialog_duration', 1.0))

if auto_handle:
    self.handle_system_dialogs(
        max_wait=max_wait,
        retry_interval=retry_interval,
        duration=duration
    )
```

---

**📝 文档版本**: v1.0
**🔄 最后更新**: 2025-06-24
**👥 维护者**: WFGameAI开发团队

---

## 📊 Action统计信息

### 已实现的Action类型统计

| 分类 | 数量 | Action列表 |
|------|------|-----------|
| **基础操作** | 3 | `click`, `click_target`, `swipe` |
| **文本操作** | 1 | `input` |
| **等待操作** | 3 | `delay`, `wait_if_exists`, `wait` |
| **应用管理** | 3 | `app_start`, `app_stop`, `device_preparation` |
| **UI元素** | 1 | `checkbox` |
| **高级流程** | 1 | `auto_login` |
| **总计** | 12 | - |

### Class元素统计

| 分类 | 数量 | 示例 |
|------|------|------|
| **系统级** | 3 | `system-newResources`, `system-cleanUpCache`, `system-skip` |
| **操作级** | 4 | `operation-close`, `operation-confirm`, `operation-back`, `operation-challenge` |
| **导航级** | 2 | `navigation-fight`, `hint-guide` |
| **工具级** | 3 | `delay`, `app_start`, `device_preparation` |
| **通用级** | 1 | `unknown` |
| **总计** | 13+ | - |
