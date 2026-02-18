"""
Supabase 数据库连接工具

替代 MySQL，使用 Supabase 作为统一的数据存储方案
"""

import os
from supabase import create_client, Client
from typing import Optional

from app.core.config import settings


# Supabase 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # 使用 service_role_key 有完整权限

# 调试：打印配置
import sys
print(f"[DEBUG Supabase] URL={SUPABASE_URL}", file=sys.stderr)


def get_supabase_client() -> Client:
    """
    获取 Supabase 客户端（用于后端操作）

    使用方式:
        client = get_supabase_client()
        response = client.table('reports').select("*").execute()
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials not configured in environment variables")

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def test_supabase_connection() -> bool:
    """测试 Supabase 连接"""
    try:
        client = get_supabase_client()
        # 尝试查询 reports 表
        response = client.table('reports').select("id").limit(1).execute()
        print(f"[DEBUG] Supabase connection test: OK", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[DEBUG] Supabase connection test failed: {e}", file=sys.stderr)
        return False


# 上下文管理器版本（兼容旧的 MySQL 接口）
class SupabaseConnection:
    """Supabase 连接上下文管理器（模拟 MySQL 连接接口）"""

    def __init__(self):
        self.client = None

    def __enter__(self):
        self.client = get_supabase_client()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Supabase 客户端不需要显式关闭
        pass


def get_supabase_connection():
    """获取 Supabase 连接（兼容旧的 MySQL 接口）"""
    return SupabaseConnection()
