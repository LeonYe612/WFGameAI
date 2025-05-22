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
│           └── Device-*/ # 各设备的运行报告目录
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

1. **单设备报告管理**
   - 单设备运行报告存放在 `apps/reports/ui_run/WFGameAI.air/log/设备目录/` 下
   - 每个设备目录包含该设备的测试报告HTML和相关截图

2. **汇总报告管理**
   - 汇总报告（聚合多个设备报告）存放在 `apps/reports/summary_reports/` 目录下
   - 汇总报告使用时间戳命名，如 `summary_report_2025-05-21-17-32-30.html`
   - 最新的汇总报告会同时保存一份为 `latest_report.html`

3. **静态资源管理**
   - 报告相关的静态资源（CSS、JS、字体、图片）集中存放在 `apps/reports/staticfiles` 目录下
   - 此目录已在Django设置中配置为静态文件目录，可通过URL `/static/reports/` 访问

## 访问URL说明

- 汇总报告URL: `/static/reports/summary_reports/[报告文件名]`
- 设备报告URL: `/static/reports/ui_run/WFGameAI.air/log/[设备目录]/log.html`
- 静态资源URL: `/static/reports/staticfiles/[资源类型]/[文件名]`

## 注意事项

1. 请不要手动删除或移动报告目录中的文件，以免影响报告的正常显示
2. 如果发现报告显示异常，可以运行 `fix_report_dirs.bat` 修复目录结构
3. 修改报告模板时，请确保保持HTML结构的完整性，尤其是CSS和JS的引用路径
