"""
数据库初始化脚本
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import DATABASE_URL
from models.tables import Base
from loguru import logger


def init_database():
    """初始化数据库"""
    try:
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(engine)
        logger.info(f"数据库初始化成功: {DATABASE_URL}")
        return engine
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


def get_session():
    """获取数据库会话"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == '__main__':
    init_database()