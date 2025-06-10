"""
项目监控系统初始化脚本
遵循严格的无假数据规则
"""
import os
import sys
import logging

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from apps.project_monitor.database import init_app_database, db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_project_environment():
    """设置项目监控环境（不创建硬编码项目）"""
    try:
        # 仅初始化数据库，不创建任何硬编码项目
        if not init_app_database():
            logger.error("数据库初始化失败")
            return False

        logger.info("项目监控环境初始化成功")
        logger.info("注意：严格遵循无假数据规则，没有创建任何硬编码项目")
        logger.info("所有数据将通过用户真实操作产生")
        return True

    except Exception as e:
        logger.error(f"设置项目环境失败: {e}")
        return False

def main():
    """主函数 - 遵循无假数据规则"""
    print("=== 项目监控系统初始化 ===")

    # 设置项目环境（仅初始化数据库）
    if not setup_project_environment():
        logger.error("项目环境设置失败")
        sys.exit(1)

    logger.info("项目监控系统初始化完成！")
    logger.info("数据库已初始化，等待用户真实操作产生数据")
    logger.info("注意：严格遵循无假数据规则，没有创建任何硬编码项目或示例数据")
    logger.info("")
    logger.info("使用方法:")
    logger.info("1. 启动Django服务器")
    logger.info("2. 通过Web界面创建真实项目")
    logger.info("3. 在代码中调用 log_ai_execution() 函数记录AI执行结果")

if __name__ == "__main__":
    main()
