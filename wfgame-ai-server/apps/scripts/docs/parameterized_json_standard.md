# WFGameAI 参数化JSON标准使用指南

## 概述

WFGameAI 2.0 引入了参数化 `target_selector` 标准，通过预定义的 `ElementPatterns` 实现更智能、更一致的UI元素识别。

## 参数化标准

### 支持的类型 (type)

| 类型 | 描述 | 对应的ElementPattern |
|-----|------|---------------------|
| `username_field` | 用户名输入框 | `USERNAME_PATTERNS` |
| `password_field` | 密码输入框 | `PASSWORD_PATTERNS` |
| `agreement_checkbox` | 协议勾选框 | `CHECKBOX_PATTERNS` |
| `login_button` | 登录按钮 | `LOGIN_BUTTON_PATTERNS` |
| `skip_button` | 跳过按钮 | `SKIP_BUTTON_PATTERNS` |
| `login_switch_button` | 登录方式切换按钮 | `LOGIN_SWITCH_BUTTON_PATTERNS` |

### 新格式示例

#### 传统方式（已废弃）：
```json
{
  "action": "input",
  "text": "${account:username}",
  "target_selector": {
    "text_hints": ["账号", "用户名", "username"],
    "resource_id_keywords": ["username", "account", "login"],
    "class_types": ["android.widget.EditText"],
    "content_desc_keywords": ["账号", "用户名"]
  }
}
```

#### 参数化方式（推荐）：
```json
{
  "action": "input",
  "text": "${account:username}",
  "target_selector": {
    "type": "username_field"
  }
}
```

## ElementPatterns 详细定义

### USERNAME_PATTERNS
```python
{
    'text_hints': ['账号', '用户名', 'username', 'account', '请输入账号', '请输入您的账号', '请输入手机号'],
    'resource_id_keywords': ['username', 'account', 'login', 'phone', 'mobile'],
    'class_types': ['android.widget.EditText'],
    'content_desc_keywords': ['账号', '用户名', 'username']
}
```

### PASSWORD_PATTERNS
```python
{
    'text_hints': ['密码', 'password', '请输入您的密码', '请输入密码', '验证码'],
    'resource_id_keywords': ['password', 'pass', 'pwd'],
    'class_types': ['android.widget.EditText'],
    'content_desc_keywords': ['密码', 'password'],
    'password_field': True
}
```

### CHECKBOX_PATTERNS
```python
{
    'resource_id_keywords': ['agree', 'accept', 'checkbox', 'cb_ag', 'remember'],
    'class_types': ["android.widget.CheckBox"],
    'content_desc_keywords': ['同意', '协议', '记住'],
    'checkable_priority': True
}
```

### LOGIN_BUTTON_PATTERNS
```python
{
    'text_hints': ['进入游戏', '立即登录', '登录', '登入', 'login', '开始游戏'],
    'resource_id_keywords': ['login', 'submit', 'enter', 'game', 'start'],
    'class_types': ['android.widget.Button', 'android.widget.TextView'],
    'content_desc_keywords': ['登录', '进入', '开始']
}
```

### SKIP_BUTTON_PATTERNS
```python
{
    'text_hints': ['跳过', '跳过引导', 'skip', '关闭', '稍后', '下次再说'],
    'resource_id_keywords': ['skip', 'close', 'dismiss', 'later', 'next_time'],
    'class_types': ['android.widget.Button', 'android.widget.TextView', 'android.widget.ImageView'],
    'content_desc_keywords': ['跳过', '关闭', 'skip', 'close']
}
```

### LOGIN_SWITCH_BUTTON_PATTERNS
```python
{
    'text_hints': ['其他登录方式', '其他方式', '切换登录', '账号登录', '密码登录'],
    'resource_id_keywords': ['other_login', 'switch_login', 'login_method', 'more_login', 'password_login'],
    'class_types': ['android.widget.TextView', 'android.widget.Button', 'android.view.View'],
    'content_desc_keywords': ['其他登录方式', '登录方式', '切换登录', '更多选项']
}
```

## 完整示例

```json
{
  "meta": {
    "name": "参数化登录流程",
    "description": "使用参数化target_selector的标准化脚本",
    "version": "2.0"
  },
  "steps": [
    {
      "step": 1,
      "action": "click_target",
      "target_selector": {
        "type": "login_switch_button",
        "skip_if_not_found": true
      },
      "remark": "切换到账号密码登录模式"
    },
    {
      "step": 2,
      "action": "input",
      "text": "${account:username}",
      "target_selector": {
        "type": "username_field"
      },
      "remark": "输入用户名"
    },
    {
      "step": 3,
      "action": "input",
      "text": "${account:password}",
      "target_selector": {
        "type": "password_field"
      },
      "remark": "输入密码"
    },
    {
      "step": 4,
      "action": "checkbox",
      "target_selector": {
        "type": "agreement_checkbox"
      },
      "remark": "勾选用户协议"
    },
    {
      "step": 5,
      "action": "click_target",
      "target_selector": {
        "type": "login_button"
      },
      "remark": "点击登录按钮"
    }
  ]
}
```

## 优势

1. **一致性**: 所有脚本使用相同的元素识别标准
2. **维护性**: 修改ElementPatterns即可影响所有脚本
3. **可读性**: 简洁的type参数替代复杂的匹配条件
4. **智能化**: 内置的智能元素识别算法
5. **向后兼容**: 仍然支持传统的target_selector格式

## 迁移指南

### 已更新的文件
- `2_new_user_input_complete.json`
- `2_new_user_input_nologin.json`
- `2_new_user_input_parameterized.json`
- `test_click_login.json`
- `click_target_test.json`
- `complete_automated_flow_parameterized.json`

### 迁移步骤
1. 将复杂的 `target_selector` 替换为简单的 `type` 参数
2. 更新 `remark` 字段说明使用的ElementPattern
3. 测试验证功能正常

## 注意事项

- 参数化方式依赖 `enhanced_input_handler.py` 中的ElementPatterns
- 支持额外参数如 `skip_if_not_found`、`retry_count` 等
- 传统方式仍然支持，但不推荐使用
- 新脚本应该优先使用参数化方式
