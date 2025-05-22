# 报告系统修复指南

## 问题描述

报告系统存在以下问题：

1. 静态文件目录结构不一致，导致无法正确访问报告文件
2. 报告URL路径不正确，导致404错误
3. JavaScript中的模板变量未正确替换

## 解决方案

我们采取了以下步骤来解决这些问题：

1. 修复了API中的URL路径，使其正确指向`/static/reports/summary_reports/`目录
2. 创建并执行了`copy_reports.py`脚本，将报告文件从`apps/reports/summary_reports`复制到`staticfiles/reports/summary_reports`目录
3. 验证并修复了报告详情页中的模板变量问题

## 修复工具

我们提供了以下工具来帮助修复报告系统：

- `copy_reports.py`: 将报告文件复制到正确的静态文件目录
- `verify_reports.py`: 验证报告系统是否正常工作
- `fix_reports.bat`: 批处理文件，执行上述两个脚本

## 如何使用

如果您遇到报告系统问题，请按照以下步骤操作：

1. 确保Django服务器正在运行
2. 运行`fix_reports.bat`批处理文件
3. 检查脚本输出，确认所有功能正常

## 常见问题

### 报告文件404错误

如果您看到类似于以下的错误：

```
WARNING basehttp "GET /static/reports/summary_report_*.html HTTP/1.1" 404 2001
```

这通常表示静态文件目录结构有问题。请运行`copy_reports.py`脚本将报告文件复制到正确的目录。

### 模板变量未替换

如果您在报告页面上看到未替换的模板变量，如`{{ report_id }}`，这表示JavaScript代码未正确渲染模板。请检查`report_detail.html`文件，确保所有模板变量都已被正确替换为JavaScript变量。

## 目录结构

报告系统使用以下目录结构：

```
wfgame-ai-server/
├── apps/
│   └── reports/
│       └── summary_reports/          # 报告生成目录
│           └── summary_report_*.html # 生成的报告HTML文件
│
└── staticfiles/
    └── reports/
        └── summary_reports/          # 静态文件服务目录
            └── summary_report_*.html # 供前端访问的报告HTML文件
```

## 最佳实践

为确保报告系统正常工作，请遵循以下最佳实践：

1. 生成新报告后，始终运行`copy_reports.py`脚本将其复制到静态文件目录
2. 定期验证报告系统功能，确保所有报告都可以正常访问
3. 在修改报告相关代码前，先备份原始文件

## 技术细节

报告系统依赖于以下技术组件：

1. Django静态文件服务（`django.contrib.staticfiles`）
2. JavaScript前端代码（`report_detail.html`和`reports_template.html`）
3. API后端代码（`api/reports.py`和`apps/reports/views.py`）

如果需要进一步了解系统架构，请参考代码注释和相关文档。
