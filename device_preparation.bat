@echo off
:: WFGameAI设备预处理脚本 - Windows版本
:: 解决设备连接、权限、锁屏等问题，特别是断电重连后的ADB授权问题

echo =====================================
echo WFGameAI 设备预处理管理器
echo =====================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

:: 检查ADB是否可用
adb version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到ADB，请确保Android SDK已安装并添加到PATH
    pause
    exit /b 1
)

:: 获取脚本所在目录
set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%device_preparation_manager.py

:: 检查Python脚本是否存在
if not exist "%PYTHON_SCRIPT%" (
    echo 错误: 找不到device_preparation_manager.py
    echo 请确保脚本位于: %PYTHON_SCRIPT%
    pause
    exit /b 1
)

:: 显示菜单
:menu
echo.
echo 请选择操作：
echo 1. 预处理所有连接的设备（推荐）
echo 2. 重新连接指定设备
echo 3. 查看设备预处理报告
echo 4. 手动配置RSA密钥授权
echo 5. 测试设备连接状态
echo 6. 退出
echo.
set /p choice="请输入选项 (1-6): "

if "%choice%"=="1" goto prepare_all
if "%choice%"=="2" goto reconnect_device
if "%choice%"=="3" goto show_report
if "%choice%"=="4" goto manual_rsa
if "%choice%"=="5" goto test_connection
if "%choice%"=="6" goto exit
echo 无效选项，请重新选择
goto menu

:prepare_all
echo.
echo 开始预处理所有设备...
echo =====================================
python "%PYTHON_SCRIPT%"
if errorlevel 1 (
    echo.
    echo 预处理过程中出现错误！
) else (
    echo.
    echo 设备预处理完成！
)
echo.
pause
goto menu

:reconnect_device
echo.
echo 当前连接的设备：
adb devices
echo.
set /p device_id="请输入要重连的设备ID: "
if "%device_id%"=="" (
    echo 设备ID不能为空
    goto reconnect_device
)

echo.
echo 尝试重新连接设备: %device_id%
python "%PYTHON_SCRIPT%" --reconnect "%device_id%"
echo.
pause
goto menu

:show_report
echo.
echo 设备预处理报告：
echo =====================================
python "%PYTHON_SCRIPT%" --report
echo.
pause
goto menu

:manual_rsa
echo.
echo 手动配置RSA密钥授权
echo =====================================
echo.

:: 检查ADB密钥是否存在
set ADB_KEY_DIR=%USERPROFILE%\.android
if not exist "%ADB_KEY_DIR%\adbkey" (
    echo 正在生成ADB RSA密钥...
    adb kill-server
    adb start-server
    timeout /t 3 /nobreak >nul
)

if exist "%ADB_KEY_DIR%\adbkey.pub" (
    echo ADB RSA公钥位置: %ADB_KEY_DIR%\adbkey.pub
    echo.
    echo RSA公钥内容：
    type "%ADB_KEY_DIR%\adbkey.pub"
    echo.
    echo 该密钥已自动保存，设备授权后将持久生效
) else (
    echo 错误: 无法生成ADB RSA密钥
)

echo.
echo 对于root设备，可将公钥复制到: /data/misc/adb/adb_keys
echo 对于非root设备，在USB调试授权对话框中点击"允许"即可
echo.
pause
goto menu

:test_connection
echo.
echo 测试设备连接状态
echo =====================================
echo.
echo 正在检查ADB服务器状态...
adb kill-server
adb start-server

echo.
echo 当前连接的设备：
adb devices -l

echo.
echo 设备详细信息：
for /f "tokens=1" %%i in ('adb devices ^| find /c "device"') do set device_count=%%i
echo 检测到 %device_count% 个已授权设备

:: 显示每个设备的详细信息
echo.
echo 设备列表详情：
for /f "skip=1 tokens=1,2" %%a in ('adb devices') do (
    if "%%b"=="device" (
        echo.
        echo 设备ID: %%a
        echo 状态: %%b
        adb -s %%a shell getprop ro.product.model 2>nul | findstr /r "." && (
            for /f %%m in ('adb -s %%a shell getprop ro.product.model') do echo 型号: %%m
        )
        adb -s %%a shell getprop ro.build.version.release 2>nul | findstr /r "." && (
            for /f %%v in ('adb -s %%a shell getprop ro.build.version.release') do echo Android版本: %%v
        )
        echo ---
    ) else if "%%b"=="unauthorized" (
        echo.
        echo 设备ID: %%a
        echo 状态: 未授权 - 请在设备上允许USB调试
        echo ---
    )
)

echo.
pause
goto menu

:exit
echo 退出设备预处理管理器
exit /b 0
