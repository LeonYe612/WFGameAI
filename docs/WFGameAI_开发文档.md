# WFGame AI自动化测试框架开发文档

## 功能概述
WFGame AI自动化测试框架是一个基于计算机视觉和深度学习技术的游戏UI自动化测试解决方案。该框架通过YOLO模型实现游戏界面元素的智能识别，支持多设备并行测试，提供完整的测试流程管理（包括录制、回放、报告生成），显著降低了传统图像识别自动化测试的维护成本，并确保在MAC和Windows系统上均可正常运行。

## 详细功能描述

### UI展示

#### 主控制面板
- **左侧区域**：设备连接状态列表
  - 显示所有已连接设备的名称（格式：品牌-型号-分辨率）
  - 设备状态指示器（已连接/未连接/测试中）
  - 每个设备项支持右键菜单（连接/断开/重启）

- **中央区域**：当前设备屏幕镜像
  - 实时显示设备屏幕内容
  - 显示当前识别到的UI元素（可选显示边界框）
  - 支持指定帧率（默认10fps以降低资源消耗）

- **右侧区域**：测试控制面板
  - 测试脚本选择器（下拉列表，从testcase目录读取JSON文件）
  - 控制按钮组（开始/暂停/停止）
  - 测试模式选择（单次执行/循环执行/时间限制执行）
  - 执行参数配置（循环次数/最大运行时间/等待超时）
  - 测试进度条和状态文本

- **底部区域**：日志输出窗口
  - 实时滚动显示操作日志
  - 日志级别过滤器（信息/警告/错误）
  - 支持日志导出功能

#### 测试报告页面
- **顶部区域**：测试基本信息
  - 测试标题和描述
  - 开始时间和结束时间
  - 执行设备列表和总数
  - 通过率统计和整体状态

- **中部区域**：测试结果可视化
  - 饼图显示测试用例通过/失败/跳过比例
  - 柱状图显示各设备测试结果对比
  - 折线图显示执行时间分布

- **底部区域**：测试用例详情表格
  - 编号、名称、预期结果、实际结果、状态和耗时
  - 按设备和场景进行分组
  - 支持按状态和执行时间排序
  - 失败项使用红色背景高亮显示
  - 点击行可展开显示详细信息和截图

### 交互流程

#### 设备连接流程
1. 系统启动后自动扫描可用设备
   - 使用`adb devices`检测Android设备
   - 使用`tidevice list`检测iOS设备
   - 显示设备序列号和基本信息

2. 用户选择设备并点击"连接"按钮
   - 系统尝试与设备建立连接
   - 检查设备状态和屏幕是否锁定
   - 如果锁定，自动尝试解锁（发送KEYCODE_WAKEUP）

3. 连接成功后更新设备状态
   - 状态指示器变为绿色
   - 开始接收屏幕镜像
   - 启用测试控制按钮

4. 连接失败处理
   - 显示错误提示对话框
   - 提供重试选项和设备检查指南
   - 记录错误日志以便后续分析

#### 测试执行流程
1. 用户从脚本列表中选择测试脚本
   - 支持单个脚本选择
   - 支持多个脚本顺序执行（按添加顺序）
   - 显示脚本基本信息（步骤数、预计执行时间）

2. 配置执行参数
   - 循环次数：设置脚本重复执行次数
   - 最大运行时间：设置测试最长持续时间
   - 失败处理：选择失败后继续/停止/重试策略

3. 点击"开始测试"按钮启动测试
   - 初始化测试环境和日志目录
   - 加载YOLO模型到内存
   - 按配置顺序执行测试脚本

4. 测试执行过程中
   - 实时更新屏幕镜像和识别结果
   - 更新测试进度条和步骤信息
   - 记录每步操作的截图和结果
   - 支持通过"暂停"按钮临时暂停执行

5. 测试完成处理
   - 显示测试完成对话框
   - 生成测试报告
   - 提示用户查看报告或继续新测试

#### 报告查看流程
1. 测试完成后自动弹出报告查看选项
   - 用户可选择"立即查看"或"稍后查看"
   - 可选择打开设备报告或汇总报告

2. 报告页面交互
   - 测试结果筛选（全部/成功/失败/跳过）
   - 设备切换导航（多设备测试时）
   - 步骤详情展开/折叠
   - 截图查看（支持原图和缩略图切换）

3. 报告导出功能
   - 导出为HTML格式（包含静态资源）
   - 导出为PDF格式（用于打印和分享）
   - 导出原始数据为JSON格式（用于二次分析）

### 逻辑功能

#### 设备管理模块
- **设备检测功能**
  - 定期扫描连接的物理设备和模拟器
  - 提取设备品牌、型号和分辨率信息
  - 生成唯一设备标识符（格式：品牌-型号-分辨率）
  - 支持热插拔检测和自动连接

- **设备连接管理**
  - 与设备建立ADB/tidevice连接
  - 监控连接状态，自动重连断开的设备
  - 设置屏幕常亮，防止测试过程中锁屏
  - 支持多设备并行操作，每设备独立线程

- **屏幕捕获功能**
  - 以设定帧率捕获设备屏幕
  - 自动调整分辨率以优化性能
  - 使用线程池管理多设备截图
  - 实现帧缓存队列，供识别模块使用

#### AI识别模块
- **模型管理功能**
  - 加载预训练的YOLO模型（yolo11m.pt）
  - 根据系统自动选择计算设备（CUDA/MPS/CPU）
  - 实现模型缓存和内存优化
  - 提供模型版本检查和自动升级

- **UI元素识别功能**
  - 对捕获的屏幕进行元素检测
  - 识别UI界面中的按钮、文本框等元素
  - 返回元素类别、位置坐标和置信度
  - 支持自定义置信度阈值（默认0.3）

- **结果优化功能**
  - 应用非极大值抑制（NMS）过滤重复检测
  - 坐标映射（从模型输入尺寸到实际屏幕尺寸）
  - 元素跟踪以提高帧间一致性
  - 识别结果缓存以提高性能

#### 操作执行模块
- **基础操作功能**
  - 点击操作（单击/双击/长按）
  - 滑动操作（方向和距离可配置）
  - 文本输入（支持中英文混合输入）
  - 特殊按键操作（HOME/BACK/MENU等）

- **操作定位策略**
  - 基于识别结果的智能定位
  - 相对坐标定位（相对屏幕比例）
  - 绝对坐标定位（精确像素点）
  - 元素中心点自动计算

- **操作验证功能**
  - 等待特定元素出现/消失
  - 截图对比验证
  - 超时和重试机制
  - 验证结果记录和日志

#### 测试脚本管理
- **脚本录制功能**
  - 用户操作实时录制
  - 智能元素识别和坐标记录
  - 自动添加等待和验证步骤
  - 录制脚本保存为JSON格式

- **脚本回放功能**
  - 按序执行脚本中的步骤
  - 支持条件分支和循环结构
  - 可调整执行速度和等待时间
  - 错误处理和恢复机制

- **脚本组织管理**
  - 按场景和功能分类管理脚本
  - 支持脚本组合和顺序执行
  - 脚本版本控制和备份
  - 脚本编辑和调试工具

#### 报告生成模块
- **数据收集功能**
  - 记录每个测试步骤的详细信息
  - 捕获关键节点的屏幕截图
  - 收集执行时间和性能指标
  - 异常和错误信息的详细记录

- **报告生成功能**
  - 使用Jinja2模板生成HTML报告
  - 处理静态资源（CSS/JS/图片）
  - 设备级报告和汇总报告生成
  - 报告数据结构化存储

- **报告优化功能**
  - 自动修复静态资源路径问题
  - 优化图片大小以提高加载速度
  - 实现报告间的交叉链接和导航
  - 提供失败分析和统计数据

## 数据模型

### 设备信息模型
```
DeviceInfo {
    id: String,              // 设备唯一标识
    name: String,            // 设备名称
    serial: String,          // 设备序列号
    platform: String,        // 平台类型(Android/iOS)
    brand: String,           // 设备品牌
    model: String,           // 设备型号
    resolution: {            // 屏幕分辨率
        width: Number,
        height: Number
    },
    status: String,          // 连接状态(connected/disconnected/testing)
    connected_time: DateTime, // 连接时间
    last_active: DateTime    // 最后活动时间
}
```

### 测试脚本模型
```
TestScript {
    id: String,               // 脚本ID
    name: String,             // 脚本名称
    description: String,      // 脚本描述
    created_at: DateTime,     // 创建时间
    updated_at: DateTime,     // 更新时间
    scenes: Array<Scene>,     // 场景列表
    version: String,          // 脚本版本
    author: String,           // 创建者
    tags: Array<String>       // 标签列表
}
```

### 场景模型
```
Scene {
    id: String,               // 场景ID
    name: String,             // 场景名称
    description: String,      // 场景描述
    steps: Array<TestStep>,   // 测试步骤
    max_retry: Number,        // 最大重试次数
    timeout: Number,          // 场景超时时间(秒)
    prerequisites: Array<String> // 前置条件
}
```

### 测试步骤模型
```
TestStep {
    id: String,               // 步骤ID
    name: String,             // 步骤名称
    action: String,           // 操作类型(click/swipe/wait/input)
    target: {                 // 操作目标
        type: String,         // 目标类型(element/coordinates)
        class: String,        // 元素类别
        name: String,         // 元素名称
        coordinates: [x, y]   // 坐标值
    },
    params: {                 // 操作参数
        duration: Number,     // 持续时间(秒)
        text: String,         // 输入文本
        direction: String,    // 滑动方向
        distance: Number      // 滑动距离
    },
    wait_time: Number,        // 执行后等待时间(秒)
    timeout: Number,          // 步骤超时时间(秒)
    retry_count: Number,      // 重试次数
    verification: {           // 验证条件
        type: String,         // 验证类型(element_appear/element_disappear/image_match)
        target: String,       // 验证目标
        timeout: Number       // 验证超时时间(秒)
    }
}
```

### 测试结果模型
```
TestResult {
    id: String,               // 结果ID
    script_id: String,        // 脚本ID
    device_id: String,        // 设备ID
    start_time: DateTime,     // 开始时间
    end_time: DateTime,       // 结束时间
    duration: Number,         // 持续时间(毫秒)
    status: String,           // 状态(passed/failed/skipped)
    pass_rate: Number,        // 通过率
    scenes: Array<SceneResult>, // 场景结果
    error: String,            // 错误信息
    logs: Array<LogEntry>,    // 日志条目
    summary: {                // 结果汇总
        total_steps: Number,  // 总步骤数
        passed_steps: Number, // 通过步骤数
        failed_steps: Number, // 失败步骤数
        skipped_steps: Number // 跳过步骤数
    }
}
```

### 场景结果模型
```
SceneResult {
    scene_id: String,         // 场景ID
    name: String,             // 场景名称
    status: String,           // 状态(passed/failed/skipped)
    start_time: DateTime,     // 开始时间
    end_time: DateTime,       // 结束时间
    duration: Number,         // 持续时间(毫秒)
    steps: Array<StepResult>, // 步骤结果
    error: String            // 错误信息
}
```

### 步骤结果模型
```
StepResult {
    step_id: String,          // 步骤ID
    name: String,             // 步骤名称
    status: String,           // 状态(passed/failed/skipped)
    start_time: DateTime,     // 开始时间
    end_time: DateTime,       // 结束时间
    duration: Number,         // 持续时间(毫秒)
    retry_count: Number,      // 实际重试次数
    screenshot_before: String, // 执行前截图路径
    screenshot_after: String,  // 执行后截图路径
    error: String,            // 错误信息
    detection_result: {       // 识别结果
        class: String,        // 识别的类别
        confidence: Number,   // 置信度
        coordinates: [x, y]   // 坐标位置
    }
}
```

### YOLO模型配置
```
YOLOConfig {
    model_path: String,       // 模型文件路径
    version: String,          // 模型版本(yolov8m)
    input_size: Number,       // 输入尺寸(640)
    confidence_threshold: Number, // 置信度阈值(0.3)
    iou_threshold: Number,    // IoU阈值(0.6)
    device: String,           // 计算设备(cuda/mps/cpu)
    classes: Array<String>,   // 类别名称列表
    augment: Boolean,         // 是否使用增强
    half_precision: Boolean   // 是否使用半精度
}
```

### 报告配置模型
```
ReportConfig {
    template_path: String,    // 模板路径
    output_dir: String,       // 输出目录
    static_resource_dir: String, // 静态资源目录
    title: String,            // 报告标题
    logo_path: String,        // Logo路径
    include_screenshots: Boolean, // 是否包含截图
    compress_images: Boolean, // 是否压缩图片
    generate_pdf: Boolean,    // 是否生成PDF
    theme: String            // 主题样式(light/dark)
}
```

## 技术细节

### YOLO模型配置
- 模型版本：Ultralytics YOLOv8m（中型模型）
- 自定义训练模型：yolo11m.pt
- 输入图像尺寸：640x640像素
- 训练配置：
  - 优化器：AdamW
  - 学习率：0.001，最终学习率比例0.01
  - 批次大小：基于硬件自适应（RTX 4090: 24, 其他: 4）
  - 训练轮次：100
  - 早停耐心值：20
  - 半精度训练：启用
  - 自动混合精度：启用
  - 数据增强：启用（包括水平翻转、色彩扰动）
  - 损失权重：box=7.5, cls=0.5, dfl=1.5
- 推理配置：
  - 置信度阈值：0.3
  - 设备：自适应（CUDA/MPS/CPU）
  - 图像预处理：调整大小、归一化

### 设备连接实现
- Android设备：使用adbutils库通过ADB连接
- iOS设备：使用tidevice库连接
- 设备检测：定期扫描并自动识别设备类型
- 连接管理：保持设备连接并监控状态变化
- 屏幕控制：确保测试过程中屏幕常亮
- 多设备支持：使用线程池同时管理多个设备
- 断连处理：自动重连机制（最多5次尝试）

### 跨平台兼容方案
- 系统检测：使用platform.system()检测当前系统
- 计算设备选择：
  - Windows: 优先使用CUDA加速
  - Mac: 使用Metal Performance Shaders (MPS)加速
  - 其他: 回退到CPU模式
- 路径处理：使用os.path.join确保路径分隔符正确
- 设备兼容性：统一设备抽象接口，底层根据平台区分实现
- 依赖管理：条件安装特定平台依赖（requirements.txt中包含平台标记）

### 测试脚本格式
- 文件格式：JSON
- 存储位置：testcase目录
- 基本结构：场景→步骤→操作和验证
- 步骤类型：点击、滑动、等待、输入、自定义
- 定位方式：元素识别（优先）或绝对/相对坐标
- 条件控制：支持分支、循环和依赖步骤
- 脚本执行：支持单个执行、循环执行和超时控制
- 脚本编辑：支持手动编辑和录制生成

### 报告生成系统
- 模板引擎：Jinja2
- 报告格式：HTML（主要）、PDF（可选）
- 静态资源：从airtest包中复制CSS/JS/图片资源
- 目录结构：
  - 设备报告：outputs/WFGameAI-reports/ui_run/WFGameAI.air/log/{设备名}_{时间戳}/
  - 汇总报告：outputs/WFGameAI-reports/ui_reports/summary_report_{时间戳}.html
- 资源路径修复：自动检测和修复静态资源引用路径
- 报告层级：设备报告（详细步骤）→汇总报告（整体结果）
- 交互功能：步骤展开/折叠、截图查看、结果筛选

### 系统性能优化
- 内存管理：
  - 大内存系统（>24GB）：使用RAM缓存
  - 标准系统：使用磁盘缓存
- GPU优化：
  - 定期清理GPU缓存（每2个epoch）
  - 限制分配器大小：max_split_size_mb:128
  - 启用TensorFloat-32（RTX系列GPU）
- 批处理优化：
  - RTX 4090：batch_size=24, workers=16
  - 其他GPU：batch_size=4, workers=4
- 存储优化：
  - 自动清理旧实验目录（保留最新3个）
  - 每实验目录保留最新3个模型文件
  - 压缩报告截图（保留原图和缩略图）

### 异常处理机制
- 设备异常：
  - 连接断开：自动重连（最多5次）
  - 屏幕锁定：发送解锁命令唤醒
  - 设备无响应：超时处理和记录
- 识别异常：
  - 目标未找到：重试、滑动寻找、降级处理
  - 低置信度：记录警告并尝试备选方案
  - 模型错误：使用备用定位策略
- 执行异常：
  - 步骤超时：记录失败并决定是否继续
  - 验证失败：重试或跳过后续步骤
  - 资源访问错误：创建备份和替代资源

### 数据持久化方案
- 测试脚本：JSON格式（testcase目录）
- 测试数据：按设备和时间戳组织
  - 截图：log/{设备}_{时间戳}/log/*.jpg
  - 日志：log/{设备}_{时间戳}/log.txt
- 报告存储：
  - HTML报告：WFGameAI-reports/ui_reports/
  - 静态资源：报告目录下static/
- 模型存储：
  - 训练模型：train_results/train/exp_{时间戳}/weights/
  - 最佳模型：outputs/weights/best_{时间戳}.pt

### 安全和权限控制
- 设备权限：
  - 要求设备开启开发者模式
  - 需要ADB调试授权
  - iOS设备需信任开发证书
- 数据安全：
  - 本地存储所有测试数据
  - 支持敏感数据清理机制
- 代码安全：
  - 使用相对路径避免路径泄露
  - 安全的文件操作API
  - 避免硬编码敏感信息

### CI/CD集成
- 命令行支持：
  - 脚本选择：--script
  - 执行控制：--loop-count, --max-duration
  - 显示控制：--show-screens
- 批处理运行：支持多脚本串联执行
- 自动化测试：支持无人值守测试
- 报告集成：生成可在CI系统展示的HTML报告
- 结果输出：支持JSON格式输出便于解析
- 错误代码：提供标准化退出码表示测试结果 