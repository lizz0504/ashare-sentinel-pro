"""
Core module initialization
"""

from app.core.config import settings
from app.core.db import db_client, get_db_client

__all__ = ["settings", "db_client", "get_db_client"]
