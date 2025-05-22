@echo off
REM 修复报告路径，确保系统能够找到报告文件
echo 开始修复报告路径...
python fix_report_paths.py
echo 报告路径修复完成

REM 重启服务器以生效
echo 重启服务器以应用更改...
echo 请手动重启开发服务器或按Ctrl+C终止然后重新启动服务器

pause
