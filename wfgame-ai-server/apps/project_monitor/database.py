"""
数据库连接和初始化
"""
import os
import configparser
import logging
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .models import Base

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_url: Optional[str] = None):
        if db_url is None:
            # 从config.ini读取MySQL配置
            db_url = self._load_mysql_config()

        self.db_url = db_url
        self.engine = create_engine(
            db_url,
            echo=False,  # 设置为True可以看到SQL语句
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=10,
            max_overflow=20
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def _load_mysql_config(self) -> str:
        """从config.ini加载MySQL配置"""
        try:
            # 查找config.ini文件
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config.ini')
            if not os.path.exists(config_path):
                logger.warning(f"配置文件不存在: {config_path}, 使用默认SQLite")
                # 回退到SQLite
                db_dir = os.path.join(os.path.dirname(__file__), 'data')
                os.makedirs(db_dir, exist_ok=True)
                return f"sqlite:///{os.path.join(db_dir, 'project_monitor.db')}"

            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')

            # 读取MySQL配置
            if 'mysql' in config:
                mysql_config = config['mysql']
                host = mysql_config.get('host', 'localhost')
                port = mysql_config.get('port', '3306')
                username = mysql_config.get('username', 'root')
                password = mysql_config.get('password', '')
                database = mysql_config.get('database', 'wfgame_ai')

                db_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
                logger.info(f"使用MySQL数据库: {host}:{port}/{database}")
                return db_url
            else:
                logger.warning("config.ini中未找到mysql配置，使用默认SQLite")
                # 回退到SQLite
                db_dir = os.path.join(os.path.dirname(__file__), 'data')
                os.makedirs(db_dir, exist_ok=True)
                return f"sqlite:///{os.path.join(db_dir, 'project_monitor.db')}"

        except Exception as e:
            logger.error(f"加载MySQL配置失败: {e}, 使用默认SQLite")
            # 回退到SQLite
            db_dir = os.path.join(os.path.dirname(__file__), 'data')
            os.makedirs(db_dir, exist_ok=True)
            return f"sqlite:///{os.path.join(db_dir, 'project_monitor.db')}"

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
