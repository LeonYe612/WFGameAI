# WFGame AI 自动化测试框架

## 项目概述

WFGame AI 自动化测试框架是一个基于YOLO11m计算机视觉的游戏UI自动化测试解决方案。该框架通过深度学习模型实现了跨平台、跨分辨率的UI元素精准识别，彻底替代传统图像对比方法，显著提高了自动化测试的稳定性和可靠性，并支持多设备并行测试（1-100台规模）。

## 项目结构（2025年5月最新，已对齐AutotestWebD分层）

```
WFGameAI/
├── datasets/                  # 数据集目录
│   ├── preprocessed/          # 预处理后的数据
│   └── templates/             # 报告模板
├── docs/                      # 文档目录
├── scripts/                   # 脚本与工具目录
├── templates/                 # 报告/页面模板目录
├── wfgame-ai-server/          # 服务器端主目录（Django后端）
│   ├── apps/                  # 业务App统一目录（如devices、scripts、reports等）
│   │   ├── devices/           # 设备管理App
│   │   ├── scripts/           # 脚本管理App
│   │   ├── reports/           # 报告管理App
│   │   ├── ...                # 其他业务App
│   ├── all_models/            # 统一模型目录（如有）
│   ├── all_urls/              # 统一路由管理目录（如有）
│   ├── staticfiles/           # 静态资源目录
│   ├── templates/             # 模板目录
│   ├── testcase/              # 测试用例目录
│   ├── logs/                  # 日志目录
│   ├── config.ini             # 配置文件
│   ├── manage.py              # Django管理脚本
│   └── wfgame_ai_server/      # 主项目目录（urls.py/settings.py/wsgi.py/asgi.py等）
├── wfgame-ai-web/             # 前端Web界面（Vue3）
├── requirements.txt           # 依赖列表
├── start_wfgame_ai.py         # 启动脚本（后端）
└── train_model.py             # 模型训练脚本
```

### 结构说明
- **wfgame-ai-server/apps/**：所有Django业务App统一放置于此，便于分层管理和后期扩展。
- **wfgame-ai-server/all_models/**、**all_urls/**：如需统一管理模型和路由，可在此维护。
- **wfgame-ai-server/wfgame_ai_server/**：主项目目录，仅保留urls.py、settings.py、wsgi.py、asgi.py等核心文件。
- 其他目录与AutotestWebD分层一致。 