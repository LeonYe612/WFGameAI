# 应用生命周期管理系统

独立的移动应用启动/停止管理器，使用模板化配置，与脚本记录/回放功能完全隔离。

## 功能特性

- **模板化配置**: 支持为不同应用创建启动/停止模板
- **多设备管理**: 同时管理多个设备上的应用
- **状态监控**: 实时监控应用运行状态和健康检查
- **自动重启**: 应用异常停止时自动重启
- **批量操作**: 支持批量启动/停止多个应用
- **REST API**: 提供完整的REST API接口
- **命令行工具**: 提供便捷的命令行操作界面
- **交互模式**: 支持交互式操作模式

## 目录结构

```
wfgame-ai-server/apps/scripts/
├── app_lifecycle_manager.py      # 核心管理器
├── app_manager.py               # 命令行工具
├── app_lifecycle_api.py         # Django API接口
├── app_templates/               # 应用模板目录
│   ├── wangzherongyao.json     # 王者荣耀模板
│   ├── hetuala.json            # 阴阳师模板
│   └── generic_android_app.json # 通用应用模板
└── README_APP_LIFECYCLE.md     # 本文档
```

## 快速开始

### 1. 查看可用模板

```bash
# 命令行方式
python app_manager.py --action list-templates

# 或直接运行进入交互模式
python app_manager.py
```

### 2. 启动应用

```bash
# 启动王者荣耀到指定设备
python app_manager.py --action start --template wangzherongyao --device DEVICE_SERIAL

# 如果只连接了一个设备，可以省略--device参数
python app_manager.py --action start --template wangzherongyao
```

### 3. 查看应用状态

```bash
python app_manager.py --action status
```

### 4. 停止应用

```bash
python app_manager.py --action stop --template wangzherongyao --device DEVICE_SERIAL
```

## 应用模板配置

### 模板文件格式

应用模板使用JSON格式，保存在`app_templates/`目录下：

```json
{
    "name": "模板名称",
    "package_name": "应用包名",
    "activity_name": "Activity名称(可选)",
    "start_commands": [
        "启动命令列表",
        "支持{device_serial}等占位符"
    ],
    "stop_commands": [
        "停止命令列表"
    ],
    "check_commands": [
        "检查命令列表"
    ],
    "startup_wait_time": 5,
    "max_restart_attempts": 3,
    "health_check_interval": 60,
    "custom_params": {
        "自定义参数": "值"
    }
}
```

### 字段说明

- `name`: 模板名称，用于标识模板
- `package_name`: Android应用包名
- `activity_name`: 启动的Activity名称（可选）
- `start_commands`: 启动命令列表，支持占位符
- `stop_commands`: 停止命令列表，支持占位符
- `check_commands`: 检查应用是否运行的命令列表
- `startup_wait_time`: 启动后等待时间（秒）
- `max_restart_attempts`: 最大自动重启次数
- `health_check_interval`: 健康检查间隔（秒）
- `custom_params`: 自定义参数

### 命令占位符

在命令中可以使用以下占位符：

- `{device_serial}`: 设备序列号
- `{package_name}`: 应用包名
- `{activity_name}`: Activity名称
- 其他自定义参数

### 示例模板

#### 王者荣耀模板

```json
{
    "name": "wangzherongyao",
    "package_name": "com.tencent.tmgp.sgame",
    "activity_name": "SGameActivity",
    "start_commands": [
        "adb -s {device_serial} shell am force-stop {package_name}",
        "adb -s {device_serial} shell am start -n {package_name}/{activity_name}",
        "adb -s {device_serial} shell input keyevent KEYCODE_WAKEUP"
    ],
    "stop_commands": [
        "adb -s {device_serial} shell am force-stop {package_name}"
    ],
    "check_commands": [
        "adb -s {device_serial} shell pidof {package_name}"
    ],
    "startup_wait_time": 8,
    "max_restart_attempts": 3,
    "health_check_interval": 60,
    "custom_params": {
        "game_type": "moba",
        "requires_login": true
    }
}
```

## REST API 接口

### 基础URL

```
http://localhost:8000/api/scripts/app-lifecycle/
```

### API端点

#### 1. 获取应用模板

```http
GET /templates/
```

**响应示例：**
```json
{
    "templates": {
        "wangzherongyao": {
            "name": "wangzherongyao",
            "package_name": "com.tencent.tmgp.sgame",
            "startup_wait_time": 8
        }
    }
}
```

#### 2. 创建应用模板

```http
POST /templates/create/
Content-Type: application/json

{
    "name": "my_app",
    "package_name": "com.example.myapp",
    "startup_wait_time": 5
}
```

#### 3. 启动应用

```http
POST /start/
Content-Type: application/json

{
    "template_name": "wangzherongyao",
    "device_serial": "DEVICE_SERIAL",
    "extra_params": {}
}
```

#### 4. 停止应用

```http
POST /stop/
Content-Type: application/json

{
    "template_name": "wangzherongyao",
    "device_serial": "DEVICE_SERIAL"
}
```

#### 5. 重启应用

```http
POST /restart/
Content-Type: application/json

{
    "template_name": "wangzherongyao",
    "device_serial": "DEVICE_SERIAL"
}
```

#### 6. 获取应用状态

```http
GET /status/?template_name=wangzherongyao&device_serial=DEVICE_SERIAL
```

**响应示例：**
```json
{
    "status": {
        "DEVICE_SERIAL_com.tencent.tmgp.sgame": {
            "package_name": "com.tencent.tmgp.sgame",
            "device_serial": "DEVICE_SERIAL",
            "state": "running",
            "start_time": 1640995200.0,
            "restart_count": 0
        }
    }
}
```

#### 7. 获取连接的设备

```http
GET /devices/
```

**响应示例：**
```json
{
    "devices": [
        {
            "serial": "DEVICE_SERIAL_1",
            "status": "online"
        }
    ]
}
```

#### 8. 批量操作

```http
POST /batch/
Content-Type: application/json

{
    "operation": "start",
    "apps": [
        {
            "template_name": "wangzherongyao",
            "device_serial": "DEVICE1"
        },
        {
            "template_name": "hetuala",
            "device_serial": "DEVICE2"
        }
    ]
}
```

#### 9. 健康检查

```http
GET /health/
```

## 命令行工具

### 基本用法

```bash
# 显示帮助
python app_manager.py --help

# 交互模式（推荐）
python app_manager.py

# 非交互模式
python app_manager.py --action ACTION [--template TEMPLATE] [--device DEVICE]
```

### 支持的操作

- `start`: 启动应用
- `stop`: 停止应用
- `restart`: 重启应用
- `status`: 查看状态
- `list-templates`: 列出模板
- `list-devices`: 列出设备
- `interactive`: 交互模式

### 交互模式功能

1. 启动应用
2. 停止应用
3. 重启应用
4. 查看状态
5. 列出模板
6. 列出设备
7. 创建新模板
0. 退出

## 配置文件

系统使用项目根目录的`config.ini`文件进行配置：

```ini
[paths]
project_root = C:\Users\Administrator\PycharmProjects\WFGameAI
server_dir = ${project_root}\wfgame-ai-server
scripts_dir = ${server_dir}\apps\scripts
```

模板文件保存在：`{scripts_dir}/app_templates/`
日志文件保存在：`{server_dir}/apps/logs/app_lifecycle/`

## 状态说明

应用实例具有以下状态：

- `stopped`: 已停止
- `starting`: 启动中
- `running`: 运行中
- `stopping`: 停止中
- `error`: 错误状态
- `unknown`: 未知状态

## 监控机制

系统会自动监控运行中的应用：

1. **健康检查**: 定期检查应用是否仍在运行
2. **自动重启**: 应用意外停止时自动重启（可配置最大重启次数）
3. **状态更新**: 实时更新应用状态
4. **资源清理**: 自动清理停止的应用实例

## 错误处理

### 常见错误及解决方案

1. **ADB未连接**
   - 确保ADB已安装并在PATH中
   - 检查设备连接状态

2. **应用启动失败**
   - 检查包名是否正确
   - 确保应用已安装到目标设备

3. **权限问题**
   - 确保ADB有足够权限
   - 检查设备是否允许ADB调试

### 日志查看

```bash
# 查看应用生命周期管理器日志
tail -f wfgame-ai-server/apps/logs/app_lifecycle/app_lifecycle.log
```

## 集成指南

### 在其他脚本中使用

```python
from app_lifecycle_manager import AppLifecycleManager

# 创建管理器实例
manager = AppLifecycleManager()

# 启动应用
success = manager.start_app("wangzherongyao", "DEVICE_SERIAL")

# 检查状态
status = manager.get_app_status()

# 清理资源
manager.cleanup()
```

### 在Web应用中使用

参考`app_lifecycle_api.py`中的Django API集成示例。

## 扩展开发

### 添加新的应用模板

1. 在`app_templates/`目录创建新的JSON文件
2. 按照模板格式配置启动/停止命令
3. 重启管理器或调用API重新加载

### 自定义命令执行器

可以扩展`AppLifecycleManager`类，重写命令执行方法：

```python
class CustomAppLifecycleManager(AppLifecycleManager):
    def _execute_commands(self, commands, operation_name):
        # 自定义命令执行逻辑
        pass
```

## 安全注意事项

1. **命令注入**: 模板中的命令会直接执行，请确保命令安全
2. **权限控制**: 建议在生产环境中添加适当的权限控制
3. **设备访问**: 确保只有授权的设备可以被管理

## 故障排除

### 常见问题

1. **模板加载失败**
   - 检查JSON格式是否正确
   - 确保文件编码为UTF-8

2. **应用无法启动**
   - 验证包名和Activity名称
   - 检查设备连接和权限

3. **监控线程异常**
   - 查看日志文件获取详细错误信息
   - 重启管理器实例

### 调试技巧

1. 使用`--action status`查看当前状态
2. 检查日志文件获取详细信息
3. 使用交互模式逐步操作

## 更新日志

### v1.0.0 (2025-05-26)
- 初始版本发布
- 支持基本的应用启动/停止功能
- 提供命令行和API接口
- 实现模板化配置系统
- 添加应用状态监控功能

## 贡献指南

欢迎提交问题和改进建议。在提交代码前，请确保：

1. 代码符合PEP 8规范
2. 添加适当的注释和文档
3. 测试新功能的正确性

## 许可证

本项目采用MIT许可证。
