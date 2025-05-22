# WFGame AI 自动化测试框架

## 项目概述

WFGame AI 自动化测试框架是一个基于YOLO11m计算机视觉的游戏UI自动化测试解决方案。该框架通过深度学习模型实现了跨平台、跨分辨率的UI元素精准识别，彻底替代传统图像对比方法，显著提高了自动化测试的稳定性和可靠性，并支持多设备并行测试（1-100台规模）。

### 核心特性

- **AI驱动的UI识别**：使用YOLO11m自定义模型进行实时UI元素检测，替代传统图像对比方法
- **B/S架构平台**：基于honeydou平台，提供完整的Web界面进行脚本管理、任务调度、设备管理等
- **多设备并行测试**：支持大规模（1-100台）设备同时执行测试用例
- **数据驱动测试**：支持数据与脚本分离，通过Excel/数据库导入测试数据
- **完整的测试流程**：包含录制、回放、报告生成等全流程功能
- **智能报告系统**：生成详细的HTML测试报告，支持多设备汇总
- **三种测试模式**：
    - 固定场景模式：预设流程自动化遍历
    - UI深度遍历模式：智能探索未知界面
    - 路径全量遍历模式：自动验证所有可能路径
- **平台兼容**：支持Windows（CUDA）。模型训练完全在Windows上进行，Mac（MPS）系统仅用于执行测试。

## 环境要求

- Python 3.9+
- PyTorch（Windows: CUDA支持，Mac: MPS支持）
- Ultralytics YOLO
- OpenCV
- Airtest
- Django 3.2+（Web平台）
- MySQL 5.7+（数据存储）
- Redis 7.2+（缓存）
- ADB工具（设备连接）

## 开发规范

- [代码规范](docs/WFGameAI-Coding-Standards.md): 项目代码风格和结构规范
- [Git提交规范](git_commit_guide.md): Git提交信息模板和规范
- [API开发规范](docs/WFGameAI-API-Dev-Standards.md): API设计和开发规范

## 快速开始

1. **环境配置**
```bash
# 克隆仓库
git clone https://github.com/username/WFGameAI.git
cd WFGameAI

# 安装依赖
pip install -r requirements.txt
```

2. **工作目录信息**
```bash
# 调试、录制、回放的脚本存放目录
WFGameAI/wfgame-ai-server/scripts

# testcase 保存目录
WFGameAI/wfgame-ai-server/testcase
```

3. **wfgame-ai-server 启动命令**
```bash
python start_wfgame_ai.py
```

4. **模型训练**
```bash
python train_model.py
```

5. **调试模式**
```bash
# 只在PC屏幕展示识别结果
python wfgame-ai-server/scripts/record_script.py
```

6. **录制模式**
```bash
# 情况1：基础录制（仅记录匹配按钮）
python wfgame-ai-server/scripts/record_script.py --record

# 情况2：增强录制（记录所有点击，未识别到的目标记录为unknown）
python wfgame-ai-server/scripts/record_script.py --record-no-match
```

7. **回放模式**
```bash
# 参数说明
# --show-screens： 展示设备框，实时显示设备屏幕
# --script：指定脚本。如果为多个，则分别在脚本前添加
# --loop-count 1：该脚本循环次数1次
# --max-duration 30：该脚本执行时间30秒

# 单脚本回放
python wfgame-ai-server/scripts/replay_script.py --show-screens --script testcase/scene1_nologin_steps_2025-04-07.json --loop-count 1

# 多脚本顺序回放（此命令下，第一个脚本执行1次结束后再继续执行第2个脚本30秒）
python wfgame-ai-server/scripts/replay_script.py --show-screens --script testcase/scene1_nologin_steps_2025-04-07.json --loop-count 1 --script testcase/scene2_guide_steps_2025-04-07.json --max-duration 30
python wfgame-ai-server/scripts/replay_script.py --show-screens --script testcase/scene1_login_steps_2025-04-07.json --loop-count 1 --script testcase/scene2_guide_steps_2025-04-07.json --max-duration 30
```

## Web平台（基于honeydou）

WFGame AI自动化测试框架基于honeydou自动化测试平台构建，采用Django+Vue的B/S架构，提供完整的Web界面进行测试管理。详细信息请参考[honeydou平台文档](docs/README_honeydou.md)。

主要功能包括：
- 脚本管理与版本控制
- 测试任务调度与执行
- 设备管理与状态监控
- 报告生成与查看
- 数据驱动测试配置

## 实施路线图

项目分为四个主要阶段实施：

1. **阶段一：构建AI核心引擎与平台基础** - **70%**
   - ✅ 开发AI视觉引擎：利用YOLO11m替代传统图像识别
   - ✅ 实现基本的多设备管理（adbutils）
   - ❌ 构建完整B/S架构平台：集成脚本管理、任务调度等功能
   - ✅ 确保固定场景脚本稳定回放

2. **阶段二：引入数据驱动与赋能团队** - **30%**
   - ✅ 实现基本的资源管理和清理功能
   - ❌ 构建数据驱动框架：实现数据与脚本分离
   - ❌ 提升平台易用性：开发低代码界面
   - ❌ 培训功能测试团队（22人）

3. **阶段三：集成智能优化与线上监控** - **0%**
   - ❌ 实施智能测试选择：基于代码变更和历史数据筛选用例
   - ❌ 部署线上自动化监控：对生产/预发环境进行监控
   - ❌ 探索AI异常检测

4. **阶段四：持续探索AI深度应用** - **0%**
   - ❌ 研究AI辅助生成：探索生成测试数据/用例
   - ❌ 深化路径遍历应用：UI深度遍历和场景路径全遍历
   - ❌ 开发AI辅助探索测试工具

当前实施进度请参考[实施进度跟踪文档](docs/WFGameAI_实施进度跟踪.md)。

## 测试报告系统

- **分层结构**：设备级别报告 + 汇总报告
- **详细记录**：包含每步操作的截图和结果
- **资源完整**：确保所有静态资源可访问
- **交互友好**：支持报告间快速导航

## 工作流程

1. **录制阶段**
   - 连接测试设备
   - 启动录制模式
   - 执行测试操作
   - 保存录制脚本

2. **回放阶段**
   - 加载测试脚本
   - 执行自动化操作
   - 实时截图记录
   - 生成测试报告

3. **分析阶段**
   - 查看测试结果
   - 分析失败原因
   - 优化测试用例

## 最佳实践

1. **录制建议**
   - 使用稳定的测试环境
   - 保持操作节奏均匀
   - 避免过快的连续操作
   - 及时添加操作备注

2. **回放优化**
   - 合理设置循环次数
   - 添加适当的等待时间
   - 定期清理日志文件
   - 监控设备性能

3. **报告管理**
   - 定期归档测试报告
   - 保持报告目录结构清晰
   - 及时清理过期报告
   - 备份重要测试数据

## 常见问题

1. **设备连接问题**
   - 检查ADB连接状态
   - 确认USB调试是否启用
   - 验证设备权限设置

2. **识别准确性**
   - 优化模型训练数据
   - 调整检测阈值
   - 更新按钮样本集

3. **报告生成失败**
   - 检查日志完整性
   - 验证静态资源
   - 确认目录权限

## 项目结构（详细分层说明，2025年5月最新）

```
WFGameAI/
├── config.ini                  # 【全局路径配置，所有后端路径引用的唯一入口】
├── datasets/                  # 数据集目录（config.ini: datasets_dir）
│   ├── preprocessed/          # 预处理后的数据
│   └── templates/             # 报告模板
├── docs/                      # 文档目录
│   ├── README_honeydou.md     # honeydou平台文档
│   └── WFGameAI_实施进度跟踪.md # 实施进度跟踪文档
├── scripts/                   # AI训练/工具脚本目录（如 generate_annotations.py 等，config.ini 不直接管理）
├── templates/                 # 报告/页面模板目录
├── wfgame-ai-server/          # 服务器端主目录（config.ini: server_dir）
│   ├── apps/                  # 各业务App目录（如 devices、scripts、reports 等）
│   │   ├── scripts/           # 脚本管理App（config.ini: scripts_dir）
│   │   │   ├── views.py       # 脚本API主视图（路径引用必须全部依赖config.ini）
│   │   │   ├── record_script.py
│   │   │   └── replay_script.py
│   │   ├── devices/           # 设备管理App
│   │   └── ...                # 其他App
│   ├── testcase/              # 测试用例目录（config.ini: testcase_dir）
│   ├── outputs/               # 输出目录（如报告，config.ini 的 reports_dir）
│   │   └── WFGameAI-reports/  # 测试报告主目录（config.ini: reports_dir）
│   │       └── ui_reports/    # UI报告目录（config.ini: ui_reports_dir）
│   └── wfgame_ai_server/      # Django主项目目录（主urls.py/settings.py/wsgi.py等）
├── wfgame-ai-web/             # 前端Web界面（Vue3）
├── requirements.txt           # 依赖列表
├── start_wfgame_ai.py         # 启动脚本（后端）
└── train_model.py             # 模型训练脚本
```

### 结构说明
- **所有后端目录引用（如脚本、用例、报告等）必须严格通过 config.ini 统一管理和获取，禁止硬编码和静态拼接。**
- **config.ini 是全局唯一的路径配置入口，所有API和后端逻辑均以其为准。**
- **wfgame-ai-server/apps/scripts/** 目录下的 record_script.py、replay_script.py 等脚本，必须通过 config.ini 的 scripts_dir 路径引用。**
- **wfgame-ai-server/testcase/**、**outputs/WFGameAI-reports/**、**outputs/WFGameAI-reports/ui_reports/** 等目录，均通过 config.ini 的 testcase_dir、reports_dir、ui_reports_dir 管理。**
- **如需新增目录或调整结构，必须先修改 config.ini 并同步后端所有路径引用。**

## 数据库配置

```ini
[DBMysql] # 数据库配置信息
HOST=127.0.0.1
USERNAME=root
PASSWD=qa123456
DBNAME=gogotest_data
```

## 目录结构与路径说明（2025年5月最新）

- 项目根目录：WFGameAI
- 服务器主目录：WFGameAI/wfgame-ai-server
- 脚本目录：WFGameAI/wfgame-ai-server/apps/scripts
- 测试用例目录：WFGameAI/wfgame-ai-server/testcase
- 报告目录：WFGameAI/outputs/WFGameAI-reports
- UI报告目录：WFGameAI/outputs/WFGameAI-reports/ui_reports

所有后端代码和API均已静态化引用上述目录，不再依赖config.ini或动态推导。
