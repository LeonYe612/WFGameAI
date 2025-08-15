"""
数据库连接和初始化
"""
import os
import logging
import configparser
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .models import Base
from django.conf import settings


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_url: Optional[str] = None):
        if db_url is None:
            # 从config.ini读取MySQL配置
            config = settings.CFG._config
            if 'database' in config:
                host = config.get('database', 'host', fallback='127.0.0.1')
                username = config.get('database', 'username', fallback='root')
                password = config.get('database', 'password', fallback='qa123456')
                dbname = config.get('database', 'dbname', fallback='gogotest_data')
                port = config.get('database', 'port', fallback='3306')

                db_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{dbname}?charset=utf8mb4"
                logger.info(f"使用MySQL数据库: {host}:{port}/{dbname}")
            else:
                raise ValueError("config.ini中缺少database配置")

        self.db_url = db_url
        self.engine = create_engine(
            db_url,
            echo=False,  # 设置为True可以看到SQL语句
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def init_database(self):
        """初始化数据库表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("数据库表初始化成功")
            return True
        except SQLAlchemyError as e:
            logger.error(f"数据库初始化失败: {e}")
            return False

    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()

    def check_connection(self):
        """检查数据库连接"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("数据库连接正常")
            return True
        except SQLAlchemyError as e:
            logger.error(f"数据库连接失败: {e}")
            return False

# 全局数据库管理器实例
db_manager = DatabaseManager()

def get_db():
    """FastAPI依赖注入函数"""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()

def init_app_database():
    """应用启动时初始化数据库"""
    logger.info("开始初始化项目监控数据库...")

    if not db_manager.check_connection():
        logger.error("数据库连接失败，无法继续")
        return False

    if not db_manager.init_database():
        logger.error("数据库表创建失败")
        return False

    logger.info("项目监控数据库初始化完成")
    return True

if __name__ == "__main__":
    # 直接运行此文件来初始化数据库
    init_app_database()
