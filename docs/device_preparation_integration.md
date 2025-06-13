# 设备预处理集成到JSON脚本控制的使用说明

## 概述

设备预处理功能已成功集成到JSON脚本控制系统中。现在可以通过在脚本的`steps`中添加`"class": "device_preparation"`步骤来控制设备预处理的运行时机。

## JSON脚本格式

### 基本格式
```json
{
  "description": "设备预处理示例脚本",
  "author": "WFGameAI",
  "version": "1.0",
  "steps": [
    {
      "step": 1,
      "class": "device_preparation",
      "action": "device_preparation",
      "remark": "设备预处理步骤描述",
      "params": {
        "check_usb": true,
        "setup_wireless": true,
        "configure_permissions": true,
        "handle_screen_lock": true,
        "setup_input_method": true,
        "save_logs": false
      }
    }
  ]
}
```

### 参数说明

| 参数名 | 类型 | 默认值 | 说明 |
|-------|------|-------|------|
| `check_usb` | boolean | true | 是否检查USB连接状态 |
| `setup_wireless` | boolean | true | 是否配置无线连接 |
| `configure_permissions` | boolean | true | 是否配置设备权限 |
| `handle_screen_lock` | boolean | true | 是否处理屏幕锁定 |
| `setup_input_method` | boolean | true | 是否设置输入法 |
| `save_logs` | boolean | false | 是否保存预处理日志 |

## 使用场景

### 1. 脚本开始前的设备预处理
```json
{
  "steps": [
    {
      "class": "device_preparation",
      "remark": "脚本执行前确保设备状态正常",
      "params": {
        "check_usb": true,
        "setup_wireless": true,
        "configure_permissions": true,
        "handle_screen_lock": true,
        "setup_input_method": true,
        "save_logs": false
      }
    },
    {
      "class": "app_start",
      "remark": "启动测试应用",
      "params": {
        "app_name": "com.example.testapp"
      }
    }
  ]
}
```

### 2. 特定操作前的设备准备
```json
{
  "steps": [
    {
      "class": "app_start",
      "remark": "启动应用",
      "params": {
        "app_name": "com.example.testapp"
      }
    },
    {
      "class": "device_preparation",
      "remark": "重要操作前确保设备状态",
      "params": {
        "check_usb": false,
        "setup_wireless": false,
        "configure_permissions": true,
        "handle_screen_lock": true,
        "setup_input_method": false,
        "save_logs": true
      }
    }
  ]
}
```

### 3. 最小化设备预处理
```json
{
  "steps": [
    {
      "class": "device_preparation",
      "remark": "仅执行必要的设备检查",
      "params": {
        "check_usb": true,
        "setup_wireless": false,
        "configure_permissions": false,
        "handle_screen_lock": true,
        "setup_input_method": false,
        "save_logs": false
      }
    }
  ]
}
```

## 执行日志

设备预处理步骤会在执行日志中记录详细信息：

```
🔧 开始设备预处理: 脚本执行前确保设备状态正常
配置参数: USB检查=true, 无线连接=true, 权限配置=true
           屏幕解锁=true, 输入法设置=true, 保存日志=false
🔍 执行USB连接检查...
📶 配置无线连接...
🔒 配置设备权限...
🔓 处理屏幕锁定...
⌨️ 设置输入法...
✅ 设备预处理完成，结果: 成功
```

## 错误处理

- 如果某个预处理步骤失败，系统会记录错误但继续执行其他步骤
- USB连接检查失败会停止后续预处理步骤
- 其他步骤失败只会显示警告，不会中断脚本执行

## 注意事项

1. 设备预处理步骤通常应该放在脚本的开始部分
2. 如果脚本中有多个设备预处理步骤，每个步骤都会独立执行
3. `save_logs`参数控制是否保存详细的预处理日志到文件
4. 设备预处理可能需要较长时间，请确保设备连接稳定

## 示例脚本文件

参考示例文件：`testcase/device_preparation_example.json`
