"""
项目监控系统初始化脚本
"""
import os
import sys
import logging
from sqlalchemy.orm import Session

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from apps.project_monitor.database import init_app_database, db_manager
from apps.project_monitor.monitor_service import monitor_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_warframe_project():
    """设置Warframe项目"""
    try:
        # 初始化数据库
        if not init_app_database():
            logger.error("数据库初始化失败")
            return False

        # 创建Warframe项目
        db: Session = db_manager.get_session()
        try:
            # 检查项目是否已存在
            from apps.project_monitor.models import Project
            existing_project = db.query(Project).filter(Project.name == "Warframe").first()

            if existing_project:
                logger.info("Warframe项目已存在，跳过创建")
                return True

            # 项目配置文件路径
            yaml_path = os.path.join(
                os.path.dirname(__file__),
                "data",
                "warframe_project.yaml"
            )

            if not os.path.exists(yaml_path):
                logger.error(f"项目配置文件不存在: {yaml_path}")
                return False

            # 创建项目
            project = monitor_service.create_project(
                db=db,
                name="Warframe",
                yaml_path=yaml_path,
                description="Warframe游戏自动化AI检测监控项目"
            )

            logger.info(f"成功创建Warframe项目，ID: {project.id}")
            return True

        except Exception as e:
            logger.error(f"创建Warframe项目失败: {e}")
            return False
        finally:
            db.close()

    except Exception as e:
        logger.error(f"设置Warframe项目失败: {e}")
        return False

def create_sample_data():
    """创建一些示例数据用于测试"""
    try:
        db: Session = db_manager.get_session()
        from apps.project_monitor.models import Project
        from datetime import datetime, timedelta
        import random

        # 获取Warframe项目
        project = db.query(Project).filter(Project.name == "Warframe").first()
        if not project:
            logger.error("Warframe项目不存在")
            return False

        # 按钮类列表（基于之前的分析结果）
        button_classes = [
            ("navigation-fight", 0.0),  # 0%成功率
            ("hint-guide", 1.0),        # 100%成功率
            ("operation-challenge", 1.0), # 100%成功率
            ("operation-confirm", 1.0),  # 100%成功率
            ("system-skip", 1.0)        # 100%成功率
        ]

        logger.info("开始创建示例数据...")

        # 为每个按钮类创建过去7天的模拟数据
        for button_class, base_success_rate in button_classes:
            for day in range(7):
                # 每天10-30次执行
                daily_executions = random.randint(10, 30)
                date = datetime.utcnow() - timedelta(days=day)

                for _ in range(daily_executions):
                    # 根据基础成功率添加一些随机性
                    success_rate = base_success_rate
                    if success_rate > 0:
                        success_rate = max(0.8, min(1.0, base_success_rate + random.uniform(-0.1, 0.1)))

                    success = random.random() < success_rate
                    detection_time = random.randint(200, 1500) if success else random.randint(500, 3000)

                    # 创建执行记录
                    log_data = {
                        'project_id': project.id,
                        'button_class': button_class,
                        'scenario': f'scenario_{random.randint(1, 5)}',
                        'success': success,
                        'detection_time_ms': detection_time,
                        'coordinates_x': random.uniform(100, 1000),
                        'coordinates_y': random.uniform(100, 600),
                        'device_id': 'test_device',
                        'executed_at': date + timedelta(
                            hours=random.randint(8, 22),
                            minutes=random.randint(0, 59),
                            seconds=random.randint(0, 59)
                        )
                    }

                    monitor_service.log_execution(db, log_data)

        logger.info("示例数据创建完成")
        return True

    except Exception as e:
        logger.error(f"创建示例数据失败: {e}")
        return False
    finally:
        db.close()

def main():
    """主函数"""
    logger.info("开始设置项目监控系统...")

    # 设置Warframe项目
    if not setup_warframe_project():
        logger.error("Warframe项目设置失败")
        sys.exit(1)

    # 询问是否创建示例数据
    create_samples = input("是否创建示例数据用于测试? (y/N): ").lower() == 'y'
    if create_samples:
        if not create_sample_data():
            logger.error("示例数据创建失败")
        else:
            logger.info("示例数据创建成功")

    logger.info("项目监控系统设置完成！")
    logger.info("数据库文件位置: apps/project_monitor/data/project_monitor.db")
    logger.info("项目配置文件: apps/project_monitor/data/warframe_project.yaml")
    logger.info("")
    logger.info("使用方法:")
    logger.info("1. 启动FastAPI服务器")
    logger.info("2. 访问 http://localhost:8000/api/project-monitor/dashboard 查看监控面板")
    logger.info("3. 在代码中调用 log_ai_execution() 函数记录AI执行结果")

if __name__ == "__main__":
    main()
