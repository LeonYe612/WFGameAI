# 报告目录结构修复脚本

此批处理文件用于修复和统一报告目录结构，将所有报告相关文件迁移到标准位置。

## 功能说明

运行此脚本将：

1. 创建规范的报告目录结构，包括：
   - 汇总报告目录 (`apps/reports/summary_reports`)
   - 单设备报告目录 (`apps/reports/ui_run/WFGameAI.air/log`)
   - 静态资源目录 (`apps/reports/staticfiles`)

2. 迁移现有报告文件到新目录
   - 把旧目录 `apps/staticfiles/reports` 中的文件移动到 `apps/reports/summary_reports`
   - 把旧目录 `apps/staticfiles/ui_run` 中的文件移动到 `apps/reports/ui_run`

3. 复制Airtest静态资源文件
   - 将Airtest包中的CSS、JS、字体和图片资源复制到 `apps/reports/staticfiles`

## 使用方法

双击运行 `fix_report_dirs.bat` 文件，或在命令行中执行：

```
cd wfgame-ai-server
.\fix_report_dirs.bat
```

## 注意事项

1. 此脚本执行后，请重启Django服务器以确保更改生效
2. 不会删除现有文件，仅进行复制和迁移操作
3. 可以多次执行此脚本，不会产生问题
