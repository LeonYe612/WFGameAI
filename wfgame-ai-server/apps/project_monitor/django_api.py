"""
项目监控非Django API接口
用于在独立脚本中记录AI执行数据，避免Django环境依赖
"""
import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Optional, Tuple

# 添加项目根目录到路径，避免导入错误
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置日志
logger = logging.getLogger(__name__)

# 全局变量，用于延迟导入
_database_manager = None
_monitor_service = None

def _get_database_manager():
    """延迟导入数据库管理器，避免循环导入"""
    global _database_manager
    if _database_manager is None:
        try:
            from .database import db_manager
            _database_manager = db_manager
        except Exception as e:
            logger.error(f"导入数据库管理器失败: {e}")
            return None
    return _database_manager

def _get_monitor_service():
    """延迟导入监控服务，避免循环导入"""
    global _monitor_service
    if _monitor_service is None:
        try:
            from .monitor_service import monitor_service
            _monitor_service = monitor_service
        except Exception as e:
            logger.error(f"导入监控服务失败: {e}")
            return None
    return _monitor_service

def log_ai_execution_sync(
    project_name: str,
    button_class: str,
    success: bool,
    scenario: Optional[str] = None,
    detection_time_ms: Optional[int] = None,
    coordinates: Optional[Tuple[float, float]] = None,
    screenshot_path: Optional[str] = None,
    device_id: Optional[str] = None
) -> bool:
    """
    同步方式记录AI执行数据

    Args:
        project_name: 项目名称
        button_class: 按钮类别
        success: 是否成功
        scenario: 场景描述
        detection_time_ms: 检测时间（毫秒）
        coordinates: 坐标 (x, y)
        screenshot_path: 截图路径
        device_id: 设备ID

    Returns:
        bool: 记录是否成功
    """
    try:
        db_manager = _get_database_manager()
        monitor_service = _get_monitor_service()

        if not db_manager or not monitor_service:
            logger.warning("数据库管理器或监控服务未可用，跳过记录")
            return False

        # 获取数据库会话
        db = db_manager.get_session()

        try:
            # 查找项目
            from .models import Project
            project = db.query(Project).filter(Project.name == project_name).first()
            if not project:
                logger.warning(f"项目不存在: {project_name}")
                return False

            # 构建日志数据
            log_data = {
                'project_id': project.id,
                'button_class': button_class,
                'scenario': scenario,
                'success': success,
                'detection_time_ms': detection_time_ms,
                'device_id': device_id,
                'screenshot_path': screenshot_path
            }

            # 添加坐标信息
            if coordinates:
                log_data['coordinates_x'] = coordinates[0]
                log_data['coordinates_y'] = coordinates[1]

            # 记录执行日志
            execution_log = monitor_service.log_execution(db, log_data)

            logger.info(f"成功记录AI执行: {project_name}.{button_class} - {'成功' if success else '失败'}")
            return True

        except Exception as e:
            logger.error(f"记录AI执行数据失败: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    except Exception as e:
        logger.error(f"记录AI执行失败: {e}")
        return False

# 异步版本的API
async def log_ai_execution(
    project_name: str,
    button_class: str,
    success: bool,
    scenario: Optional[str] = None,
    detection_time_ms: Optional[int] = None,
    coordinates: Optional[Tuple[float, float]] = None,
    screenshot_path: Optional[str] = None,
    device_id: Optional[str] = None
) -> bool:
    """
    异步方式记录AI执行数据
    在独立线程中执行同步操作，避免阻塞主线程
    """
    try:
        # 在线程池中执行同步操作
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            log_ai_execution_sync,
            project_name,
            button_class,
            success,
            scenario,
            detection_time_ms,
            coordinates,
            screenshot_path,
            device_id
        )
        return result
    except Exception as e:
        logger.error(f"异步记录AI执行失败: {e}")
        return False

# 向后兼容的函数别名
log_detection_result = log_ai_execution_sync

# 测试函数
def test_api():
    """测试API功能"""
    print("测试项目监控API...")
    print("注意：此测试需要先有真实项目数据才能运行")
    print("如果没有项目数据，将显示'无数据'")

    # 不创建硬编码数据，仅测试API连接
    try:
        from .database import db_manager
        db_manager.init_database()
        print("✓ 数据库连接测试成功")
        return True
    except Exception as e:
        print(f"✗ API测试失败: {e}")
        return False

if __name__ == "__main__":
    # 直接运行此文件进行测试
    test_api()