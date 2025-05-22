# 标记不再使用的目录

在我们完成报告目录结构优化后，有一些旧的目录不再使用，但为了确保安全，我们不会自动删除这些目录。

## 使用说明

1. 运行脚本标记不再使用的目录：
   - Windows: 双击运行 `mark_unused_dirs.bat`
   - 或者使用Python: `python mark_unused_dirs.py`

2. 脚本会将以下目录添加"_useless"后缀：
   - `apps/staticfiles/reports` → `apps/staticfiles/reports_useless`
   - `apps/staticfiles/ui_run` → `apps/staticfiles/ui_run_useless`
   - `outputs/WFGameAI-reports` → `outputs/WFGameAI-reports_useless`
   - `outputs/device_reports` → `outputs/device_reports_useless`

3. 确认这些目录不再被使用：
   - 启动服务，检查报告功能是否正常
   - 确保新的报告能正确保存在 `apps/reports/summary_reports` 和 `apps/reports/ui_run`

4. 手动删除标记的目录：
   - 确认一切正常后，可以手动删除这些带有"_useless"后缀的目录

## 注意事项

- 请勿删除其他未标记的目录
- 如果发现删除后有功能异常，可以将这些目录恢复（去掉"_useless"后缀）
- 这个脚本是一次性使用的工具，在完成清理后可以删除
