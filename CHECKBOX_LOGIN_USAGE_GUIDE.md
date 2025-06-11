# Checkbox和登录按钮功能使用指南

## 功能概述

增强输入处理器现在完全支持智能登录操作器的所有功能，包括：
- 📝 **智能文本输入** - 用户名和密码自动识别输入
- ☑️ **Checkbox自动勾选** - 协议同意框智能识别和操作
- 🔘 **登录按钮自动点击** - 登录按钮智能识别和点击
- 🚀 **一键自动登录** - 完整登录流程自动化

## JSON配置方式

### 方式1：分步操作 (推荐用于复杂场景)

```json
{
  "steps": [
    {
      "step": 1,
      "action": "input",
      "text": "${account:username}",
      "target_selector": {
        "placeholder": "请输入手机号"
      },
      "confidence": 0.95,
      "timestamp": "2025-06-11 10:00:00.000000",
      "remark": "输入登录用户名"
    },
    {
      "step": 2,
      "action": "input",
      "text": "${account:password}",
      "target_selector": {
        "placeholder": "请输入密码"
      },
      "confidence": 0.95,
      "timestamp": "2025-06-11 10:00:05.000000",
      "remark": "输入登录密码"
    },
    {
      "step": 3,
      "action": "checkbox",
      "target_selector": {
        "type": "agreement_checkbox"
      },
      "confidence": 0.95,
      "timestamp": "2025-06-11 10:00:10.000000",
      "remark": "勾选用户协议"
    },
    {
      "step": 4,
      "action": "click",
      "target_selector": {
        "type": "login_button"
      },
      "confidence": 0.92,
      "timestamp": "2025-06-11 10:00:15.000000",
      "remark": "点击登录按钮"
    }
  ]
}
```

### 方式2：一键自动登录 (推荐用于简单场景)

```json
{
  "steps": [
    {
      "step": 1,
      "action": "auto_login",
      "params": {
        "username": "${account:username}",
        "password": "${account:password}"
      },
      "confidence": 0.95,
      "timestamp": "2025-06-11 10:00:00.000000",
      "remark": "执行完整自动登录流程"
    }
  ]
}
```

## Action类型详解

### 1. `input` - 文本输入
- **功能**: 智能识别并输入文本到目标输入框
- **参数**:
  - `text`: 输入的文本内容，支持 `${account:username}` 和 `${account:password}` 参数替换
  - `target_selector.placeholder`: 目标输入框的提示文本

### 2. `checkbox` - 勾选框操作
- **功能**: 自动识别并勾选协议同意框
- **参数**:
  - `target_selector.type`: 固定为 `"agreement_checkbox"`
- **智能识别**:
  - 优先识别 `android.widget.CheckBox` 控件
  - 支持 `checkable=true` 的元素
  - 使用40分权重的优先级算法

### 3. `click` with `type: login_button` - 登录按钮点击
- **功能**: 自动识别并点击登录按钮
- **参数**:
  - `target_selector.type`: 固定为 `"login_button"`
- **智能识别**:
  - 识别包含"登录"、"进入游戏"、"立即登录"等文本的按钮
  - 支持 `android.widget.Button` 和 `android.widget.TextView` 类型

### 4. `auto_login` - 完整自动登录
- **功能**: 一次性完成整个登录流程
- **参数**:
  - `params.username`: 用户名，支持参数替换
  - `params.password`: 密码，支持参数替换
- **执行流程**:
  1. 自动识别用户名输入框并输入
  2. 自动识别密码输入框并输入
  3. 自动识别并勾选协议checkbox (可选)
  4. 自动识别并点击登录按钮

## 智能识别算法

### 用户名输入框识别模式
- **文本提示**: 账号、用户名、username、account、请输入账号、请输入您的账号、请输入手机号
- **Resource ID**: username、account、login、phone、mobile
- **控件类型**: android.widget.EditText

### 密码输入框识别模式
- **文本提示**: 密码、password、请输入您的密码、请输入密码、验证码
- **Resource ID**: password、pass、pwd
- **控件类型**: android.widget.EditText
- **特殊属性**: password=true

### Checkbox识别模式
- **Resource ID**: agree、accept、checkbox、cb_ag、remember
- **控件类型**: android.widget.CheckBox
- **特殊属性**: checkable=true (40分优先权重)

### 登录按钮识别模式
- **文本内容**: 进入游戏、立即登录、登录、登入、login、开始游戏
- **Resource ID**: login、submit、enter、game、start
- **控件类型**: android.widget.Button、android.widget.TextView

## 账号参数替换

系统支持自动账号分配和参数替换：

- `${account:username}` → 自动替换为分配给设备的用户名
- `${account:password}` → 自动替换为分配给设备的密码

账号配置文件位置：`wfgame-ai-server/apps/scripts/datasets/accounts_info/accounts.txt`

## 示例文件

1. **scene1_input_steps.json** - 基础登录场景
2. **complete_login_example.json** - 完整分步登录示例
3. **auto_login_example.json** - 一键登录示例

## 执行日志

所有操作都会记录详细的执行日志：

```json
{
  "tag": "function",
  "depth": 1,
  "time": 1749619520.123,
  "data": {
    "name": "check_checkbox",
    "call_args": {
      "target_selector": {"type": "agreement_checkbox"}
    },
    "start_time": 1749619520.123,
    "ret": {"success": true},
    "end_time": 1749619520.623,
    "desc": "勾选用户协议",
    "title": "#3 勾选用户协议"
  }
}
```

## 最佳实践

1. **简单登录场景**: 使用 `auto_login` 一键完成
2. **复杂登录场景**: 使用分步操作，便于调试和控制
3. **参数替换**: 始终使用 `${account:username}` 和 `${account:password}` 而不是硬编码
4. **备注信息**: 为每个步骤添加清晰的 `remark` 描述
5. **时间间隔**: 合理设置步骤间的时间间隔

## 故障排除

### 常见问题

1. **找不到输入框**
   - 检查 `placeholder` 是否匹配实际界面
   - 使用UI结构检测器分析界面元素

2. **Checkbox勾选失败**
   - 确认界面中存在可勾选元素
   - 检查元素是否有 `checkable=true` 属性

3. **登录按钮识别失败**
   - 确认按钮文本包含登录相关关键词
   - 检查按钮是否为可点击状态

### 调试工具

使用 `ui_structure_detector.py` 分析当前界面：

```bash
python ui_structure_detector.py
```

这将生成详细的UI元素分析报告，帮助调试识别问题。

## 更新日志

- ✅ 集成智能登录操作器的全部功能
- ✅ 支持checkbox智能识别和操作
- ✅ 支持登录按钮智能识别和点击
- ✅ 支持完整自动登录流程
- ✅ 完整的JSON配置支持
- ✅ 详细的执行日志记录
- ✅ 参数替换和账号管理集成
