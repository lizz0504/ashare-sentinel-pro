"""
MySQL 数据库连接工具 - V1.6 版本化管理

支持直接 MySQL 连接用于版本化数据存储
"""

import os
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Optional

from app.core.config import settings


# MySQL 配置
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "ashare_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "ashare_pass")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "ashare_sentinel")

# 调试：打印配置
import sys
print(f"[DEBUG MySQL] Host={MYSQL_HOST}, User={MYSQL_USER}, Database={MYSQL_DATABASE}", file=sys.stderr)


@contextmanager
def get_mysql_connection():
    """
    获取 MySQL 数据库连接（上下文管理器）

    使用方式:
        with get_mysql_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stocks")
            results = cursor.fetchall()
    """
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=False
    )

    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_mysql_connection_direct():
    """
    获取 MySQL 数据库连接（直接返回，需手动管理）

    用于需要长期保持连接的场景

    Returns:
        connection: MySQL 连接对象
    """
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=False
    )


def test_mysql_connection() -> bool:
    """测试 MySQL 连接是否正常"""
    try:
        with get_mysql_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return result is not None
    except Exception as e:
        print(f"MySQL connection test failed: {e}")
        return False


def init_versioning_schema():
    """
    初始化版本化数据库表结构

    执行 v1.6_versioning_schema.sql 中的迁移脚本
    """
    from pathlib import Path

    schema_file = Path(__file__).parent.parent / "migrations" / "v1.6_versioning_schema.sql"

    if not schema_file.exists():
        print(f"Schema file not found: {schema_file}")
        return False

    try:
        with open(schema_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # 分割 SQL 语句（处理 DELIMITER）
        statements = []
        current_statement = []
        delimiter = ";"

        for line in sql_script.split('\n'):
            line = line.strip()

            # 跳过注释和空行
            if not line or line.startswith('--') or line.startswith('/*'):
                continue

            # 处理 DELIMITER 命令
            if line.upper().startswith('DELIMITER'):
                delimiter = line.split()[1]
                continue

            current_statement.append(line)

            # 检查是否到达语句结束
            if line.endswith(delimiter):
                statement = '\n'.join(current_statement)
                # 移除结尾的 delimiter
                if delimiter != ";":
                    statement = statement[:-len(delimiter)].strip()
                statements.append(statement)
                current_statement = []

        # 执行 SQL 语句
        with get_mysql_connection() as conn:
            cursor = conn.cursor()

            for statement in statements:
                if statement.strip():
                    try:
                        cursor.execute(statement)
                        print(f"Executed: {statement[:50]}...")
                    except Exception as e:
                        # 如果表已存在，忽略错误
                        if "already exists" not in str(e).lower():
                            print(f"SQL Error: {e}")
                            print(f"Statement: {statement[:200]}")

            conn.commit()
            print("Versioning schema initialized successfully!")
            return True

    except Exception as e:
        print(f"Failed to initialize schema: {e}")
        return False


# ============================================================================
# 便捷导出
# ============================================================================

__all__ = [
    "get_mysql_connection",
    "get_mysql_connection_direct",
    "test_mysql_connection",
    "init_versioning_schema"
]
