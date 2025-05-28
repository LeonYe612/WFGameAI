#!/usr/bin/env python3
"""
Verification script to check if the app is actually stopped after running the stop script.
"""

from app_lifecycle_manager import AppLifecycleManager

def main():
    print("开始验证应用停止状态...")

    try:
        manager = AppLifecycleManager()
        package_name = "com.qyfhl.qxzf"

        # Check both connected devices
        devices = ["5c41023b", "CWM0222215003786"]

        for device_id in devices:
            print(f"\n检查设备 {device_id}:")

            # Check if app is running using our fixed method
            print(f"正在检查应用 {package_name} 是否运行...")
            is_running = manager.check_app_running(device_id, package_name)
            print(f"check_app_running 结果: {is_running}")

            if is_running:
                print(f"❌ 应用 {package_name} 仍在运行!")
            else:
                print(f"✅ 应用 {package_name} 已成功停止")

            # Also get list of running apps to double-check
            print("获取运行应用列表...")
            running_apps = manager.get_running_apps(device_id)
            print(f"发现 {len(running_apps)} 个运行应用")

            if package_name in running_apps:
                print(f"❌ 在运行应用列表中发现 {package_name}")
            else:
                print(f"✅ 运行应用列表中未发现 {package_name}")

    except Exception as e:
        print(f"验证过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
