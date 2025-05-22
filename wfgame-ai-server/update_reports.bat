@echo off
echo ====================================================
echo WFGame AI 报告系统更新工具
echo ====================================================
echo 此脚本将执行以下操作:
echo 1. 修复报告文件中的链接路径
echo 2. 复制报告文件到静态目录
echo ====================================================
echo.
echo 正在处理...
cd %~dp0
python apps\reports\report_hooks.py --manual
echo.
echo ====================================================
echo 操作完成!
echo.
echo 现在可以通过以下方式访问报告:
echo 1. 概要报告: /static/reports/summary_reports/summary_report_*.html
echo ====================================================
pause
