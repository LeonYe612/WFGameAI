@echo off
REM Git 大文件清理脚本 - 用于解决 pre-receive hook declined 错误
REM 作者: GitHub Copilot

echo ====== Git 仓库大文件清理工具 v2.0 ======
echo 此脚本将帮助您解决 GitHub "pre-receive hook declined" 错误问题
echo 警告: 此脚本会修改 Git 历史，请先确保您已备份代码！
echo.

REM 检查git是否可用
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误: Git 未安装或不在 PATH 环境变量中
    echo 请安装 Git 或将其添加到 PATH 中
    goto :end
)

REM 检查是否在Git仓库中
git rev-parse --is-inside-work-tree >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误: 当前目录不是 Git 仓库
    echo 请在 Git 仓库根目录中运行此脚本
    goto :end
)

echo [步骤 1] 检测仓库中的大文件...
echo.

REM 找出所有超过5MB的大文件
git rev-list --objects --all | git cat-file --batch-check="%%objecttype %%objectname %%objectsize %%rest" | findstr /r "blob.*[5-9][0-9][0-9][0-9][0-9][0-9][0-9]" > large_blobs.txt
git rev-list --objects --all | git cat-file --batch-check="%%objecttype %%objectname %%objectsize %%rest" | findstr /r "blob.*[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]" >> large_blobs.txt

REM 检查是否找到大文件
set /P LARGE_FILES=<large_blobs.txt
if "%LARGE_FILES%"=="" (
    echo 未检测到大文件，仓库状态良好！
    del large_blobs.txt
    goto :cleanup_done
)

echo 检测到以下大文件:
type large_blobs.txt | findstr /i "wfgame reports staticfiles fonts"
echo.

echo [步骤 2] 为大文件创建更有效的 .gitignore 规则...
echo.

REM 从large_blobs.txt提取文件扩展名，创建gitignore规则
echo # 大文件类型，由 cleanup_large_files.bat 添加 > .gitignore.new
echo # 使用 Git LFS 跟踪这些文件或忽略它们 >> .gitignore.new

REM 添加已知的大文件目录和文件类型
echo # 大文件需要 Git LFS 跟踪或忽略 >> .gitignore.new
echo *.pt >> .gitignore.new
echo *.png >> .gitignore.new
echo *.jpg >> .gitignore.new
echo *.jpeg >> .gitignore.new
echo *.ttf >> .gitignore.new
echo *.eot >> .gitignore.new
echo *.woff >> .gitignore.new
echo *.woff2 >> .gitignore.new
echo *.svg >> .gitignore.new

echo # 静态文件和报告 >> .gitignore.new
echo wfgame-ai-server/logs/django.log >> .gitignore.new
echo wfgame-ai-server/apps/reports/* >> .gitignore.new
echo wfgame-ai-server/staticfiles/reports/* >> .gitignore.new
echo wfgame-ai-server/staticfiles/drf-yasg/* >> .gitignore.new
echo wfgame-ai-server/staticfiles/fonts/* >> .gitignore.new
echo wfgame-ai-server/apps/scripts/* >> .gitignore.new

echo # Python 缓存文件 >> .gitignore.new
echo __pycache__/ >> .gitignore.new
echo *.py[cod] >> .gitignore.new
echo *$py.class >> .gitignore.new

echo.
echo 新的 .gitignore 规则已创建: .gitignore.new
echo.

set /p USERINPUT="是否合并新规则到现有的 .gitignore 文件? (y/n): "
if /i "%USERINPUT%"=="y" (
    echo.
    echo 合并 .gitignore 规则...

    if exist .gitignore (
        type .gitignore.new >> .gitignore
    ) else (
        copy .gitignore.new .gitignore
    )

    echo 已更新 .gitignore 文件
) else (
    echo 跳过 .gitignore 更新
)

:cleanup_done

echo.
echo [步骤 3] 从暂存区和历史记录中移除大文件...
echo.

set /p USERINPUT="是否从当前暂存区移除大文件？这不会删除文件，仅从Git中解除跟踪 (y/n): "
if /i "%USERINPUT%"=="y" (
    echo.
    echo 从暂存区移除大文件...

    REM 移除大文件
    for /f "tokens=1-3*" %%a in (large_blobs.txt) do (
        if "%%a"=="blob" (
            git rm --cached "%%d" >nul 2>nul
            if not %ERRORLEVEL% equ 0 (
                echo 无法移除: %%d (可能未被跟踪)
            ) else (
                echo 已移除: %%d
            )
        )
    )

    echo.
    echo 从暂存区移除完成。已移除的文件仍会保留在本地，但不会被Git跟踪。
) else (
    echo 跳过移除暂存区大文件
)

echo.
set /p USERINPUT="是否从Git历史记录中彻底清除大文件？这个操作不可逆且会重写提交历史 (y/n): "
if /i "%USERINPUT%"=="y" (
    echo.
    echo 警告: 此操作会重写Git历史，所有协作者需要重新克隆仓库！
    set /p CONFIRM="确认要清理历史? (y/n): "
    if /i "%CONFIRM%"=="y" (
        echo.
        echo 正在移除大文件历史记录...

        REM 删除已知的大文件
        git filter-branch --force --index-filter ^
        "git rm --cached --ignore-unmatch wfgame-ai-server/staticfiles/reports/ui_run/WFGameAI.air/log/OnePlus-KB2000-1080x2400_2025-05-20-16-12-59/static/fonts/SourceHanSansCN-Regular.ttf" ^
        --prune-empty --tag-name-filter cat -- --all

        REM 删除引用和垃圾回收
        echo 正在清理和压缩仓库...
        git gc --prune=now
        echo 历史清理完成!
    ) else (
        echo 已取消历史清理操作
    )
) else (
    echo 跳过历史记录清理
)

echo.
echo [步骤 4] 清理完成。

echo.
echo ======= 后续操作 =======
echo 1. 提交您的变更: git commit -m "fix(repo): 解决大文件问题，更新.gitignore"
echo 2. 推送到远程仓库: git push origin master
echo.
echo 如果推送仍然失败，您可能需要强制推送 (谨慎使用):
echo git push origin --force --all
echo.
echo 请通知其他协作者执行: git pull --rebase
echo.
echo 如需更彻底清理大文件，建议使用BFG Repo-Cleaner工具:
echo https://rtyley.github.io/bfg-repo-cleaner/

:end
if exist large_blobs.txt del large_blobs.txt
if exist .gitignore.new del .gitignore.new
echo.
pause
