# WFGameAI Action 使用手册（精简版）

> **📋 快速参考指南**
> 本文档提供WFGameAI框架中所有Action类型的快速参考，包含核心参数和使用示例。
> **详细文档**: [完整技术文档](./WFGameAI回放功能完整技术文档.md)

---

## 🎯 Action 快速参考

### 常用Actions

| Action | 功能 | 必需参数 | 示例 |
|--------|------|----------|------|
| `click` | 基础点击 | `class` | `{"action": "click", "class": "login-button"}` |
| `click_target` | 智能点击 | `target_selector` | 见下方详细示例 |
| `input` | 文本输入 | `text`, `target_selector` | `{"action": "input", "text": "${account:username}"}` |
| `delay` | 延时等待 | `params.seconds` | `{"action": "delay", "params": {"seconds": 3}}` |
| `swipe` | 滑动操作 | `start_x/y`, `end_x/y` | `{"action": "swipe", "start_x": 500, "start_y": 800, "end_x": 500, "end_y": 400}` |
| `wait_if_exists` | 条件等待 | `class` | `{"action": "wait_if_exists", "class": "loading-icon"}` |
| `app_start` | 启动应用 | `params.package_name` | 见应用管理部分 |
| `checkbox` | 复选框 | `target_selector` | `{"action": "checkbox", "target_selector": {...}}` |
| `auto_login` | 自动登录 | `params` | `{"action": "auto_login", "params": {"login_type": "phone"}}` |

---

## 📱 核心Action详解

### 1. click_target - 智能点击（推荐）

**最常用的点击方式，支持多种定位策略**

```json
{
  "action": "click_target",
  "target_selector": {
    "text_hints": ["登录", "进入游戏"],           // 按钮文字提示
    "resource_id_keywords": ["login", "btn"],   // 资源ID关键词
    "class_types": ["android.widget.Button"],   // 控件类型
    "skip_if_not_found": true,                  // 找不到时跳过
    "retry_count": 3                            // 重试次数
  },
  "remark": "智能点击登录按钮"
}
```

### 2. input - 文本输入

**支持账号变量替换的文本输入**

```json
{
  "action": "input",
  "text": "${account:username}",              // 支持变量: username, password, phone
  "target_selector": {
    "placeholder": "请输入用户名",
    "clear_previous_text": true           // 清除原有文本
  },
  "remark": "输入用户名"
}
```

### 3. wait_if_exists - 条件等待

**处理热更新、加载界面的最佳选择**

```json
{
  "action": "wait_if_exists",
  "class": "system-newResources",         // 热更新图标
  "polling_interval": 5000,              // 检查间隔(毫秒)
  "max_duration": 300,                   // 最大等待时间(秒)
  "remark": "等待热更新完成"
}
```

---

## 🏗️ 应用管理

### app_start - 应用启动

```json
{
  "class": "app_start",
  "params": {
    "package_name": "com.example.app",
    "handle_permission": true,            // 自动处理权限弹窗
    "permission_wait": 15,
    "allow_permission": true
  },
  "remark": "启动应用并处理权限"
}
```

### device_preparation - 设备预处理

```json
{
  "class": "device_preparation",
  "params": {
    "check_usb": true,
    "configure_permissions": true,
    "handle_screen_lock": true
  },
  "remark": "设备初始化"
}
```

---

## 📝 常见脚本模式

### 1. 完整登录流程

```json
{
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
      "action": "delay",
      "params": {"seconds": 3},
      "remark": "等待界面稳定"
    },
    {
      "step": 3,
      "action": "click_target",
      "target_selector": {
        "text_hints": ["其他登录方式", "账号登录"]
      },
      "remark": "切换登录方式"
    },
    {
      "step": 4,
      "action": "input",
      "text": "${account:username}",
      "target_selector": {"placeholder": "请输入用户名"},
      "remark": "输入用户名"
    },
    {
      "step": 5,
      "action": "input",
      "text": "${account:password}",
      "target_selector": {"placeholder": "请输入密码"},
      "remark": "输入密码"
    },
    {
      "step": 6,
      "action": "click_target",
      "target_selector": {"text_hints": ["登录", "立即登录"]},
      "remark": "点击登录"
    }
  ]
}
```

### 2. 应用启动模板

```json
{
  "steps": [
    {
      "class": "device_preparation",
      "remark": "设备预处理"
    },
    {
      "class": "app_start",
      "params": {
        "package_name": "com.your.app",
        "handle_permission": true
      },
      "remark": "启动应用"
    },
    {
      "step": 1,
      "action": "delay",
      "params": {"seconds": 5},
      "remark": "等待应用完全启动"
    }
  ]
}
```

---

## 💡 最佳实践

### 时序控制
- **热更新处理**: 使用 `wait_if_exists` + `delay` 组合
- **界面切换**: 操作后添加 1-3 秒 `delay`
- **网络等待**: 使用较长的 `max_duration` (300秒)

### 元素定位
- **优先使用**: `click_target` 而不是 `click`
- **多重保险**: 在 `text_hints` 中提供多个文字选项
- **容错处理**: 设置 `skip_if_not_found: true`

### 账号管理
- **变量使用**: `${account:username}`, `${account:password}`
- **输入清理**: 设置 `clear_previous_text: true`

### 调试技巧
- **详细备注**: 每个步骤添加清晰的 `remark`
- **步骤编号**: 使用 1, 1.5, 2 的递增编号
- **置信度**: 关键元素设置较高的 `confidence` (0.9+)

---

## 🔧 故障排除

| 问题 | 解决方案 |
|------|----------|
| 点击失败 | 增加 `retry_count`, 检查 `text_hints` |
| 界面未稳定 | 增加 `delay` 时间 |
| 元素找不到 | 使用 `skip_if_not_found: true` |
| 输入失败 | 检查 `placeholder` 匹配，设置 `clear_previous_text` |
| 热更新卡住 | 调整 `polling_interval` 和 `max_duration` |

---

**📝 版本**: v2.0 精简版 | **🔄 更新**: 2025-06-24
