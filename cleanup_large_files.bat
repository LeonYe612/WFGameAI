@echo off
echo 这个批处理文件将清理Git仓库中的大文件
echo 警告：这将重写Git历史，所有协作者需要重新克隆仓库！
echo.
pause

REM 移除大文件历史记录
echo 正在移除大文件历史记录...

REM 删除已跟踪的大文件
git filter-branch --force --index-filter ^
"git rm --cached --ignore-unmatch wfgame-ai-server/staticfiles/reports/ui_run/WFGameAI.air/log/OnePlus-KB2000-1080x2400_2025-05-20-16-12-59/static/fonts/SourceHanSansCN-Regular.ttf" ^
--prune-empty --tag-name-filter cat -- --all

REM 删除引用和垃圾回收
echo 正在清理和压缩仓库...
git gc --prune=now

REM 强制推送更改
echo 完成！现在您可以使用以下命令强制推送到远程仓库：
echo git push origin --force --all
echo.
echo 后续操作：
echo 1. 确保添加了 .gitignore 规则
echo 2. 运行 git push origin --force --all
echo 3. 通知其他协作者执行 git pull --rebase

pause
