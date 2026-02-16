"""
Database Helper Utilities
统一的数据库操作辅助函数，减少重复代码
"""
from typing import Any, Dict, List, Optional
from supabase import Client
from app.core.db import get_db_client


def safe_insert(table_name: str, data: Dict[str, Any]) -> Optional[List[Dict]]:
    """
    安全插入数据到指定表

    Args:
        table_name: 表名
        data: 要插入的数据字典

    Returns:
        插入的数据列表，失败时返回None
    """
    db: Client = get_db_client()
    try:
        result = db.table(table_name).insert(data).execute()
        return result.data if result.data else None
    except Exception as e:
        print(f"[ERROR] Failed to insert into {table_name}: {e}")
        return None


def safe_select(table_name: str, filters: Optional[Dict] = None, order_by: str = "created_at", desc: bool = True) -> Optional[List[Dict]]:
    """
    安全查询指定表的数据

    Args:
        table_name: 表名
        filters: 过滤条件字典
        order_by: 排序字段
        desc: 是否降序排列

    Returns:
        查询结果列表，失败时返回None
    """
    db: Client = get_db_client()
    try:
        query = db.table(table_name).select("*")

        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

        if order_by:
            query = query.order(order_by, desc=desc)

        result = query.execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"[ERROR] Failed to select from {table_name}: {e}")
        return []


def safe_update(table_name: str, data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """
    安全更新指定表的数据

    Args:
        table_name: 表名
        data: 要更新的数据
        filters: 更新条件

    Returns:
        更新成功返回True，否则返回False
    """
    db: Client = get_db_client()
    try:
        query = db.table(table_name)
        for key, value in filters.items():
            query = query.eq(key, value)
        result = query.update(data).execute()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update {table_name}: {e}")
        return False


def safe_delete(table_name: str, filters: Dict[str, Any]) -> bool:
    """
    安全删除指定表的数据

    Args:
        table_name: 表名
        filters: 删除条件

    Returns:
        删除成功返回True，否则返回False
    """
    db: Client = get_db_client()
    try:
        query = db.table(table_name)
        for key, value in filters.items():
            query = query.eq(key, value)
        result = query.delete().execute()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to delete from {table_name}: {e}")
        return False