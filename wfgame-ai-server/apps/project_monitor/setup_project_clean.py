#!/usr/bin/env python3
"""
项目监控系统初始化脚本
遵循编码规范：不创建任何硬编码或假数据
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

def setup_project_environment():
    """设置项目监控环境（不创建硬编码项目）"""
    try:
        # 仅初始化数据库，不创建任何硬编码项目
        if not init_app_database():
            logger.error("数据库初始化失败")
            return False

        logger.info("项目监控环境初始化成功")
        logger.info("注意：没有创建任何硬编码项目，数据将通过用户真实操作产生")
        return True

    except Exception as e:
        logger.error(f"设置项目环境失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始设置项目监控系统...")

    # 设置项目环境
    if not setup_project_environment():
        logger.error("项目环境设置失败")
        sys.exit(1)

    logger.info("项目监控系统设置完成！")
    logger.info("数据库已初始化，等待用户真实数据")
    logger.info("")
    logger.info("使用方法:")
    logger.info("1. 启动Django服务器")
    logger.info("2. 访问项目监控页面查看监控面板")
    logger.info("3. 在代码中调用 log_ai_execution() 函数记录AI执行结果")
    logger.info("4. 所有数据将通过用户的真实操作自动产生")

if __name__ == "__main__":
    main()
