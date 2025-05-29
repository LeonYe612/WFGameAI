@echo off
:: ================================
:: Description:
:: 定期清理旧的报告文件，防止占用过多磁盘空间
:: Author: WFGame AI Team
:: CreateDate: 2025-05-29
:: ===============================

echo ===================================
echo WFGameAI自动化测试平台 - 报告清理工具
echo ===================================
echo.

:: 设置默认保留天数
set RETENTION_DAYS=30

:: 处理命令行参数
if not "%~1"=="" (
    set RETENTION_DAYS=%~1
)

echo 将清理 %RETENTION_DAYS% 天前的报告文件
echo.

:: 获取脚本所在目录
set SCRIPT_DIR=%~dp0

:: 运行Python脚本清理旧报告
cd /d "%SCRIPT_DIR%"
python cleanup_old_reports.py --days %RETENTION_DAYS%

echo.
echo 清理完成!
echo.
echo 提示: 你可以通过Windows任务计划程序将此批处理设置为每周自动运行。
echo 示例: cleanup_reports.bat 30 (保留30天的报告)
echo.

pause
