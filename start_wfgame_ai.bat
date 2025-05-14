@echo off
REM ====================================
REM WFGame AI自动化测试平台启动脚本
REM 版本: 1.0
REM ====================================

setlocal enabledelayedexpansion

echo.
echo  ██╗    ██╗███████╗ ██████╗  █████╗ ███╗   ███╗███████╗     █████╗ ██╗
echo  ██║    ██║██╔════╝██╔════╝ ██╔══██╗████╗ ████║██╔════╝    ██╔══██╗██║
echo  ██║ █╗ ██║█████╗  ██║  ███╗███████║██╔████╔██║█████╗      ███████║██║
echo  ██║███╗██║██╔══╝  ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝      ██╔══██║██║
echo  ╚███╔███╔╝██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗    ██║  ██║██║
echo   ╚══╝╚══╝ ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝    ╚═╝  ╚═╝╚═╝
echo.
echo  自动化测试平台服务启动工具 v1.0
echo.

REM 获取脚本所在目录作为项目根目录
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

REM 检查是否存在Python和Node.js
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到Python。请确保已安装Python并添加到PATH环境变量中。
    goto :error
)

where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到Node.js。请确保已安装Node.js并添加到PATH环境变量中。
    goto :error
)

where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到npm。请确保已正确安装Node.js。
    goto :error
)

REM 检查后端目录是否存在
if not exist "%ROOT_DIR%wfgame-ai-server" (
    echo [错误] 后端目录不存在: %ROOT_DIR%wfgame-ai-server
    goto :error
)

REM 检查前端目录是否存在
if not exist "%ROOT_DIR%wfgame-ai-web" (
    echo [错误] 前端目录不存在: %ROOT_DIR%wfgame-ai-web
    goto :error
)

REM 检查前端依赖是否已安装
if not exist "%ROOT_DIR%wfgame-ai-web\node_modules" (
    echo [信息] 前端依赖不存在，正在安装依赖...
    cd /d "%ROOT_DIR%wfgame-ai-web"
    call npm install
    if %ERRORLEVEL% NEQ 0 (
        echo [错误] 前端依赖安装失败
        goto :error
    )
    echo [信息] 前端依赖安装完成
)

REM 创建日志目录
if not exist "%ROOT_DIR%logs" mkdir "%ROOT_DIR%logs"

echo.
echo [信息] 正在启动后端服务...
echo.

REM 启动后端服务
start "WFGame AI 后端服务" cmd /c "cd /d "%ROOT_DIR%wfgame-ai-server" && python manage.py runserver 0.0.0.0:8000 > "%ROOT_DIR%logs\backend.log" 2>&1"

echo [信息] 正在启动前端服务...
echo.

REM 启动前端服务
start "WFGame AI 前端服务" cmd /c "cd /d "%ROOT_DIR%wfgame-ai-web" && npm run serve > "%ROOT_DIR%logs\frontend.log" 2>&1"

REM 等待服务启动
echo [信息] 服务启动中，请稍候...
timeout /t 15 /nobreak > nul

REM 打开浏览器
echo [信息] 正在打开浏览器...
start http://localhost:8080

echo.
echo [成功] 服务已启动！
echo.
echo 访问地址:
echo - 前端: http://localhost:8080
echo - 后端: http://localhost:8000
echo - API文档: http://localhost:8000/api/docs/
echo.
echo 服务日志位置:
echo - 后端日志: %ROOT_DIR%logs\backend.log
echo - 前端日志: %ROOT_DIR%logs\frontend.log
echo.
echo 按任意键停止所有服务...
pause > nul

REM 停止所有服务
echo.
echo [信息] 正在停止服务...

REM 使用taskkill命令结束所有相关进程
taskkill /fi "WINDOWTITLE eq WFGame AI 后端服务*" /f > nul 2>&1
taskkill /fi "WINDOWTITLE eq WFGame AI 前端服务*" /f > nul 2>&1

echo [成功] 服务已停止
goto :eof

:error
echo.
echo 启动失败！请查看上面的错误信息。
pause
exit /b 1 