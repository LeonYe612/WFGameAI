# WFGameAI 报告目录结构优化

## 目录结构优化说明

为了统一管理测试报告相关代码和文件，我们进行了以下优化：

1. **报告业务集中管理**：所有与报告生成、报告输出相关的代码和文件已经统一放在 `apps/reports` 目录下管理，这是专门用于管理测试报告相关业务的目录。

2. **静态文件目录统一**：将多处创建或引用的 `staticfiles` 目录统一到 `apps/reports/staticfiles` 目录下，明确了该目录的用途为存放报告相关的静态资源文件（CSS、JS、fonts、image）。

3. **聚合报告存放目录**：为报告聚合（汇总多个设备报告）专门定义了目录 `\apps\reports\summary_reports`（替代原来目录名 `\apps\reports\reports`），这是统一的聚合报告存放位置。

4. **单设备报告存放目录**：单设备运行报告现统一存放在 `\wfgame-ai-server\apps\reports\ui_run\WFGameAI.air\log` 目录下，确保所有单设备报告都放在这个标准位置。

## 实施改动

以下是我们具体实施的改动：

1. 创建了新的目录结构：
   - `apps/reports/staticfiles` - 静态资源目录
   - `apps/reports/summary_reports` - 汇总报告目录
   - `apps/reports/ui_run/WFGameAI.air/log` - 单设备报告目录

2. 修改了代码中的路径引用，主要包括：
   - 将 `os.path.join(os.path.dirname(__file__), "..", "staticfiles", "ui_run")` 修改为 `os.path.join(os.path.dirname(__file__), "..", "reports", "ui_run")`
   - 将 `os.path.join(os.path.dirname(__file__), "..", "staticfiles", "reports")` 修改为 `os.path.join(os.path.dirname(__file__), "..", "reports", "summary_reports")`

3. 更新了静态文件配置：
   - 在 Django 的 settings.py 中添加了 `apps/reports` 到 `STATICFILES_DIRS`

4. 创建了管理和修复脚本：
   - `apps/reports/fix_static_path.py` - 用于修复和迁移报告文件
   - `fix_report_dirs.bat` - 一键执行修复脚本的批处理文件

## 使用说明

1. **查看报告**：
   - 汇总报告可通过 `/static/reports/summary_reports/[报告文件名]` 访问
   - 单设备报告可通过 `/static/reports/ui_run/WFGameAI.air/log/[设备目录]/log.html` 访问

2. **修复报告目录**：
   如果发现报告显示异常，可以执行以下操作：
   ```
   cd wfgame-ai-server
   .\fix_report_dirs.bat
   ```

3. **查看详细说明**：
   更多细节说明请参考 `wfgame-ai-server/apps/reports/README.md`

## 注意事项

1. 不要手动删除或移动报告目录中的文件，以免影响报告的正常显示
2. 在生成报告的代码中，已经更新了相关路径引用，请不要修改回旧的路径
3. 涉及到报告功能的代码改动，请确保遵循新的目录结构规范
