# -*- coding: utf-8 -*-
"""
股票数据库管理模块
提供A股股票信息的本地缓存和动态查询
"""
import json
import os
from datetime import datetime
from typing import Dict, Optional

import akshare as ak


# 本地数据库文件路径
_STOCK_DB_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "stock_database.json")


def _load_local_db() -> Dict:
    """加载本地股票数据库"""
    if os.path.exists(_STOCK_DB_FILE):
        try:
            with open(_STOCK_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load local DB: {e}")
    return {}


def _save_local_db(data: Dict):
    """保存本地股票数据库"""
    os.makedirs(os.path.dirname(_STOCK_DB_FILE), exist_ok=True)
    with open(_STOCK_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved {len(data)} stocks to local DB")


def fetch_all_a_stocks() -> Dict:
    """
    从AkShare获取所有A股股票信息

    Returns:
        {股票代码: {name, sector, industry}}
    """
    stock_db = {}

    try:
        print("[INFO] Fetching A-share stock list from AkShare...")

        # 尝试多个接口
        interfaces = [
            # 方法1: stock_info_a_code_name - 获取A股代码和名称
            lambda: ak.stock_info_a_code_name(),
            # 方法2: stock_zh_a_spot_em - 沪深A股行情
            lambda: ak.stock_zh_a_spot_em()[['代码', '名称', '最新价']],
        ]

        stock_list = None
        for i, interface in enumerate(interfaces):
            try:
                print(f"[INFO] Trying interface {i+1}...")
                stock_list = interface()
                break
            except Exception as e:
                print(f"[WARN] Interface {i+1} failed: {e}")
                continue

        if stock_list is None or stock_list.empty:
            print("[ERROR] All interfaces failed")
            return {}

        # 处理股票列表
        for _, row in stock_list.iterrows():
            if '代码' in stock_list.columns:
                code = str(row['代码']).zfill(6)
                name = str(row['名称'])
            elif 'code' in stock_list.columns:
                code = str(row['code']).zfill(6)
                name = str(row['name'])
            else:
                continue

            # 只保留6位数字代码（A股）
            if code.isdigit() and len(code) == 6:
                stock_db[code] = {
                    'name': name,
                    'sector': '未知',  # 后续可以通过AI分类
                    'industry': '未知'
                }

        print(f"[OK] Fetched {len(stock_db)} stocks from AkShare")
        return stock_db

    except Exception as e:
        print(f"[ERROR] Failed to fetch stock list: {e}")
        import traceback
        traceback.print_exc()
        return {}


def update_stock_database():
    """
    更新本地股票数据库
    从AkShare获取最新数据并保存到本地
    """
    print("=" * 50)
    print("开始更新股票数据库...")
    print("=" * 50)

    # 获取在线数据
    online_data = fetch_all_a_stocks()

    if not online_data:
        print("[ERROR] No data fetched, keeping existing database")
        return

    # 合并本地数据（保留已有的sector/industry信息）
    local_data = _load_local_db()

    for code, info in online_data.items():
        if code in local_data:
            # 保留本地已有的分类信息
            online_data[code]['sector'] = local_data[code].get('sector', '未知')
            online_data[code]['industry'] = local_data[code].get('industry', '未知')

    # 保存更新后的数据库
    _save_local_db(online_data)

    print("=" * 50)
    print(f"股票数据库更新完成！共 {len(online_data)} 只股票")
    print(f"数据库路径: {_STOCK_DB_FILE}")
    print("=" * 50)


def get_stock_from_db(symbol: str) -> Optional[Dict]:
    """
    从本地数据库获取股票信息

    Args:
        symbol: 股票代码

    Returns:
        {name, sector, industry} 或 None
    """
    stock_db = _load_local_db()
    code = symbol.upper().zfill(6)

    if code in stock_db:
        return stock_db[code]

    return None


def search_stocks(keyword: str, limit: int = 20) -> list:
    """
    搜索股票（按代码或名称）

    Args:
        keyword: 搜索关键词
        limit: 返回结果数量限制

    Returns:
        [{code, name, sector, industry}]
    """
    stock_db = _load_local_db()
    keyword = keyword.upper()

    results = []
    for code, info in stock_db.items():
        if (keyword in code or
            keyword in info['name'] or
            keyword in info.get('pinyin', '')):
            results.append({
                'code': code,
                'name': info['name'],
                'sector': info.get('sector', '未知'),
                'industry': info.get('industry', '未知')
            })

            if len(results) >= limit:
                break

    return results


# 导出数据到CSV（可选）
def export_to_csv(output_file: str = None):
    """导出股票数据库到CSV文件"""
    if output_file is None:
        output_file = os.path.join(os.path.dirname(__file__), "..", "data", "stocks.csv")

    stock_db = _load_local_db()

    if not stock_db:
        print("[WARN] No data to export")
        return

    import pandas as pd

    data = []
    for code, info in stock_db.items():
        data.append({
            '代码': code,
            '名称': info['name'],
            '板块': info.get('sector', '未知'),
            '行业': info.get('industry', '未知')
        })

    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"[OK] Exported {len(data)} stocks to {output_file}")


if __name__ == "__main__":
    # 运行更新
    update_stock_database()

    # 导出CSV
    export_to_csv()
