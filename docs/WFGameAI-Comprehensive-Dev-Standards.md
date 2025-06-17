# WFGame AI 综合开发规范

## 一、项目概述

### 1.1 项目启动

- **服务启动命令**: `python start_wfgame_ai.py`

### 1.2 技术框架

- **开发语言**: Python 3.9
- **后端框架**: Django
- **前端框架**: VUE3
- **数据库**: MySQL
- **Python 环境路径**: `F:\QA\Software\anaconda3\envs\py39_yolov10\python.exe`

### 1.3 核心开发原则

- **统一请求方法**: 全部使用 POST 请求
- **路径规范**: 全局禁止使用绝对路径，统一使用 `config.ini` 文件管理路径配置
- **系统支持**: 训练模型时仅需支持 Windows（CUDA），不用支持 Mac（MPS）系统
- **基本排版**: 如果每行代码中间有超过 4 个空格，则需要仔细检查是否排版未换行

---

## 二、API 开发规范

### 2.1 API 请求方法规范

#### 2.1.1 统一使用 POST 请求

- 所有 API 端点必须支持 POST 方法，禁止使用 GET/PUT/DELETE
- 在 APIView 中添加 `http_method_names = ['post']`
- 在 ViewSet 中添加同样配置
- action 装饰器必须指定 `methods=['post']`

#### 2.1.2 权限控制

- 所有 API 视图必须允许匿名访问
- 在所有视图类中添加 `permission_classes = [AllowAny]`
- 禁止使用需要身份验证的权限类

#### 2.1.3 路由配置

- 避免 URL 路由冲突，每个 API 路径对应唯一视图
- 禁止多个视图指向同一 URL 路径
- API 路径必须遵循 RESTful 规范，例如 `/api/devices/scan/`
- 在 include 其他应用的 urls.py 时必须注意路径前缀

#### 2.1.4 错误处理

- 400 错误: 确保提供所有必填字段，API 设计时最小化必填字段
- 404 错误: 确保所有路由正确配置，前端调用存在的 API 路径
- 405 错误: 确保视图类允许正确的 HTTP 方法
- 禁止直接抛出未处理的异常，必须捕获并返回友好错误信息

#### 2.1.5 请求与响应

- API 参数验证必须提供清晰错误信息
- 响应必须使用统一格式，错误时包含 detail 字段
- 成功操作返回 HTTP 200 状态码
- 前端调用 API 时必须设置 Content-Type 为 application/json

#### 2.1.6 开发实施规范

- 在思考之后直接在原文件内进行修改和实现功能，不要只说而不改代码
- 如果遇到文件或文件夹缺失，允许直接创建
- 禁止任何形式的伪代码
- 禁止使用绝对路径，公用目录统一使用 `config.ini` 文件进行管理

#### 2.1.7 脚本执行规范

- 脚本步骤中如果缺少 `action` 字段，系统将自动设置默认值为 `"click"`
- 这确保了向后兼容性，现有脚本无需修改即可正常运行
- 支持的 action 类型：`click`、`swipe`、`wait`、`wait_if_exists`、`app_start`、`input`等

```json
{
  "step": 1,
  "class": "operation-close",
  // action字段可以省略，系统将自动设置为"click"
  "confidence": 0.93,
  "timestamp": "2025-04-07 18:40:12.664292",
  "remark": "启动游戏后先有一个公告弹窗，点击关闭"
}
```

#### 2.1.8 文本输入操作规范

- 支持 `"action": "input"` 类型用于文本输入操作（用户名、密码等）
- 使用参数化语法 `${account:username}` 和 `${account:password}` 引用账户信息
- 系统自动检测输入焦点，优先使用 placeholder 属性，备选键盘状态检测
- 账户信息从 CSV 文件读取，按设备连接顺序分配，独占使用

##### 文本输入示例

```json
{
  "step": 1,
  "action": "input",
  "class": "username-field",
  "text": "${account:username}",
  "confidence": 0.95,
  "timestamp": "2025-04-07 18:40:15.123456",
  "remark": "输入用户名"
},
{
  "step": 2,
  "action": "input",
  "class": "password-field",
  "text": "${account:password}",
  "confidence": 0.95,
  "timestamp": "2025-04-07 18:40:18.654321",
  "remark": "输入密码"
}
```

##### 账户管理规范

- **账户文件格式**: CSV 格式，逗号分隔，无标题行
- **文件位置**: `apps/scripts/accounts.txt`
- **分配机制**: 按设备连接顺序自动分配，每个设备独占一个账户
- **参数解析**: 支持 `${account:username}` 和 `${account:password}` 语法
- **错误处理**: 显示明显错误信息，无重试机制，无加密存储

##### 账户文件示例 (accounts.txt)

```
user1,password1
user2,password2
user3,password3
```

##### 焦点检测机制

1. **首选方式**: 检测 UI 元素的 placeholder 属性判断是否为输入字段
2. **备选方式**: 通过键盘状态检测当前是否有输入焦点
3. **焦点管理**: 自动点击目标元素获取输入焦点
4. **输入执行**: 使用 adb shell input 命令进行文本输入

#### 2.1.9 登录功能完整实现

系统已完整实现登录自动化功能，包含以下核心组件：

##### 2.1.9.1 账号管理系统

- **文件**: `account_manager.py`
- **数据源**: `accounts.txt` (CSV 格式：用户名,密码)
- **分配机制**: 按设备连接顺序自动分配，独占使用
- **释放机制**: 脚本执行完成后自动释放账号
- **安全**: 密码日志自动隐藏，无加密存储

##### 2.1.9.2 输入处理器

- **文件**: `input_handler.py`
- **焦点检测**: 优先使用 placeholder 属性定位，备选键盘状态检测
- **文本输入**: 分段输入机制，支持长文本处理
- **错误处理**: 完善的错误提示和重试机制

##### 2.1.9.3 参数化语法

- **用户名**: `${account:username}` - 自动替换为分配的用户名
- **密码**: `${account:password}` - 自动替换为分配的密码，日志中隐藏显示
- **目标选择器**: `"target_selector": {"placeholder": "提示文本"}` - 通过 placeholder 定位输入框

##### 2.1.9.4 脚本示例

```json
{
  "steps": [
    {
      "action": "input",
      "text": "${account:username}",
      "target_selector": {
        "placeholder": "用户名"
      },
      "remark": "输入用户名"
    },
    {
      "action": "input",
      "text": "${account:password}",
      "target_selector": {
        "placeholder": "密码"
      },
      "remark": "输入密码"
    }
  ]
}
```

##### 2.1.9.5 集成状态

- ✅ replay_script.py 已集成 input action 处理逻辑
- ✅ 账号分配和释放机制已实现
- ✅ 参数替换功能已完成
- ✅ 焦点检测综合方案已实现
- ✅ 错误处理和日志隐藏已完成
- ✅ 所有组件集成测试通过

### 2.2 API 示例代码

```python
# 正确的APIView配置
class MyApiView(views.APIView):
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法

    def post(self, request):
        # 处理请求
        return Response({"detail": "操作成功"})

# 正确的ViewSet配置
class MyViewSet(viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MySerializer
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法

    @action(detail=True, methods=['post'])
    def my_custom_action(self, request, pk=None):
        # 处理请求
        return Response({"detail": "操作成功"})
```

### 2.3 前端 API 调用示例

```javascript
// 正确的API调用方式
fetch("/api/endpoint/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
})
  .then((res) => res.json())
  .then((data) => {
    // 处理响应
  })
  .catch((err) => {
    // 错误处理
  });
```

---

## 三、代码开发规范

### 3.1 基本原则

#### 3.1.1 修改方式

- 直接在原文件上修改
- 分析后直接在原文件内改动代码
- 添加详细的注释

#### 3.1.2 核心规则

- 全局禁止出现/使用绝对路径（统一使用 `config.ini` 管理）

#### 3.1.3 修复规则

- 禁止为修复问题创建新的文件或函数
- 禁止增加或使用 `cleanup_unused_files`！
- 所有修复必须直接在原始文件中进行
- 必须在文件内添加注释说明修改的内容和目的
- 讲清楚原因后直接生成或修复代码

### 3.2 数据处理规则（严格执行）

**绝对禁止项**：

- 创建任何假数据、硬编码数据、测试数据、示例数据、演示数据或写死的数据
- 在代码中写死项目名称如"Warframe"、"warframe"、"测试项目"、"测试数据"等任何虚假信息
- 创建占位数据、默认数据或预设数据
- 在测试代码中创建任何持久化的假数据
- 使用游戏名称、虚构项目名称、示例名称作为硬编码数据
- 在代码中包含任何写死的项目名称、设备名称、用户名称等信息

**必须执行项**：

- 如果暂无真实数据，必须显示"无数据"、"暂无数据"或空状态
- 所有数据必须来自用户的真实操作或系统的实际运行
- 数据库中不允许存在任何虚假记录或测试记录
- 测试代码只能验证功能逻辑，不得创建任何实际数据记录
- 违反此规则将被视为严重的代码质量问题
- 任何包含硬编码数据的代码都必须立即修复或删除

### 3.3 代码提交规范

- 提交前必须验证修复是否解决了问题
- 提交后必须验证是否有低级的缩进错误
- 每次修改必须提供完整的测试方法和预期结果
- 禁止提交未经测试的代码

---

## 四、Python 代码规范

### 4.1 导入规则

```python
# 标准库导入
import os
import sys
import json

# 第三方库导入
import numpy as np
import torch
import cv2

# 本地模块导入
from utils.logger import Logger
from models.yolo import YOLO
```

### 4.2 命名规范

#### 4.2.1 变量命名

```python
# 常量使用大写
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30

# 普通变量使用小写下划线
device_name = "OnePlus"
current_step = 0

# 私有变量以单下划线开头
_internal_counter = 0
```

#### 4.2.2 函数命名

```python
# 公共函数使用小写下划线
def process_image(frame):
    pass

# 私有函数以单下划线开头
def _internal_process():
    pass

# 类方法使用驼峰
def processNextFrame(self):
    pass
```

#### 4.2.3 类命名

```python
# 类名使用驼峰
class DeviceManager:
    pass

class UIDetector:
    pass
```

### 4.3 数据库表命名规范

#### 4.3.1 表名前缀规则

- 所有新建的 AI 项目相关表必须使用 `ai_` 前缀
- 保持与现有系统表（`tb_` 前缀）区分
- 表名使用小写下划线命名法

#### 4.3.2 示例

```python
class YourModel(models.Model):
    # ... fields here ...

    class Meta:
        db_table = 'ai_your_table_name'  # 必须使用 ai_ 前缀
```

#### 4.3.3 现有示例

- `ai_device` - 设备表
- `ai_devicelog` - 设备日志表
- `ai_script` - 脚本表
- `ai_script_execution` - 脚本执行记录表

#### 4.3.4 命名规则详解

1. **前缀要求**

   - 必须使用 `ai_` 作为前缀
   - 不允许使用其他前缀（如 `tb_`）

2. **表名格式**

   - 全部小写字母
   - 使用下划线分隔单词
   - 使用名词或名词短语

3. **命名建议**

   - 使用清晰、描述性的名称
   - 避免使用缩写（除非是广泛接受的缩写）
   - 如果是关联表，应体现出两个实体的关系

4. **例外情况**
   - 特殊情况需要使用其他前缀时，必须经过团队讨论并记录在文档中

### 4.4 格式规范

#### 4.4.1 缩进

- 使用 4 个空格进行缩进
- 不使用制表符

#### 4.4.2 行长度

- 最大行长度为 120 字符
- 超长行使用括号换行

#### 4.4.3 空行

- 类定义之间空两行
- 方法定义之间空一行
- 相关代码块之间空一行

#### 4.4.4 注释

```python
# 单行注释使用 # 加空格
# 这是一个单行注释

"""
多行注释使用三引号
第一行空行
具体描述从第二行开始
"""
```

### 4.5 文档字符串

#### 4.5.1 函数文档

```python
def process_device(device_name: str, timeout: int = 30) -> bool:
    """
    处理设备连接和初始化。

    Args:
        device_name: 设备名称
        timeout: 超时时间（秒）

    Returns:
        bool: 处理是否成功

    Raises:
        DeviceConnectionError: 设备连接失败时抛出
    """
    pass
```

#### 4.5.2 类文档

```python
class DeviceManager:
    """
    设备管理器类。

    负责管理设备连接、状态监控和资源释放。

    Attributes:
        devices (List[str]): 已连接设备列表
        current_device (str): 当前活动设备
    """
    pass
```

### 4.6 异常处理

```python
try:
    process_device()
except DeviceError as e:
    logger.error(f"设备处理失败: {e}")
    raise
finally:
    cleanup_resources()
```

### 4.7 类型注解

```python
from typing import List, Dict, Optional

def process_results(
    results: List[Dict[str, float]],
    threshold: Optional[float] = None
) -> bool:
    pass
```

---

## 五、项目结构规范

### 5.1 文件命名

- 模块文件名：小写下划线 (例如: `device_manager.py`)
- 测试文件名：以 `test_` 开头 (例如: `test_device_manager.py`)
- 配置文件名：小写 (例如: `config.ini`)

### 5.2 目录结构

```
wfgame-ai-server/
├── apps/               # Django 应用包
│   ├── scripts/        # 脚本管理模块
│   └── devices/        # 设备管理模块
├── config.ini          # 配置文件
├── start_wfgame_ai.py  # 启动脚本
└── manage.py           # Django 管理脚本
```

### 5.3 资源目录

- **前端页面文件资源存放目录**: `WFGameAI\wfgame-ai-server\staticfiles`
- **前端 web 页面文件目录**: `WFGameAI\wfgame-ai-server\staticfiles\pages`
- **Airtest 报告静态资源**: airtest 报告生成需要静态资源（CSS/JS 等静态资源目录）是在 airtest 包的 report/ 目录下

---

## 六、配置管理规范

### 6.1 环境变量

- 使用 `config.ini` 文件而非环境变量
- 所有路径都必须使用相对路径，禁止硬编码绝对路径

### 6.2 配置文件

```ini
[paths]
# 脚本目录
scripts_dir = ${server_dir}/apps/scripts

# 测试用例目录
testcase_dir = ${server_dir}/apps/scripts/testcase

# 报告目录
reports_dir = ${server_dir}/outputs/WFGameAI-reports
```

---

## 七、测试与监控规范

### 7.1 API 接口测试

- 修改 API 后必须重新启动服务进行测试，确认 HTTP 方法和权限设置正确
- 使用 Postman 或前端调用验证端点可访问性

### 7.2 设备预处理与脚本执行分离

- **设备预处理阶段**：在脚本执行前完成，包括设备连接检查、权限设置、屏幕解锁等
- **脚本执行阶段**：只执行脚本中定义的步骤，不进行额外的设备操作
- **分离原则**：设备状态检查不应包含可能干扰脚本执行的操作（如自动滑动、点击等）

#### 7.2.1 设备状态检查优化

```python
def check_device_status(device, device_name):
    """
    检查设备状态，确保设备可用且屏幕处于正确状态
    注意：移除了自动滑动操作，避免干扰实际脚本执行
    """
    try:
        # 基本连接测试
        device.shell("echo test")

        # 检查屏幕状态
        display_state = device.shell("dumpsys power | grep 'mHoldingDisplaySuspendBlocker'")
        if "true" not in display_state.lower():
            device.shell("input keyevent 26")  # 仅使用电源键唤醒
            time.sleep(1)

        return True
    except Exception as e:
        print(f"设备 {device_name} 状态检查失败: {e}")
        return False
```

### 7.2 UI 自动化测试

#### 7.2.1 截图命名规范

```
screenshot_20250515_143045.png  # 截图_年月日_时分秒
```

#### 7.2.2 测试用例格式

```json
{
  "name": "登录测试",
  "steps": [
    {
      "action": "click",
      "target": "login_button",
      "screenshot": "login_screen.png"
    }
  ]
}
```

#### 7.2.3 图像处理标准

```python
# 灰度转换
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

# 应用阈值
_, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

# 查找轮廓
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```

### 7.3 YOLO 模型测试

#### 7.3.1 系统配置要求

**Windows 配置**：

- Intel(R) Core(TM) i7-14700 2.10 GHz
- 显示卡 NVIDIA GeForce RTX 4090
- RAM 32.0 GB
- 64 位操作系统, 基于 x64 的处理器

**Mac 配置**：

- Apple M2 Pro
- RAM 16GB

#### 7.3.2 数据准备

```python
# 数据集路径设置
train_path = os.path.join("datasets", "train")
valid_path = os.path.join("datasets", "valid")

# 数据加载与预处理
dataset = YOLO.load_dataset(train_path, augment=True)
```

#### 7.3.3 训练配置

```python
# 训练参数
config = {
    "epochs": 100,
    "batch_size": 16,
    "img_size": 640,
    "device": "cuda:0"
}

# 模型训练
model.train(**config)
```

#### 7.3.4 模型评估

```python
# 验证
results = model.validate(valid_path)
precision = results["precision"]
recall = results["recall"]
mAP = results["mAP_0.5"]
```

### 7.4 错误监控

- 注意日志中的请求错误，特别是 404/405/403/400/ModuleNotFoundError 错误
- 发现错误需立即修复对应视图类的配置

---

## 八、日志规范

### 8.1 日志级别

```python
# 错误日志
logger.error("连接设备失败")

# 警告日志
logger.warning("设备连接不稳定")

# 信息日志
logger.info("设备连接成功")

# 调试日志
logger.debug("开始连接设备")
```

### 8.2 日志格式

```
[2025-05-15 14:30:45] [INFO] [device_manager.py:45] 设备连接成功: OnePlus8T
```

---

## 九、报告生成规范

### 9.1 HTML 报告组件

```python
# 添加结果图表
report.add_chart("precision", precision_data)

# 添加结果表格
report.add_table("检测结果", results_data)

# 生成HTML报告
report.generate("report.html")
```

### 9.2 性能指标

```python
# 计算帧率
fps = 1.0 / (time.time() - start_time)

# 计算内存使用
memory_usage = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
```

---

## 十、Git 提交规范

### 10.1 Commit 信息模板

提交代码时请遵循以下 commit 信息模板格式：

```
<type>(<scope>): <简要描述问题和修复>

修复内容：
1. <修改模块/文件1>:
   - <具体修改内容>
   - <具体修改内容>

2. <修改模块/文件2>:
   - <具体修改内容>
   - <具体修改内容>

3. <修改的关键点>:
   - <具体修改内容>
   - <具体修改内容>

修复问题: "<错误信息或问题描述>"

测试: <描述如何验证修复结果>
日期: <提交日期，格式：Month DD, YYYY>
```

其中：

- `<type>`: 提交类型，如 fix、feat、docs 等
- `<scope>`: 影响范围，如 templates、devices、scripts 等
- 示例：`feat(devices): 增强设备连接与管理功能`

### 10.2 Type 类型说明

- `fix`: 修复 bug
- `feat`: 新功能
- `docs`: 文档更新
- `style`: 代码风格或格式修改
- `refactor`: 代码重构（不涉及功能变更）
- `perf`: 性能优化
- `test`: 添加或修改测试
- `build`: 构建系统或外部依赖项修改
- `ci`: CI 配置或脚本修改

### 10.3 提交示例

```
fix: resolve script path duplication issue in debugging functions

修复内容：
1. 前端脚本路径处理(scripts.html):
   - 移除全局设置中脚本路径的'apps/scripts/'前缀，防止路径重复
   - 更新executeCommand函数，仅使用脚本文件名而非完整路径
   - 修复路径处理逻辑，从任何路径中只提取基本文件名

2. 后端路径处理(views.py):
   - 改进debug_script函数中的脚本路径解析
   - 当脚本找不到时添加更好的错误信息
   - 修复路径处理，防止目录重复，例如"apps/scripts/apps/scripts/"

3. 路径格式修复:
   - 更新loadSettings函数
   - 更新saveSettings函数
   - 更新executeCommand函数

修复问题: "can't open file '...apps\scripts\apps\scripts\record_script.py'"

测试: 验证了脚本调试、录制和回放按钮的功能正常
日期: May 21, 2025
```
