@echo off
echo =====================================
echo WFGameAI 设备预处理管理器 - 增强版
echo =====================================
echo.

cd /d "%~dp0"

:menu
echo 请选择操作：
echo 1. 运行完整设备检查和预处理（推荐）
echo 2. 仅运行USB连接检查
echo 3. 仅生成设备测试报告
echo 4. 查看帮助
echo 5. 退出
echo.
set /p choice=请输入选项 (1-5):

if "%choice%"=="1" goto full_check
if "%choice%"=="2" goto usb_check
if "%choice%"=="3" goto report_only
if "%choice%"=="4" goto help
if "%choice%"=="5" goto exit
echo 无效选项，请重新选择
goto menu

:full_check
echo.
echo 🔄 运行完整设备检查和预处理...
python enhanced_device_preparation_manager.py
goto end

:usb_check
echo.
echo 🔍 运行USB连接检查...
python usb_connection_checker.py
goto end

:report_only
echo.
echo 📊 生成设备测试报告...
python enhanced_device_preparation_manager.py --report
goto end

:help
echo.
echo =====================================
echo 帮助信息
echo =====================================
echo.
echo 选项1: 完整检查
echo   - USB连接状态检查
echo   - 设备预处理和配置
echo   - RSA密钥授权设置
echo   - 无线连接配置
echo   - 功能测试
echo   - 生成详细报告表格
echo.
echo 选项2: USB检查
echo   - 仅检查USB连接状态
echo   - 显示设备连接问题
echo   - 提供解决方案指导
echo.
echo 选项3: 报告生成
echo   - 快速检查所有设备
echo   - 生成测试结果表格
echo   - 不进行设备配置修改
echo.
goto menu

:end
echo.
echo 按任意键继续...
pause >nul
goto menu

:exit
echo 退出程序
exit /b 0
