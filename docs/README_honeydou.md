# Honeydou 自动化测试平台

> 更新时间：2023年5月28日

## 平台概述

Honeydou是一个完整的自动化测试平台，采用Django+Vue构建的B/S架构，提供了丰富的测试工具和功能。该平台设计用于支持多种测试场景，包括UI自动化测试、接口测试、性能测试等，并提供了完善的任务管理、报告生成和设备管理功能。

## 核心组件

### 1. Web平台 (AutotestWebD)

基于Django框架开发的Web应用，提供了完整的用户界面和后端服务：

- **用户管理系统**：登录、权限控制
- **UI测试模块**：UI测试脚本管理、任务调度、执行报告
- **接口测试模块**：接口定义、测试用例管理
- **测试资源管理**：设备管理、环境配置
- **报告系统**：测试结果展示、统计分析
- **配置中心**：全局参数配置、环境变量管理

### 2. 自动化框架 (AutotestFramework)

提供底层测试执行引擎和核心功能：

- **测试执行引擎**：任务调度、多线程支持
- **关键字驱动框架**：支持多种测试操作的关键字
- **设备控制**：基于ADB的设备连接与控制
- **报告生成器**：生成HTML格式的测试报告
- **核心模型**：TaskBase、HttpBase、DubboBase等基础类

### 3. 部署与环境

- **容器化部署**：支持Docker部署，包含完整的docker-compose配置
- **数据库**：使用MySQL 5.7存储测试数据、用户信息等
- **缓存服务**：使用Redis 7.2提供缓存支持
- **Web服务**：使用uWSGI作为应用服务器

## 技术栈

- **后端**：Python 3.11 + Django 3.2
- **前端**：HTML/CSS/JavaScript + jQuery
- **数据库**：MySQL 5.7
- **缓存**：Redis 7.2
- **UI测试库**：Airtest 1.3.5 + PocoUI 1.0.94
- **任务队列**：Celery 5.4.0
- **WebSocket**：Django Channels 3.0.5
- **容器化**：Docker + docker-compose

## 功能模块

平台包含以下核心功能模块：

1. **自动化测试工具**
   - 设备管理与连接
   - 脚本录制与回放
   - 任务调度与执行
   - 报告生成与分析

2. **UI测试功能**
   - UI元素识别与操作
   - 测试用例管理
   - 测试套件组织
   - 执行结果分析

3. **接口测试功能**
   - 接口定义与管理
   - 测试用例编写
   - 数据驱动测试
   - 断言与验证

4. **构建自动化**
   - 前端构建流程
   - 服务器管理

5. **版本质量数据**
   - 禅道项目集成
   - 质量数据统计
   - 项目进度监控

6. **QA资产管理**
   - 测试设备信息管理
   - 资源使用状态跟踪

## 系统架构

```
Honeydou平台
├── Web层 (AutotestWebD)
│   ├── 用户界面 (templates)
│   ├── 业务逻辑 (apps)
│   ├── 静态资源 (static)
│   └── URL路由 (all_urls)
├── 框架层 (AutotestFramework)
│   ├── 核心模型 (cores/model)
│   ├── 关键字 (cores/keywords)
│   ├── 处理器 (cores/processor)
│   ├── 工具库 (cores/tools)
│   └── 报告生成 (report)
└── 基础设施
    ├── 数据库 (MySQL)
    ├── 缓存 (Redis)
    ├── 任务队列 (Celery)
    └── Web服务器 (uWSGI)
```

## 与WFGameAI的集成点

Honeydou平台与WFGameAI项目有以下关键集成点：

1. **Web界面集成**：WFGameAI可利用Honeydou已有的B/S架构平台，集成YOLO视觉识别模块
2. **任务管理**：利用现有的任务调度系统管理大规模设备测试任务
3. **设备管理**：扩展现有的设备管理功能，支持1-100台设备的并行测试
4. **报告系统**：基于现有报告模板，扩展AI视觉测试的特殊报告需求
5. **数据驱动**：利用现有数据驱动框架，实现脚本与测试数据的分离

## 配置与启动

### 环境要求
- Python 3.11
- MySQL 5.7
- Redis 7.2

### 安装依赖
```bash
pip install -r requirement.txt -i https://pypi.mirrors.ustc.edu.cn/simple/
```

### 使用Docker启动
```bash
cd docker-auto-platform
docker-compose up -d
```

## 结论

Honeydou自动化测试平台提供了一个完整的B/S架构测试平台基础，包含了用户管理、任务调度、设备管理、报告生成等核心功能。WFGameAI项目可以在此基础上集成YOLO视觉识别引擎，实现更稳定可靠的UI自动化测试，并支持大规模设备并行测试和数据驱动的测试场景。 