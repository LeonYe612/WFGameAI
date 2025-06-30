# 报告模块说明文档

## 目录结构说明

报告模块(`apps/reports`)是专门用于管理测试报告相关业务的目录，包含以下主要部分：

### 目录结构

```
apps/reports/
├── staticfiles/           # 静态资源目录，包含报告需要的CSS、JS等资源
│   ├── css/              # 样式文件
│   ├── js/               # JavaScript文件
│   ├── fonts/            # 字体文件
│   └── image/            # 图片资源
│
├── summary_reports/       # 汇总报告存放目录（替代原来的reports目录）
│   ├── summary_report_*  # 带时间戳的汇总报告HTML文件
│   └── latest_report.html # 最新汇总报告的快捷方式
│
├── ui_run/                # UI自动化测试运行目录
│   └── WFGameAI.air/     # Airtest项目目录
│       └── log/          # 设备日志目录
│           └── DeviceSerial_YYYY-MM-DD-HH-MM-SS/ # 各设备的运行报告目录
│               ├── log.txt           # 设备执行日志（JSON格式）
│               ├── log.html          # 设备报告HTML文件
│               ├── *.jpg             # 操作截图文件
│               ├── *_small.jpg       # 截图缩略图文件
│               └── script.py         # 执行脚本副本
│
├── templates/             # 报告模板文件目录
│   ├── summary_template.html  # 汇总报告模板
│   └── log_template.html      # 设备报告模板
│
├── __init__.py            # 包初始化文件
├── apps.py                # Django应用配置
├── urls.py                # URL路由配置
├── views.py               # 视图函数
└── fix_static_dirs.py     # 目录结构修复脚本
```

## 主要功能说明

1. **多设备报告管理**
   - 支持多设备并发执行，每个设备独立生成报告
   - 设备报告目录结构：`设备序列号_YYYY-MM-DD-HH-MM-SS/`
   - 每个设备目录包含完整的执行日志、截图和HTML报告

2. **设备报告目录结构**
   ```
   CWM0222215003786_2025-06-30-16-18-06/
   ├── log.txt              # JSON格式的执行日志
   ├── log.html            # 可视化HTML报告
   ├── 1751271056663.jpg   # 操作截图（原始大小）
   ├── 1751271056663_small.jpg # 截图缩略图
   └── script.py           # 执行的脚本副本
   ```

3. **日志格式说明**
   - log.txt采用每行一个JSON对象的格式
   - 每个日志条目包含操作类型、参数、截图路径、执行结果等信息
   - 支持AI检测操作的详细日志记录

4. **汇总报告管理**
   - 汇总报告（聚合多个设备报告）存放在 `summary_reports/` 目录下
   - 汇总报告使用时间戳命名，如 `summary_report_2025-06-30-16-18-28.html`
   - 提供设备执行概览和详细报告链接

3. **静态资源管理**
   - 报告相关的静态资源（CSS、JS、字体、图片）集中存放在 `staticfiles` 目录下
   - 此目录已在Django设置中配置为静态文件目录，可通过URL `/static/reports/` 访问

## AI检测操作支持

- ✅ **Priority模式脚本支持**：支持基于Priority字段的AI检测脚本执行
- ✅ **AI视觉检测**：支持`ai_detection_click`等AI检测操作
- ✅ **截图自动保存**：操作执行时自动截图并保存到设备报告目录
- ✅ **日志完整记录**：记录AI检测结果、置信度、检测区域等详细信息
- ✅ **多种截图方法**：支持adb shell、subprocess、airtest等多种截图方式
- ✅ **错误处理机制**：截图失败时使用fallback方法确保操作继续

## 修复历史

### 2025-06-30 重大修复
- 🔧 **修复多设备报告生成问题**：解决了报告目录创建和日志写入问题
- 🔧 **修复ActionProcessor日志路径**：统一日志文件路径为设备目录下的log.txt
- 🔧 **修复截图保存路径**：截图文件直接保存在设备目录下，不创建log子目录
- 🔧 **增强截图可靠性**：添加多种截图方法的fallback机制
- ✅ **验证多设备并发**：确保多设备同时执行时报告生成正常

## 访问URL说明

- 汇总报告URL: `/static/reports/summary_reports/[报告文件名]`
- 设备报告URL: `/static/reports/ui_run/WFGameAI.air/log/[设备目录]/log.html`
- 设备截图URL: `/static/reports/ui_run/WFGameAI.air/log/[设备目录]/[截图文件名]`
- 静态资源URL: `/static/reports/staticfiles/[资源类型]/[文件名]`

## 重要注意事项

1. **目录结构要求**：
   - 设备报告目录结构必须为：`设备序列号_时间戳/`
   - 所有文件（log.txt、log.html、截图等）必须直接存放在设备目录下
   - 禁止创建log子目录，避免路径混乱

2. **文件命名规范**：
   - 截图文件：使用时间戳命名，如`1751271056663.jpg`
   - 缩略图：在原文件名基础上添加`_small`后缀
   - 日志文件：固定为`log.txt`和`log.html`

3. **多设备支持**：
   - 支持多台设备同时执行脚本
   - 每个设备独立生成报告目录
   - 汇总报告自动聚合所有设备的执行结果

4. **故障排除**：
   - 如果报告显示"0个步骤"，检查ActionProcessor的log_txt_path设置
   - 如果截图不显示，确认截图文件保存在正确的设备目录下
   - 如果汇总报告为空，检查设备报告目录是否正确返回
