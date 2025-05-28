#!/usr/bin/env python3
"""
测试Windows兼容性修复后的应用生命周期管理器
"""
import logging
from app_lifecycle_manager import AppLifecycleManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_app_lifecycle_windows_compatibility():
    """测试Windows兼容性修复"""
    logger.info("开始测试Windows兼容性修复...")

    # 创建应用生命周期管理器实例
    app_manager = AppLifecycleManager()

    # 测试设备ID（替换为你的实际设备ID）
    device_id = "5c41023b"  # 从之前的调试信息中获取的设备ID
    test_package_name = "com.qyfhl.qxzf"  # 测试包名

    logger.info(f"测试设备: {device_id}")
    logger.info(f"测试包名: {test_package_name}")

    try:
        # 1. 测试应用状态检查
        logger.info("=" * 50)
        logger.info("测试1: 检查应用运行状态")
        is_running = app_manager.check_app_running(test_package_name, device_id)
        logger.info(f"应用运行状态: {'运行中' if is_running else '未运行'}")

        # 2. 测试启动应用
        logger.info("=" * 50)
        logger.info("测试2: 启动应用")
        if not is_running:
            logger.info("应用未运行，尝试启动...")
            start_result = app_manager.start_app(test_package_name, device_id)
            logger.info(f"启动结果: {'成功' if start_result else '失败'}")

            # 启动后再次检查状态
            is_running_after_start = app_manager.check_app_running(test_package_name, device_id)
            logger.info(f"启动后应用状态: {'运行中' if is_running_after_start else '未运行'}")
        else:
            logger.info("应用已在运行，跳过启动测试")

        # 3. 测试获取运行中的应用列表
        logger.info("=" * 50)
        logger.info("测试3: 获取运行中的应用列表")
        running_apps = app_manager.get_running_apps(device_id)
        logger.info(f"检测到 {len(running_apps)} 个运行中的应用")

        # 显示前10个应用
        for i, app in enumerate(running_apps[:10]):
            logger.info(f"  {i+1}. {app}")

        if len(running_apps) > 10:
            logger.info(f"  ... 还有 {len(running_apps) - 10} 个应用")

        # 检查目标应用是否在列表中
        if test_package_name in running_apps:
            logger.info(f"✓ 目标应用 {test_package_name} 在运行列表中")
        else:
            logger.info(f"✗ 目标应用 {test_package_name} 不在运行列表中")

        logger.info("=" * 50)
        logger.info("Windows兼容性测试完成！")

    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_app_lifecycle_windows_compatibility()
