@echo off
REM 重命名不再使用的目录，添加_useless后缀
REM 运行此脚本后，用户可以手动检查并删除这些目录

echo 开始重命名不再使用的目录，添加_useless后缀...

cd /d %~dp0

REM 重命名不再使用的目录
REM 1. 旧的reports目录
IF EXIST "apps\staticfiles\reports" (
    echo 重命名 apps\staticfiles\reports 为 apps\staticfiles\reports_useless
    ren "apps\staticfiles\reports" "reports_useless"
)

REM 2. 旧的ui_run目录
IF EXIST "apps\staticfiles\ui_run" (
    echo 重命名 apps\staticfiles\ui_run 为 apps\staticfiles\ui_run_useless
    ren "apps\staticfiles\ui_run" "ui_run_useless"
)

REM 3. outputs目录中旧的报告目录
IF EXIST "outputs\WFGameAI-reports" (
    echo 重命名 outputs\WFGameAI-reports 为 outputs\WFGameAI-reports_useless
    ren "outputs\WFGameAI-reports" "WFGameAI-reports_useless"
)

REM 4. outputs下的其他可能被引用为报告目录的文件夹
IF EXIST "outputs\device_reports" (
    echo 重命名 outputs\device_reports 为 outputs\device_reports_useless
    ren "outputs\device_reports" "device_reports_useless"
)

echo.
echo 目录重命名完成！
echo 请手动检查以下目录是否确实不再使用，确认后可以手动删除：
echo - apps\staticfiles\reports_useless
echo - apps\staticfiles\ui_run_useless
echo - outputs\WFGameAI-reports_useless
echo - outputs\device_reports_useless
echo.

pause
