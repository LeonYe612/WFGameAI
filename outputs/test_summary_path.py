import os
import sys
from datetime import datetime
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from replay_script import run_summary

# 准备测试数据 - 使用实际的设备目录结构
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
device_log_dir = os.path.join(base_dir, "outputs", "WFGameAI-reports", "ui_run", "WFGameAI.air", "log")

# 确保测试目录存在
os.makedirs(device_log_dir, exist_ok=True)

# 创建测试设备目录
test_device_name = "Test-Device-1080x2400_2025-04-18-15-30-00"
test_device_dir = os.path.join(device_log_dir, test_device_name)
os.makedirs(test_device_dir, exist_ok=True)

# 创建测试log.html文件
test_log_html = os.path.join(test_device_dir, "log.html")
with open(test_log_html, "w") as f:
    f.write("<html><body>测试设备报告</body></html>")

# 准备测试数据
test_data = {
    'tests': {
        'Test-Device': test_log_html
    }
}

# 运行汇总报告生成
print(f"生成测试汇总报告...")
print(f"测试数据: {json.dumps(test_data, indent=2)}")
summary_report_path = run_summary(test_data)

if summary_report_path:
    print(f"✅ 汇总报告生成成功: {summary_report_path}")
    
    # 读取生成的HTML文件，检查链接
    with open(summary_report_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 检查链接
    import re
    links = re.findall(r'<a href="([^"]+)"', html_content)
    print(f"报告中的链接: {links}")
    
    # 打开报告
    print("请在浏览器中打开报告，检查设备报告链接是否正确")
    os.system(f"open {summary_report_path}")
else:
    print("❌ 汇总报告生成失败") 