# WFGame AI 自动化测试框架

## 项目概述

WFGame AI 自动化测试框架是一个基于**计算机视觉 AI 技术**的移动端自动化测试解决方案。该框架通过 YOLO11m 深度学习模型实现了跨平台、跨分辨率的 UI 元素精准识别，彻底替代传统图像对比方法，显著提高了自动化测试的稳定性和可靠性，并支持多设备并行测试。

### 🎯 核心特性

- **🤖 AI 驱动的 UI 识别**：使用 YOLO11m 自定义模型进行实时 UI 元素检测，替代传统图像对比方法
- **🌐 B/S 架构平台**：基于 Django+Vue3 的现代化 Web 界面，提供完整的测试管理平台
- **📱 多设备并行测试**：支持大规模（1-100 台）Android 设备同时执行测试用例，具备智能混合执行策略
- **📊 数据驱动测试**：支持数据与脚本分离，通过 Excel/数据库导入测试数据
- **🔄 完整的测试流程**：包含连接设备、录制脚本、调试设备、脚本管理、回放执行、查看报告等全流程功能
- **📋 智能报告系统**：生成详细的 HTML 测试报告，支持多设备汇总和历史趋势分析
- **👆 触摸手势支持**：
  - **点击操作**：精准的 UI 元素点击识别和执行
  - **滑动手势**：支持上下左右滑动，可自定义起止坐标、距离和持续时间
  - **多点触控**：支持复杂的手势操作（规划中）
- **🎮 双模式测试执行**：
  - **Step模式**：线性顺序执行预设流程
  - **Priority模式**：动态循环检测，智能应对UI变化

## 🛠️ 环境要求

### 系统环境

- **操作系统**：Windows 10/11, macOS 12+, Linux Ubuntu 18.04+
- **Python**：3.9+ (推荐 3.9-3.11)
- **Node.js**：16+ (前端开发，可选)
- **ADB 工具**：Android 调试桥，用于设备连接

### 核心依赖

- **PyTorch**：深度学习框架（Windows: CUDA 支持，Mac: MPS 支持）
- **Ultralytics YOLO**：目标检测模型
- **OpenCV**：图像处理库
- **Airtest**：移动端自动化测试框架
- **Django 4.2+**：Web 后端框架
- **Vue 3**：前端界面框架
- **Element Plus**：UI 组件库

### 数据库与缓存

- **MySQL 5.7+**：主数据库（测试数据、脚本记录等）
  - 所有新建表必须使用 `ai_` 前缀（[查看详细命名规范](docs/WFGameAI-Coding-Standards.md#数据库表命名规范)）
- **Redis 7.2+**：缓存系统（可选）

## 🚀 快速开始

### 1. 环境配置

```bash
# 克隆仓库
git clone https://github.com/username/WFGameAI.git
cd WFGameAI

# 安装Python依赖
pip install -r requirements.txt

# 配置数据库连接信息
# 编辑 config.ini 文件，设置数据库连接参数
```

### 2. 数据库初始化

```bash
# 进入服务器目录
cd wfgame-ai-server

# 执行数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建超级管理员账户
python manage.py createsuperuser
```

### 3. 启动系统

```bash
# 启动后端服务
python start_wfgame_ai.py

# 启动前端开发服务器（可选）
cd wfgame-ai-web
npm install
npm run serve
```

### 4. 设备连接

```bash
# 确保Android设备已开启USB调试
# 连接设备并验证ADB连接
adb devices

# 如使用无线连接
adb connect 192.168.1.100:5555
```

## 📖 使用指南

### 核心功能目录

```bash
# 核心脚本目录（录制、回放、调试）
WFGameAI/wfgame-ai-server/apps/scripts/
├── record_script.py          # 录制脚本（支持点击+滑动手势）
├── replay_script.py          # 回放脚本（支持点击+滑动手势）
├── views.py                  # 脚本管理API
├── model_loader.py           # AI模型加载适配器
├── app_lifecycle_manager.py  # 应用生命周期管理
├── testcase/                 # 测试用例保存目录
├── datasets/                 # 脚本相关数据集
└── app_templates/            # 脚本模板

# Web界面访问
http://localhost:8000         # 主管理界面
http://localhost:8080         # 前端开发服务器（可选）
```

### 录制测试脚本

#### 1. 调试模式（仅展示识别结果）

```bash
# 连接设备并在PC屏幕展示AI识别结果，不执行任何操作
python wfgame-ai-server/apps/scripts/record_script.py
```

#### 2. 基础录制模式（仅记录匹配按钮）

```bash
# 录制用户点击的已识别UI元素
python wfgame-ai-server/apps/scripts/record_script.py --record
```

#### 3. 增强录制模式（记录所有点击和滑动）

```bash
# 记录所有操作：已识别元素、未识别点击、滑动手势
python wfgame-ai-server/apps/scripts/record_script.py --record-no-match
```

#### 4. 滑动操作录制

录制模式会自动检测鼠标拖拽操作：

- **最小拖拽距离**：10 像素以上才识别为滑动
- **自动计算持续时间**：根据实际拖拽时间自动设置
- **坐标自动转换**：显示坐标自动转换为设备实际坐标
- **多设备同步**：支持一机多控模式下的滑动同步

### 回放测试脚本

#### 1. 单脚本回放

```bash
# 基础回放
python wfgame-ai-server/apps/scripts/replay_script.py \
  --script testcase/scene1_nologin_steps_2025-05-29.json

# 带屏幕显示的回放
python wfgame-ai-server/apps/scripts/replay_script.py \
  --show-screens \
  --script testcase/scene1_nologin_steps_2025-05-29.json \
  --loop-count 1
```

#### 2. 多脚本顺序回放

```bash
# 按顺序执行多个脚本
python wfgame-ai-server/apps/scripts/replay_script.py \
  --show-screens \
  --script testcase/scene1_nologin_steps_2025-05-29.json --loop-count 1 \
  --script testcase/scene2_guide_steps_2025-05-29.json --max-duration 30
```

#### 3. 滑动操作测试

```bash
# 测试滑动功能（使用提供的测试文件）
python wfgame-ai-server/apps/scripts/replay_script.py \
  --show-screens \
  --script test_swipe.json

# 执行包含滑动的完整测试流程
python wfgame-ai-server/apps/scripts/replay_script.py \
  --show-screens \
  --script testcase/login_with_swipe_2025-05-29.json
```

### 滑动操作详细说明

#### JSON 格式示例

```json
{
  "steps": [
    {
      "step": 1,
      "action": "swipe",
      "start_x": 500,
      "start_y": 800,
      "end_x": 500,
      "end_y": 400,
      "duration": 500,
      "timestamp": "2025-05-29 12:00:00.000000",
      "remark": "向上滑动"
    }
  ]
}
```

#### 支持的滑动类型

- **垂直滑动**：上滑、下滑
- **水平滑动**：左滑、右滑
- **对角滑动**：任意方向的滑动
- **自定义持续时间**：100ms-5000ms 范围内

### 参数说明

- `--show-screens`：显示设备屏幕窗口，实时查看测试过程
- `--script`：指定要执行的测试脚本文件路径
- `--loop-count N`：脚本循环执行次数（N 次）
- `--max-duration N`：脚本最大执行时间（N 秒）
- `--record`：启用录制模式（仅记录已识别元素）
- `--record-no-match`：启用增强录制模式（记录所有操作）

## 🌐 Web 管理平台

WFGame AI 提供完整的 Web 管理界面，基于现代化的技术栈构建：

### 技术架构

- **后端**：Django 4.2 + REST API
- **前端**：Vue 3 + Element Plus + Vite
- **数据库**：MySQL / SQLite
- **AI 引擎**：YOLO11m + PyTorch

### 主要功能模块

#### 🏠 控制台（Dashboard）

- 系统概览和实时监控
- 设备连接状态统计
- 最近测试任务状态
- 报告生成统计图表

#### 📱 设备管理

- 设备连接状态监控
- 设备信息查看（型号、分辨率、Android 版本等）
- 一键连接/断开设备
- 设备健康状态检查

#### 📝 脚本管理

- **脚本列表**：查看所有测试脚本，支持分类筛选
- **脚本详情**：查看脚本内容、执行历史、编辑脚本
- **脚本执行**：直接从 Web 界面启动脚本执行
- **脚本分类**：支持按业务场景分类管理
- **版本控制**：脚本修改历史记录
- **滑动支持**：完整的滑动操作录制、编辑和回放

#### 📋 任务管理

- 创建和调度测试任务
- 批量执行多个脚本
- 任务执行进度监控
- 任务执行历史查询

#### 📊 测试报告

- **分层报告结构**：设备级别报告 + 汇总报告
- **详细记录**：每步操作的截图和结果
- **交互友好**：报告间快速导航
- **历史趋势**：测试结果统计分析
- **资源完整**：确保所有静态资源可访问
- **智能生成**：脚本执行完成后自动生成汇总报告
- **实时监控**：支持实时报告生成状态查看

#### ⚙️ 系统设置

- 全局配置管理
- 路径配置设置
- AI 模型参数调优
- 日志级别配置

### Web 界面访问

```
主界面：http://localhost:8000
API文档：http://localhost:8000/api/docs/
管理后台：http://localhost:8000/admin/
```

## 🛠️ 完整功能列表

### 核心功能

✅ **设备连接管理**

- 支持 USB 和无线连接
- 多设备并行操作
- 设备状态实时监控
- 自动重连机制

✅ **AI 视觉识别**

- YOLO11m 深度学习模型
- 实时 UI 元素检测
- 跨分辨率适配
- 自定义模型训练支持

✅ **脚本录制功能**

- 点击操作录制
- 滑动手势录制（上下左右任意方向）
- 坐标自动转换
- 操作时间戳记录
- 多设备同步录制

✅ **脚本回放功能**

- JSON 格式脚本执行
- 滑动操作回放
- 循环执行支持
- 实时屏幕显示
- 执行进度监控

✅ **测试报告系统**

- HTML 格式详细报告
- 操作截图记录
- 多设备汇总报告
- 历史趋势分析
- 报告静态资源管理
- 智能报告生成与监控
- 基于执行时间的设备分组

✅ **Web 管理界面**

- 现代化 B/S 架构
- RESTful API 设计
- 设备管理界面
- 脚本管理界面
- 报告查看界面

### 滑动功能特性

✅ **录制阶段**

- 鼠标拖拽自动检测
- 最小距离阈值（10 像素）
- 自动计算持续时间
- 坐标精确转换
- 多设备同步支持

✅ **回放阶段**

- ADB 滑动命令执行
- 自定义持续时间（100ms-5000ms）
- 坐标边界检查
- 操作日志记录
- Airtest 报告兼容

✅ **支持的滑动类型**

- 垂直滑动（上滑、下滑）
- 水平滑动（左滑、右滑）
- 对角滑动（任意方向）
- 自定义起止坐标
- 可调节滑动速度

## 🎯 实施路线图

项目按照四个主要阶段实施，目前已完成所有核心功能：

### 阶段一：构建 AI 核心引擎与平台基础 - **✅ 100% 完成**

- ✅ **AI 视觉引擎**：基于 YOLO11m 的 UI 元素识别，替代传统图像识别
- ✅ **多设备管理**：基于 adbutils 的设备连接和管理
- ✅ **B/S 架构平台**：Django+Vue3 完整 Web 界面
- ✅ **核心功能**：录制、回放、调试、报告生成
- ✅ **滑动手势**：支持滑动操作的录制和回放
- ✅ **脚本管理**：Web 界面的脚本管理和执行

### 阶段二：引入数据驱动与赋能团队 - **✅ 100% 完成**

- ✅ **资源管理**：完整的测试资源管理和清理功能
- ✅ **Web 界面**：现代化的管理界面和 API
- ✅ **报告系统**：多层级测试报告生成和查看
- ✅ **数据驱动框架**：支持数据与脚本分离
- ✅ **完整测试流程**：从录制到回放的完整自动化流程
- ✅ **多设备支持**：支持并行多设备测试

### 阶段三：集成智能优化与线上监控 - **📋 规划中**

- ❌ **智能测试选择**：基于代码变更和历史数据筛选用例
- ❌ **线上监控**：对生产/预发环境进行自动化监控
- ❌ **AI 异常检测**：智能识别测试异常和问题

### 阶段四：持续探索 AI 深度应用 - **🔮 研究中**

- ❌ **AI 辅助生成**：自动生成测试数据和用例
- ❌ **深度 UI 遍历**：智能探索未知界面路径
- ❌ **全路径遍历**：自动验证所有可能的用户路径
- ❌ **AI 探索工具**：智能化测试工具链

**当前实施进度详情**：[实施进度跟踪文档](docs/WFGameAI_实施进度跟踪.md)

## 🔬 测试与验证

### 滑动功能测试

项目提供了完整的滑动功能测试用例，用于验证滑动手势的录制和回放：

#### 测试文件：test_swipe.json

```json
{
  "steps": [
    {
      "step": 1,
      "action": "swipe",
      "start_x": 500,
      "start_y": 800,
      "end_x": 500,
      "end_y": 400,
      "duration": 500,
      "timestamp": "2025-05-29 12:00:00.000000",
      "remark": "向上滑动测试"
    },
    {
      "step": 2,
      "action": "swipe",
      "start_x": 200,
      "start_y": 600,
      "end_x": 800,
      "end_y": 600,
      "duration": 300,
      "timestamp": "2025-05-29 12:00:01.000000",
      "remark": "向右滑动测试"
    }
  ]
}
```

#### 执行滑动测试

```bash
# 运行滑动功能测试
python wfgame-ai-server/apps/scripts/replay_script.py \
  --show-screens \
  --script test_swipe.json
```

### 工作流程验证

#### 完整测试流程

1. **录制阶段**

   - 连接测试设备
   - 启动录制模式
   - 执行测试操作（点击+滑动）
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

### 测试报告系统

- **分层结构**：设备级别报告 + 汇总报告
- **详细记录**：包含每步操作的截图和结果
- **资源完整**：确保所有静态资源可访问
- **交互友好**：支持报告间快速导航
- **智能生成**：脚本执行完成后自动生成汇总报告
- **基于执行时间分组**：确保每次执行生成独立的汇总报告

#### 报告生成机制

1. **触发方式**

   - **实时生成**：每次脚本回放执行完成后立即生成对应的汇总报告
   - **Django 视图触发**：脚本执行完成后通过后台监控线程自动生成
   - **脚本主函数触发**：replay_script.py 主函数结束时作为备用方案

2. **报告类型与对应关系**

   - **设备级别报告**：每个设备在单次执行中的详细报告（log.html + 截图）
   - **汇总报告**：单次执行批次中所有设备的统一汇总（summary_report.html）
   - **一对一关系**：一次脚本执行 → 一个汇总报告 → 对应该批次的所有设备报告

3. **批次识别机制**

   - **当前执行设备列表**：报告生成基于当前正在执行的设备列表，而非历史扫描
   - **精确设备匹配**：replay_script.py 收集实际处理的设备名称，直接传递给报告生成函数
   - **时间戳一致性**：同一批次内所有设备的时间戳相近（秒级差异）
   - **批次隔离**：不同批次的执行完全独立，各自生成独立的汇总报告
   - **回退机制**：如设备列表获取失败，使用 5 分钟时间窗口检测同批次设备

4. **报告内容结构**

   - **批次统计概览**：当前执行的总设备数、成功设备数、成功率、执行时间
   - **设备详情表格**：该批次内每个设备的执行状态和结果
   - **导航链接**：链接到同批次设备的详细报告

5. **报告文件组织**

   ```
   reports/
   ├── summary_reports/
   │   ├── summary_report_2025-06-17-14-31-xx.html  # 14:31批次汇总
   │   ├── summary_report_2025-06-17-15-27-xx.html  # 15:27批次汇总
   │   └── latest_report.html                        # 最新批次快捷方式
   └── ui_run/WFGameAI.air/log/
       ├── OnePlus-KB2000_2025-06-17-14-31-21/      # 14:31批次设备1
       ├── HUAWEI-JAD-AL00_2025-06-17-14-31-25/     # 14:31批次设备2
       ├── OnePlus-KB2000_2025-06-17-15-27-48/      # 15:27批次设备1
       └── HUAWEI-JAD-AL00_2025-06-17-15-27-52/     # 15:27批次设备2
   ```

6. **编码安全保障**
   - 使用 UTF-8 编码处理所有文件操作
   - 特殊字符异常处理（errors='replace'）
   - Font Awesome 图标替代 Unicode emoji

## 📚 最佳实践

### 录制建议

1. **使用稳定的测试环境**

   - 保持设备网络连接稳定
   - 确保应用版本一致
   - 避免录制期间接收通知

2. **保持操作节奏均匀**

   - 避免过快的连续操作
   - 给界面充分的响应时间
   - 合理使用等待时间

3. **滑动操作建议**

   - 拖拽距离大于 10 像素才会被识别为滑动
   - 合理设置滑动持续时间（100ms-5000ms）
   - 考虑设备性能差异，适当延长等待时间

4. **及时添加操作备注**
   - 为每个操作步骤添加有意义的备注
   - 便于后续维护和理解

### 回放优化

1. **合理设置循环次数**

   - 根据测试需求设置适当的循环执行次数
   - 避免无限循环导致资源浪费

2. **添加适当的等待时间**

   - 在关键操作后添加等待时间
   - 确保界面完全加载后再进行下一步

3. **监控设备性能**
   - 定期清理日志文件
   - 监控设备内存和 CPU 使用情况
   - 及时处理设备过热问题

### 报告管理

1. **定期归档测试报告**

   - 按时间和项目分类保存报告
   - 保持报告目录结构清晰

2. **及时清理过期报告**

   - 设置报告保留周期
   - 自动清理过期的测试数据

3. **备份重要测试数据**
   - 定期备份关键测试脚本
   - 保存重要的测试报告

## 🔧 常见问题解决

### 设备连接问题

1. **检查 ADB 连接状态**

   ```bash
   adb devices
   adb kill-server
   adb start-server
   ```

2. **确认 USB 调试是否启用**

   - 在设备设置中启用开发者选项
   - 开启 USB 调试模式
   - 允许计算机调试权限

3. **验证设备权限设置**
   - 确保设备信任连接的计算机
   - 检查防火墙和安全软件设置

### AI 识别准确性问题

1. **优化模型训练数据**

   - 增加更多样本到训练集
   - 确保样本质量和多样性

2. **调整检测阈值**

   - 根据实际情况调整置信度阈值
   - 平衡准确率和召回率

3. **更新按钮样本集**
   - 定期更新 UI 元素样本
   - 适应界面变化和新功能

### 滑动操作问题

1. **滑动不被识别**

   - 确保拖拽距离超过 10 像素
   - 检查鼠标事件是否正常触发

2. **滑动坐标不准确**

   - 验证坐标转换逻辑
   - 检查设备分辨率设置

3. **滑动执行失败**
   - 确保设备支持 input swipe 命令
   - 检查 ADB 连接状态

### 报告生成失败

1. **检查日志完整性**

   - 确保所有操作都有对应的日志记录
   - 检查日志文件格式是否正确

2. **验证静态资源**

   - 确保所有截图文件存在
   - 检查静态资源路径设置

3. **确认目录权限**

   - 验证报告输出目录的写入权限
   - 检查磁盘空间是否充足

4. **编码问题处理**

   - 确保系统使用 UTF-8 编码
   - 检查特殊字符处理设置
   - 验证 Font Awesome 图标加载

5. **设备目录时间戳**
   - 检查设备目录的修改时间
   - 确认执行时间分组逻辑
   - 验证设备目录筛选机制

## 开发工具说明

### 提交信息生成工具

为了规范化 Git 提交信息并突出代码变更的业务价值，项目提供了提交信息自动生成工具：

```bash
# 运行提交信息生成器
python generate_commit_message.py
```

该工具会：

1. 分析当前暂存区的文件变更
2. 智能提取功能特性和业务价值
3. 检测大文件并提示可能的推送问题
4. 生成符合团队规范的、高质量的提交信息

生成的提交信息保存在`commit_message.txt`中，可以通过以下命令直接使用：

```bash
git commit -F commit_message.txt
```

### Git 大文件处理工具

如果您遇到 GitHub 的"pre-receive hook declined"错误，可以使用项目提供的大文件清理工具：

```bash
# 在Windows环境下运行
cleanup_large_files.bat
```

该工具会：

1. 扫描并检测仓库中的大文件
2. 智能生成.gitignore 规则以避免提交大文件
3. 帮助从暂存区移除大文件
4. 提供清理 Git 历史中大文件的方案

## 项目结构（详细分层说明，2025 年 7 月最新）

```
WFGameAI/
├── config.ini                    # 【全局路径配置，所有后端路径引用的唯一入口】
├── requirements.txt              # Python依赖列表
├── start_wfgame_ai.py           # 项目启动脚本（后端）
├── utils.py                      # 项目配置管理工具
├── test_swipe.json              # 滑动功能测试用例
├── yolo11m.pt / yolo11n.pt      # AI视觉识别模型文件
├── config_validator.py          # 配置文件验证工具
├── value_formatter.py           # 数据格式化工具
├── usb_connection_checker.py    # USB连接测试工具
├── update_device_db.py          # 设备数据库更新工具
├── device_preparation.bat       # 设备准备批处理脚本
├── generate_commit_message.py   # 提交信息生成工具
├── ai_capture_and_analyze_result/ # AI截图分析工具目录
│   └── ai_capture_and_analyze_real_screen.py # 实时屏幕分析工具
├── datasets/                    # 数据集目录（config.ini: datasets_dir）
│   ├── My First Project.v7i.yolov11/  # YOLO训练数据集
│   ├── preprocessed/            # 预处理后的数据
│   │   └── cache_gen/           # 缓存生成目录
│   └── templates/               # 报告模板
│       ├── report_tpl.html.useless
│       └── summary_template.html
├── docs/                        # 完整项目文档目录
│   ├── swipe_implementation.md  # 滑动功能实现文档
│   ├── WFGameAI_实施进度跟踪.md  # 实施进度跟踪文档
│   ├── WFGameAI回放系统双模式深度解析.md # 回放系统详细文档
│   ├── WFGameAI_报告生成系统详细文档_AI优化版.md # 报告系统文档
│   ├── WFGameAI_Action_使用手册.md # Action API使用手册
│   ├── AI 自动化测试框架实施路线图 -【详细】.md # 实施路线图
│   └── Web服务+本地轻量组件混合模式详细设计.md # 架构设计文档
├── external/                    # 外部集成组件
│   └── honeydou/                # honeydou平台集成
├── templates/                   # 全局报告/页面模板目录
│   └── summary_template.html
├── train_results/               # AI模型训练结果
│   └── train/
├── train_model/                 # AI模型训练工具
├── models/                      # 模型存储目录
├── diagnosis_detector.py        # 诊断检测器
├── detection_diagnosis_tool.py  # 检测诊断工具
├── universal_ui_dom_detector.py # 通用UI元素检测器
├── comprehensive_detection_check.py # 全面检测验证工具
├── implement_dataset_restructure.py # 数据集重构工具
├── aggressive_class_optimization.py # 类别优化工具
├── class_analysis.py            # 类别分析工具
├── optimize_classes.py          # 类别优化执行器
├── wfgame-ai-server/            # 服务器端主目录（config.ini: server_dir）
│   ├── manage.py                # Django管理脚本
│   ├── apps/                    # 各业务App目录
│   │   ├── scripts/             # 【核心】脚本管理App（config.ini: scripts_dir）
│   │   │   ├── record_script.py      # 录制脚本（支持点击+滑动）
│   │   │   ├── replay_script.py      # 回放脚本（支持点击+滑动）
│   │   │   ├── action_processor.py   # 操作处理器
│   │   │   ├── optimized_hybrid_executor.py # 智能混合执行器
│   │   │   ├── adaptive_threshold_manager.py # 自适应阈值管理器
│   │   │   ├── mysql_account_manager.py # 数据库账号管理器
│   │   │   ├── multi_device_replayer.py # 多设备并发回放器
│   │   │   ├── enhanced_device_preparation_manager.py # 增强设备准备管理器
│   │   │   ├── app_lifecycle_manager.py # 应用生命周期管理
│   │   │   ├── detection_manager.py # 检测管理器
│   │   │   ├── enhanced_input_handler.py # 增强输入处理器
│   │   │   ├── storage_manager.py   # 存储管理器
│   │   │   ├── views.py             # 脚本API主视图
│   │   │   ├── models.py            # 脚本数据模型
│   │   │   ├── urls.py              # URL路由配置
│   │   │   ├── serializers.py       # 序列化器
│   │   │   ├── testcase/            # 测试用例保存目录
│   │   │   ├── datasets/            # 脚本相关数据集
│   │   │   └── app_templates/       # 脚本模板
│   │   ├── devices/             # 设备管理App
│   │   ├── reports/             # 测试报告管理App
│   │   │   ├── views.py             # 报告API
│   │   │   ├── report_generator.py  # 报告生成器
│   │   │   ├── staticfiles/         # 报告静态资源
│   │   │   └── fix_static_*.py      # 静态资源修复工具
│   │   ├── tasks/               # 任务管理App
│   │   ├── users/               # 用户管理App
│   │   ├── data_source/         # 数据源管理App
│   │   ├── project_monitor/     # 项目监控App
│   │   └── logs/                # 日志管理App
│   │       └── app_lifecycle/   # 应用生命周期日志
│   ├── generate_summary_from_logs.py # 报告生成脚本
│   ├── create_integrated_reports.py  # 集成报告生成工具
│   ├── check_projects.py         # 项目检查工具
│   ├── staticfiles/             # 静态文件总目录
│   │   ├── pages/               # 前端页面文件
│   │   ├── reports/             # 测试报告静态资源
│   │   │   ├── ui_run/          # 设备级别报告目录
│   │   │   │   └── WFGameAI.air/
│   │   │   │       └── log/     # 设备报告目录
│   │   │   │           └── {device}_{timestamp}/ # 设备执行记录
│   │   │   │               ├── log.html    # 设备详细报告
│   │   │   │               ├── log.txt     # 设备日志文件
│   │   │   │               ├── *.jpg       # 操作截图
│   │   │   │               └── static/    # 静态资源
│   │   │   └── summary_reports/ # 汇总报告目录
│   │   │       ├── summary_report_{timestamp}.html # 时间戳报告
│   │   │       └── latest_report.html # 最新报告快捷方式
│   │   ├── admin/              # Django管理界面
│   │   └── rest_framework/     # REST API界面
│   ├── wfgame_ai_server/       # Django配置目录
│   │   ├── settings.py         # 项目配置
│   │   ├── urls.py             # 路由配置
│   │   └── middleware.py       # 中间件
│   ├── wfgame_ai_server_main/  # Django主项目目录
│   │   ├── settings.py         # 项目配置
│   │   ├── urls.py             # 路由配置
│   │   ├── wsgi.py             # WSGI入口
│   │   ├── asgi.py             # ASGI入口
│   │   └── celery.py           # Celery配置
│   └── logs/                   # 服务器日志目录
├── wfgame-ai-web/             # 前端Web界面（Vue3+Element Plus）
│   ├── package.json            # 前端依赖配置
│   ├── vite.config.js          # Vite构建配置
│   ├── src/                    # Vue源码目录
│   │   ├── api/                # API接口
│   │   ├── assets/             # 静态资源
│   │   ├── components/         # 组件
│   │   ├── router/             # 路由
│   │   ├── stores/             # 状态管理
│   │   ├── utils/              # 工具函数
│   │   └── views/              # 视图
│   ├── pages/                  # 页面组件
│   ├── css/                    # 样式文件
│   ├── js/                     # JavaScript文件
│   └── lib/                    # 前端库文件
├── dependencies/               # 依赖目录
│   └── apks/                   # APK文件
└── git_hooks/                 # Git钩子脚本
```

### 结构说明

- **所有后端目录引用（如脚本、用例、报告等）必须严格通过 config.ini 统一管理和获取，禁止硬编码和静态拼接。**
- **config.ini 是全局唯一的路径配置入口，所有 API 和后端逻辑均以其为准。**
- **核心逻辑与功能组件说明**:
  - **action_processor.py**: 操作处理器，负责执行各类动作（点击、滑动、等待等）
  - **optimized_hybrid_executor.py**: 智能混合执行器，根据设备数量和系统资源智能选择执行策略
  - **adaptive_threshold_manager.py**: 自适应阈值管理，根据执行结果动态优化检测阈值
  - **mysql_account_manager.py**: 数据库账号管理，处理多设备并行执行时的账号分配
  - **enhanced_device_preparation_manager.py**: 设备准备管理器，处理设备连接、预处理等
- **如需新增目录或调整结构，必须先修改 config.ini 并同步后端所有路径引用。**

### 核心文档说明

- **滑动功能实现文档**: [滑动实现文档](docs/swipe_implementation.md)
- **回放系统双模式文档**: [回放系统双模式深度解析](docs/WFGameAI回放系统双模式深度解析.md)
- **报告系统文档**: [报告生成系统详细文档](docs/WFGameAI_报告生成系统详细文档_AI优化版.md)
- **Action API使用手册**: [Action使用手册](docs/WFGameAI_Action_使用手册.md)
- **实施进度跟踪**: [实施进度跟踪文档](docs/WFGameAI_实施进度跟踪.md)

## 数据库配置

```ini
[DBMysql] # 数据库配置信息
HOST=127.0.0.1
USERNAME=root
PASSWD=qa123456
DBNAME=gogotest_data
```

## 🎉 项目特色

WFGame AI 自动化测试框架的独特优势：

1. **AI 驱动的智能识别**：摆脱传统图像匹配的局限，实现真正的智能 UI 识别
2. **完整的 B/S 架构**：现代化 Web 管理界面，支持团队协作和远程管理
3. **多设备并行测试**：大规模设备测试能力，提升测试效率
4. **手势操作支持**：完整的点击和滑动手势支持，覆盖更多测试场景
5. **详细测试报告**：分层级报告结构，支持历史趋势分析
6. **开箱即用**：完整的开发环境和部署方案，快速上手

---

**项目地址**：https://github.com/username/WFGameAI
**文档地址**：[项目文档](docs/)
**技术支持**：请提交 Issue 或联系开发团队

# 录制功能实现指南--6 月后继续研发-“增强录制”部分

## 功能概述

录制功能允许用户通过直观的操作方式创建自动化测试脚本。系统捕获用户在设备上的操作（点击、滑动等），并自动生成对应的 JSON 脚本，该脚本可供回放引擎直接执行。录制模式支持基础录制（仅记录匹配按钮）和增强录制（记录所有点击和滑动）两种方式。

## 详细功能描述

### UI 展示

1. **录制控制面板**

   - 显示在 Web 界面的脚本管理页面中
   - 包含"开始录制"按钮（带有摄像机图标）
   - 录制配置区域，包括:
     - 设备选择下拉框
     - 录制模式选择（基础/增强）
     - 脚本名称输入框
     - 脚本描述输入框

2. **录制状态指示**
   - 录制开始后显示"录制中"状态
   - 实时显示录制的步骤数量
   - 显示录制已持续时间

### 交互流程

1. **开始录制**

   - 用户点击"开始录制"按钮
   - 弹出录制设置对话框
   - 用户填写必要信息（设备、脚本名称等）
   - 点击确认开始录制

2. **录制过程**

   - 系统启动后台录制进程
   - 用户在选定设备上进行操作
   - 系统捕获并记录这些操作
   - 用户可随时通过快捷键（Ctrl+C）或关闭命令窗口停止录制

3. **录制完成**
   - 系统自动保存生成的 JSON 脚本
   - 在 Web 界面上显示新创建的脚本
   - 可选择直接编辑或执行该脚本

### 逻辑功能

1. **录制模式识别**

   - 基础录制模式（`--record`）：仅记录已识别的 UI 元素点击
   - 增强录制模式（`--record-no-match`）：记录所有操作，包括未识别元素的点击

2. **操作捕获与转换**

   - **点击操作处理**:

     - 使用 YOLO 模型识别屏幕上的 UI 元素
     - 记录用户点击的元素信息，包括 class、位置坐标
     - 根据不同模式决定是否记录未匹配的点击

   - **滑动操作处理**:
     - 记录鼠标拖拽的起始和结束坐标
     - 转换为设备实际坐标
     - 生成对应的滑动步骤 JSON 结构

3. **JSON 生成逻辑**

   - 创建标准格式的步骤结构，包含:
     - `step`: 步骤序号
     - `class`: 操作元素的类名
     - `action`: 操作类型（click、swipe 等）
     - `x`, `y`: 操作坐标
     - 对于滑动还包含`x2`, `y2`结束坐标

4. **等待时间控制**

   - 实现`max_duration`参数，设置最大等待时间
   - 在等待类操作中应用该参数限制等待时长

5. **脚本保存逻辑**
   - 生成唯一文件名（基于时间戳）
   - 将步骤数组包装到完整 JSON 结构中
   - 保存到指定路径，并更新数据库记录

## 数据结构

1. **录制配置数据结构**

   ```json
   {
     "device": "设备ID",
     "name": "脚本名称",
     "description": "脚本描述",
     "mode": "record/record-no-match",
     "max_duration": 30
   }
   ```

2. **生成的 JSON 脚本结构**
   ```json
   {
     "steps": [
       {
         "step": 1,
         "class": "element-class-name",
         "action": "click",
         "x": 100,
         "y": 200
       },
       {
         "step": 2,
         "class": "another-element",
         "action": "swipe",
         "x": 100,
         "y": 200,
         "x2": 300,
         "y2": 400
       }
     ]
   }
   ```

## 实现注意事项

1. **性能考虑**

   - 使用多线程架构，避免 UI 检测影响操作响应性
   - 实时保存录制进度，防止意外中断导致数据丢失

2. **兼容性处理**

   - 确保录制的脚本符合回放引擎的要求
   - 正确处理不同分辨率设备的坐标转换

3. **错误处理**

   - 录制过程中出现异常时记录日志，但不中断录制流程
   - 提供录制失败的错误反馈

4. **需要注意的限制**
   - 录制功能保持现状，不增加右键-新增录制动作的功能
   - 确保录制的脚本能够正确区分`step`和`Priority`元素
   - 简单的线性拖动已足够满足滑动操作需求
