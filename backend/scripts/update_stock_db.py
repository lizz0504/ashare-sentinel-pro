# -*- coding: utf-8 -*-
"""
股票数据库更新脚本
运行此脚本从AkShare获取最新的A股股票列表
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.stock_db import update_stock_database, export_to_csv, search_stocks

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='更新A股股票数据库')
    parser.add_argument('--export-csv', action='store_true', help='导出为CSV文件')
    parser.add_argument('--search', type=str, help='搜索股票')
    parser.add_argument('--limit', type=int, default=20, help='搜索结果数量限制')

    args = parser.parse_args()

    if args.search:
        # 搜索股票
        results = search_stocks(args.search, args.limit)
        print(f"\n搜索 '{args.search}' 的结果 ({len(results)}):")
        print("-" * 60)
        for r in results:
            print(f"{r['code']} | {r['name']:8s} | {r['sector']:6s} | {r['industry']}")
    else:
        # 更新数据库
        update_stock_database()

        # 如果需要，导出CSV
        if args.export_csv:
            export_to_csv()
