#!/usr/bin/env python3
"""
验证AppLifecycleManager修复的核心功能
"""

import sys
import subprocess
import time

# 添加路径
sys.path.insert(0, 'c:\\Users\\Administrator\\PycharmProjects\\WFGameAI\\wfgame-ai-server\\apps\\scripts')

try:
    from app_lifecycle_manager import AppLifecycleManager, AppTemplate

    def verify_check_app_running():
        """验证_check_app_running方法的修复"""
        print("=== 验证应用检查修复 ===")

        # 创建管理器
        manager = AppLifecycleManager()

        # 获取card2prepare模板
        template = manager.get_app_template('card2prepare')
        if not template:
            print("❌ 未找到card2prepare模板")
            return False

        print(f"✅ 找到模板: {template.name}")
        print(f"   包名: {template.package_name}")
        print(f"   检查命令: {template.check_commands}")

        # 检查连接的设备
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            devices = []
            for line in result.stdout.strip().split('\n')[1:]:
                if 'device' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)

            if not devices:
                print("❌ 没有连接的设备")
                return False

            print(f"✅ 连接的设备: {devices}")

            # 测试第一个设备
            device_id = devices[0]
            print(f"\n--- 测试设备: {device_id} ---")

            # 手动执行pidof命令，模拟检查逻辑
            print("1. 执行原始pidof命令...")
            cmd = f"adb -s {device_id} shell pidof {template.package_name}"
            print(f"   命令: {cmd}")

            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=10)
            print(f"   返回码: {result.returncode}")
            print(f"   输出: '{result.stdout.strip()}'")
            print(f"   错误: '{result.stderr.strip()}'")

            # 测试修复后的检查方法
            print("\n2. 测试修复后的_check_app_running方法...")
            is_running = manager._check_app_running(template, device_id)
            print(f"   检查结果: {'运行中' if is_running else '未运行'}")

            # 如果未运行，尝试启动然后再检查
            if not is_running:
                print("\n3. 尝试启动应用后再检查...")
                success = manager.start_app('card2prepare', device_id)
                print(f"   启动结果: {'成功' if success else '失败'}")

                if success:
                    print("   等待2秒后再次检查...")
                    time.sleep(2)
                    is_running_after = manager._check_app_running(template, device_id)
                    print(f"   启动后检查结果: {'运行中' if is_running_after else '未运行'}")

                    # 清理：停止应用
                    print("   清理：停止应用...")
                    manager.stop_app('card2prepare', device_id)

                    return is_running_after

            return is_running

        except Exception as e:
            print(f"❌ 测试出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def main():
        """主函数"""
        print("开始验证AppLifecycleManager修复...")

        success = verify_check_app_running()

        if success:
            print("\n🎉 修复验证成功！应用检查功能正常工作")
        else:
            print("\n⚠️  修复验证失败，可能需要进一步调试")

        return success    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"❌ 导入错误: {e}")
except Exception as e:
    print(f"❌ 执行错误: {e}")
    import traceback
    traceback.print_exc()

# 确保脚本被执行
if __name__ == "__main__":
    try:
        from app_lifecycle_manager import AppLifecycleManager, AppTemplate
        success = verify_check_app_running()
        if success:
            print("\n🎉 修复验证成功！应用检查功能正常工作")
        else:
            print("\n⚠️  修复验证失败，可能需要进一步调试")
    except Exception as e:
        print(f"❌ 总体执行错误: {e}")
        import traceback
        traceback.print_exc()
