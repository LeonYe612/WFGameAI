@echo off
REM 执行报告目录结构修复脚本

echo 开始执行报告目录结构修复...

cd /d %~dp0

REM 激活虚拟环境
call activate py39_yolov10

REM 运行修复脚本
python apps/reports/fix_static_path.py

REM 运行报告挂钩生成集成报告
python apps/reports/report_hooks.py --hook

REM 显示完成信息
echo 报告目录结构修复完成！
echo 请重启Django服务器以应用更改。

pause
