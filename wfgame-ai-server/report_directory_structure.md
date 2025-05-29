# WFGameAI 统一报告目录结构说明

## 1. 概述

本文档介绍了 WFGameAI 项目中的统一报告目录结构。为了解决之前报告文件散布在多个位置的问题，我们实现了一个集中式的目录结构，将所有报告相关文件整合到 `staticfiles/reports/` 目录下。

## 2. 目录结构

项目根目录下的统一报告目录结构如下：

```
wfgame-ai-server/
└── staticfiles/
    └── reports/
        ├── summary_reports/      # 存放汇总报告
        └── ui_run/
            └── WFGameAI.air/
                └── log/          # 存放设备报告和截图
```

## 3. 目录用途

### 3.1 staticfiles/reports/

这是所有报告相关文件的统一根目录，位于 Django 项目的 staticfiles 目录下，确保可以通过 Web 服务直接访问。

### 3.2 staticfiles/reports/summary_reports/

此目录存放所有汇总报告文件，包括：
- 汇总 HTML 报告（summary_report_*.html）
- 最新报告的快捷方式（latest_report.html）
- 汇总配置文件和模板

### 3.3 staticfiles/reports/ui_run/WFGameAI.air/log/

此目录存放所有设备测试报告，包括：
- 每个设备的报告子目录
- 屏幕截图
- 日志文件
- HTML 报告文件

## 4. 配置文件中的路径定义

在各个模块中，统一使用以下变量名定义报告目录结构：

```python
# 统一报告目录配置
STATICFILES_REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "staticfiles", "reports")
DEVICE_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "ui_run", "WFGameAI.air", "log")
SUMMARY_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "summary_reports")
```

关键模块中的配置：
- `apps/scripts/replay_script.py` - 自动化测试脚本中的路径配置
- `apps/reports/views.py` - 报告查看 API 中的路径配置
- `create_integrated_reports.py` - 集成报告生成脚本中的路径配置

## 5. 向后兼容

为了确保向后兼容，一些旧的变量名仍然保留，但它们现在指向新的统一目录：

```python
# 为兼容性保留UI_REPORTS_DIR变量，但指向新的设备报告目录
UI_REPORTS_DIR = DEVICE_REPORTS_DIR
```

## 6. 验证和修复

提供了验证脚本来确认统一目录结构的正确性：

```bash
# 验证目录结构
python validate_report_structure.py

# 修复目录结构
python validate_report_structure.py repair
```

## 7. 报告文件维护

### 7.1 定期清理

旧报告会逐渐占用大量存储空间，为此提供了自动清理工具：

```bash
# 清理30天前的报告文件
python cleanup_old_reports.py --days 30

# 模拟清理过程（不实际删除文件）
python cleanup_old_reports.py --days 30 --dry-run
```

也可以使用批处理脚本调用清理工具：

```batch
# 清理30天前的报告文件
cleanup_reports.bat 30
```

建议将此批处理脚本加入 Windows 任务计划程序，设置为每周执行一次。

### 7.2 注意事项

1. **不要手动修改目录结构**：使用脚本和提供的 API 来操作报告文件
2. **文件权限**：确保 Web 服务器对这些目录有读写权限
3. **定期清理**：使用提供的清理工具定期执行维护，避免占用过多磁盘空间

## 8. 排错指南

如果遇到与报告目录相关的问题，请按以下步骤排查：

1. 运行验证脚本检查目录结构：`python validate_report_structure.py`
2. 检查 Django 设置中的 `STATICFILES_DIRS` 是否包含 `staticfiles` 目录
3. 确认 `staticfiles/reports/` 及其所有子目录存在并具有合适的权限
4. 运行修复脚本：`python validate_report_structure.py repair`
5. 如果问题持续，检查日志文件和服务器错误记录

## 9. 未来改进

计划中的改进包括：

- 报告文件压缩存储
- 优化报告访问的性能
- 增强报告统计和分析功能

---

最后更新: 2025年5月29日 (新增报告自动清理功能)
