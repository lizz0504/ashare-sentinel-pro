"""
Supabase Database Client (Backend)

后端专用的 Supabase 客户端配置

关键特性:
- 使用 SUPABASE_SERVICE_KEY (service_role key) 初始化
- 绕过 Row Level Security (RLS) 策略，拥有完全权限
- 用于 AI 分析引擎写入研报结果，不依赖用户登录态
"""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache(maxsize=1)
def get_db_client() -> Client:
    """
    获取 Supabase 客户端实例（后端特权模式）

    使用 Service Role Key 初始化，拥有管理员权限：
    - 绕过 RLS (Row Level Security) 策略
    - 可直接读写任何表
    - 用于 AI 引擎写入分析结果

    ⚠️ 警告: 此函数返回的客户端拥有完全权限，请谨慎使用！

    Returns:
        Client: Supabase 客户端实例

    Example:
        ```python
        from app.core.db import get_db_client

        # 写入研报分析结果（AI 引擎）
        supabase = get_db_client()
        supabase.table('reports').insert({
            'user_id': user_id,
            'analysis': ai_result,
            'created_at': now()
        }).execute()
        ```
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY,
    )


# 便捷导出
db_client = get_db_client()
