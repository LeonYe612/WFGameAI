# WFGame AI 自动化测试框架代码规范

## ai-server 服务启动命令
- `python .\start_wfgame_ai.py`

## 项目统一使用请求方法
- 全部使用 POST

## python 目录
- `F:\QA\Software\anaconda3\envs\py39_yolov10\python.exe`

## 注意事项
- 训练模型时仅需支持 Windows（CUDA），不用支持 Mac（MPS）系统（模型训练完全在 Windows 上进行）。
- 分析后直接在原文件内改动代码。
- 添加详细的注释。

## 常用路径
- airtest 报告生成需要静态资源（CSS/JS 等静态资源目录）是在 airtest 包的 report/ 目录下。

## 前端页面文件资源存放目录
- WFGameAI\wfgame-ai-server\staticfiles

## 前端web页面文件目录
- WFGameAI\wfgame-ai-server\staticfiles\pages

## 代码修改规范

### 修改方式
- 直接在原文件上修改。

### 路径规则
- 全局禁止出现/使用绝对路径。

## YOLO 训练规范

### Windows 配置：
- Intel(R) Core(TM) i7-14700   2.10 GHz
- 显示卡 NVIDIA GeForce RTX 4090
- RAM 32.0 GB
- 64 位操作系统, 基于 x64 的处理器

### Mac 配置：
- Apple M2 Pro
- RAM 16GB

### 修复规则
- 禁止为修复问题创建新的文件或函数。禁止增加或使用 cleanup_unused_files！
- 所有修复必须直接在原始文件中进行。
- 必须在文件内添加注释说明修改的内容和目的。
- 讲清楚原因后直接生成或修复代码。

### 代码提交规范
- 提交前必须验证修复是否解决了问题。
- 提交后必须验证是否有低级的缩进错误。
- 每次修改必须提供完整的测试方法和预期结果。
- 禁止提交未经测试的代码。

## Python 代码规范

### 导入规则
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

### 命名规范

#### 变量命名
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

#### 函数命名
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

### 数据库表命名规范

#### 表名前缀规则
- 所有新建的 AI 项目相关表必须使用 `ai_` 前缀
- 保持与现有系统表（`tb_` 前缀）区分
- 表名使用小写下划线命名法

#### 示例
```python
class YourModel(models.Model):
    # ... fields here ...

    class Meta:
        db_table = 'ai_your_table_name'  # 必须使用 ai_ 前缀
```

#### 现有示例
- `ai_device` - 设备表
- `ai_devicelog` - 设备日志表
- `ai_script` - 脚本表
- `ai_script_execution` - 脚本执行记录表

#### 命名规则详解
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
```

#### 类命名
```python
# 类名使用驼峰
class DeviceManager:
    pass

class UIDetector:
    pass
```

### 格式规范

1. **缩进**
   - 使用 4 个空格进行缩进
   - 不使用制表符
2. **行长度**
   - 最大行长度为 120 字符
   - 超长行使用括号换行
3. **空行**
   - 类定义之间空两行
   - 方法定义之间空一行
   - 相关代码块之间空一行
4. **注释**
```python
# 单行注释使用 # 加空格
# 这是一个单行注释

"""
多行注释使用三引号
第一行空行
具体描述从第二行开始
"""
```

### 文档字符串

#### 函数文档
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

#### 类文档
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

### 异常处理
```python
try:
    process_device()
except DeviceError as e:
    logger.error(f"设备处理失败: {e}")
    raise
finally:
    cleanup_resources()
```

### 类型注解
```python
from typing import List, Dict, Optional

def process_results(
    results: List[Dict[str, float]],
    threshold: Optional[float] = None
) -> bool:
    pass
```

## 项目结构规范

### 文件命名
- 模块文件名：小写下划线 (例如: `device_manager.py`)
- 测试文件名：以 `test_` 开头 (例如: `test_device_manager.py`)
- 配置文件名：小写 (例如: `config.ini`)

### 目录结构
```
wfgame-ai-server/
├── apps/               # Django 应用包
│   ├── scripts/        # 脚本管理模块
│   └── devices/        # 设备管理模块
├── config.ini          # 配置文件
├── start_wfgame_ai.py  # 启动脚本
└── manage.py           # Django 管理脚本
```

## 配置管理规范

### 环境变量
- 使用 `config.ini` 文件而非环境变量
- 所有路径都必须使用相对路径，禁止硬编码绝对路径

### 配置文件
```ini
[paths]
# 脚本目录
scripts_dir = ${server_dir}/apps/scripts

# 测试用例目录
testcase_dir = ${server_dir}/apps/scripts/testcase

# 报告目录
reports_dir = ${server_dir}/outputs/WFGameAI-reports
```

## 日志规范

### 日志级别
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

### 日志格式
```
[2025-05-15 14:30:45] [INFO] [device_manager.py:45] 设备连接成功: OnePlus8T
```

## UI检测与测试规范

### 截图命名
```
screenshot_20250515_143045.png  # 截图_年月日_时分秒
```

### 测试用例格式
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

### 图像处理
```python
# 灰度转换
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

# 应用阈值
_, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

# 查找轮廓
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```

## 模型训练规范

### 数据准备
```python
# 数据集路径设置
train_path = os.path.join("datasets", "train")
valid_path = os.path.join("datasets", "valid")

# 数据加载与预处理
dataset = YOLO.load_dataset(train_path, augment=True)
```

### 训练配置
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

### 模型评估
```python
# 验证
results = model.validate(valid_path)
precision = results["precision"]
recall = results["recall"]
mAP = results["mAP_0.5"]
```

## 报告生成规范

### HTML报告组件
```python
# 添加结果图表
report.add_chart("precision", precision_data)

# 添加结果表格
report.add_table("检测结果", results_data)

# 生成HTML报告
report.generate("report.html")
```

### 性能指标
```python
# 计算帧率
fps = 1.0 / (time.time() - start_time)

# 计算内存使用
memory_usage = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
```

## Git 提交规范

### Commit 信息模板
提交代码时请遵循以下commit信息模板格式：

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

### Type 类型说明
- `fix`: 修复bug
- `feat`: 新功能
- `docs`: 文档更新
- `style`: 代码风格或格式修改
- `refactor`: 代码重构（不涉及功能变更）
- `perf`: 性能优化
- `test`: 添加或修改测试
- `build`: 构建系统或外部依赖项修改
- `ci`: CI配置或脚本修改

### 提交示例
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
