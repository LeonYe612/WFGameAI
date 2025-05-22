# 报告路径修复指南

## 问题描述

WFGameAI系统的报告页面无法显示已生成的报告列表，尽管报告文件已经存在于以下目录：

```
C:\Users\Administrator\PycharmProjects\WFGameAI\wfgame-ai-server\apps\reports\summary_reports
```

问题原因是系统配置文件 `config.ini` 中指定的报告路径为：

```
[paths]
reports_dir = ${server_dir}\outputs\WFGameAI-reports
ui_reports_dir = ${reports_dir}\ui_reports
```

导致系统在错误的位置查找报告文件。

## 解决方案

我们实施了以下修复方案：

1. 修改了 `apps/reports/views.py` 中的代码，使其可以同时检查两个可能的报告目录：
   - 配置文件中指定的目录 (`outputs/WFGameAI-reports/ui_reports`)
   - 实际存储报告的目录 (`apps/reports/summary_reports`)

2. 创建了 `fix_report_paths.py` 脚本，用于：
   - 自动将报告文件从 `apps/reports/summary_reports` 同步到 `outputs/WFGameAI-reports/ui_reports`
   - 尝试创建符号链接（在支持的系统上）或直接复制文件

3. 更新了 Django 静态文件设置，添加了 `outputs` 目录到 `STATICFILES_DIRS`，确保能正确访问两个位置的报告文件

## 使用说明

### 手动同步报告

如果需要手动同步报告文件，可以运行：

```bash
# Windows
python fix_report_paths.py

# 或使用批处理文件
fix_report_paths.bat
```

### 长期解决方案

为了彻底解决此问题，建议选择以下一种方法：

1. **方法一：修改配置文件**

   将 `config.ini` 中的报告路径更新为实际路径：

   ```ini
   [paths]
   reports_dir = ${server_dir}\apps\reports
   ui_reports_dir = ${reports_dir}\summary_reports
   ```

2. **方法二：统一报告生成位置**

   修改报告生成逻辑，将所有报告统一保存到配置文件指定的位置。

## 注意事项

- 重启服务器以使更改生效
- 确保 `outputs/WFGameAI-reports/ui_reports` 目录具有正确的读写权限
- 如果使用方法一修改配置文件，请确保更新所有依赖于该配置的代码

## 技术细节

修复涉及以下文件：

1. `apps/reports/views.py` - 修改报告列表获取逻辑
2. `wfgame_ai_server_main/settings.py` - 更新静态文件配置
3. `fix_report_paths.py` - 创建报告同步脚本
4. `fix_report_paths.bat` - 批处理文件调用脚本

通过上述修改，系统现在可以：

- 从两个位置查找报告文件
- 正确显示报告列表
- 准确计算设备数量和成功率
- 维持所有报告的链接有效性
