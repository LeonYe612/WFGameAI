@echo off
cd /d "c:\Users\Administrator\PycharmProjects\WFGameAI\wfgame-ai-server"
echo ========================================
echo 项目监控系统测试套件
echo ========================================
echo.

echo 1. 运行基础测试...
python basic_test.py
echo.

echo 2. 运行状态检查...
python status_check.py
echo.

echo 3. 运行完整集成测试...
python complete_integration_test.py
echo.

echo 4. 运行最终验证...
python final_verification.py
echo.

echo ========================================
echo 测试完成
echo ========================================
pause
