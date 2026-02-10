"""
Database Session Management

SQLAlchemy session management for Guru Watcher
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.core.config import settings


# ============================================
# Async Engine (for async operations)
# ============================================

# 注意：由于项目使用 Supabase，这里主要提供同步接口
# 如果需要完全异步的 SQLAlchemy，需要配置异步数据库连接

DATABASE_URL = getattr(settings, 'DATABASE_URL', None)

if DATABASE_URL:
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
else:
    # 如果没有配置 DATABASE_URL，使用 Supabase 客户端
    from app.core.db import get_db_client
    SessionLocal = None
    Base = None


def get_db():
    """
    获取数据库会话

    Returns:
        SQLAlchemy Session 或 None
    """
    if SessionLocal:
        return SessionLocal()
    return None


# ============================================
# 便捷导出
# ============================================

__all__ = ["engine", "SessionLocal", "Base", "get_db"]
