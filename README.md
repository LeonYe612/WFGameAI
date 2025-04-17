# WFGame AI 自动化测试框架

## 项目概述

WFGame AI 自动化测试框架是一个基于计算机视觉（YOLO）与Airtest的游戏UI自动化测试解决方案。该框架通过深度学习模型实现了跨平台、跨分辨率的UI元素识别，显著降低了传统图像识别自动化测试的维护成本，提高了测试稳定性。

### 核心特性

- **AI驱动的UI识别**：使用YOLO模型进行实时UI元素检测
- **多设备并行测试**：支持多台设备同时执行测试用例
- **完整的测试流程**：包含录制、回放、报告生成等全流程功能
- **智能报告系统**：生成详细的HTML测试报告，支持多设备汇总
- **三种测试模式**：
  - 固定场景模式：预设流程自动化遍历
  - UI深度遍历模式：智能探索未知界面
  - 路径全量遍历模式：自动验证所有可能路径

## 技术架构

```
WFGameAI/
├── scripts/                # 核心脚本目录
│   ├── train_model.py     # 模型训练
│   ├── record_script.py   # 测试录制
│   └── replay_script.py   # 测试回放
├── models/                 # 模型存储
├── datasets/              # 训练数据集
├── outputs/               # 输出目录
│   ├── train/            # 训练输出
│   ├── recordlogs/       # 录制日志
│   └── replay_reports/   # 回放报告
└── templates/            # 报告模板
```

## 环境要求

- Python 3.9+
- PyTorch
- Ultralytics YOLO
- OpenCV
- Airtest
- ADB工具

## 快速开始

1. **环境配置**
```bash
# 克隆仓库
git clone https://github.com/username/WFGameAI.git
cd WFGameAI

# 安装依赖
pip install -r requirements.txt
```

2. **模型训练**
```bash
python scripts/train_model.py
```

3. **生成标注**
```bash
python scripts/generate_annotations.py
```

4. **录制测试**
```bash
# 基础录制（仅记录匹配按钮）
python record_script.py --record

# 增强录制（记录所有点击）
python record_script.py --record-no-match
```

5. **回放测试**
```bash
# 单脚本回放

python replay_script.py --show-screens --script outputs/recordlogs/scene2_guide_steps_2025-04-07.json --max-duration 30
``` --script参数指定了回放步骤文件为outputs/recordlogs/scene2_guide_steps_2025-04-07.json，可能会循环执行一到多次，直到达到最大运行时间30秒。```

python replay_script.py --show-screens --script outputs/recordlogs/scene1_login_steps_2025-04-07.json --loop-count 1：
```--script参数指定了回放步骤文件为outputs/recordlogs/scene1_login_steps_2025-04-07.json，并且会循环执行一次。```

# 多脚本顺序回放
```python replay_script.py --show-screens --script outputs/recordlogs/scene1_nologin_steps_2025-04-07.json --loop-count 1 --script outputs/recordlogs/scene2_guide_steps_2025-04-07.json --max-duration 30```

```说明：先执行场景1的登录操作，然后执行场景2的引导操作。
    --script 参数表示指定了回放步骤文件为outputs/recordlogs/scene1_nologin_steps_2025-04-07.json 
    --loop-count 1 ，表示此文件只会循环执行一次。
    --script 参数指定了回放步骤文件为outputs/recordlogs/scene2_guide_steps_2025-04-07.json 
    --max-duration 30，表示此步骤无视循环次数，会执行30秒后结束。且只对此文件生效，非全局。```




## 测试报告

### 报告结构
```
outputs/
├── replay_reports/              # 报告根目录
│   ├── summary_report_*.html   # 汇总报告
│   └── device_name_timestamp/  # 设备报告目录
│       ├── log.html           # 详细测试报告
│       ├── static/            # 静态资源
│       └── log/              # 日志和截图
└── recordlogs/                # 录制脚本存储
```

### 报告特性

- 分层结构：设备级别报告 + 汇总报告
- 详细记录：包含每步操作的截图和结果
- 资源完整：确保所有静态资源可访问
- 交互友好：支持报告间快速导航

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

## 贡献指南

欢迎提交Issue和Pull Request来改进项目。请确保：

1. 遵循项目的代码规范
2. 添加必要的测试用例
3. 更新相关文档
4. 提供清晰的提交信息

## 许可证

[MIT License](LICENSE)

## 联系方式

- 项目维护者：[Your Name]
- 邮箱：[your.email@example.com]
- 项目主页：[GitHub Repository URL]
