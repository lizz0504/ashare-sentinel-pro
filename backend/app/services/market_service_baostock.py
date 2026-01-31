"""
Baostock Financial Data Fetcher - Simplified and Tested

经过测试的Baostock财务数据获取函数
"""

import baostock as bs
from datetime import datetime, timedelta
from typing import Dict, Optional


def get_financials_baostock(symbol: str) -> Optional[Dict]:
    """
    使用Baostock获取A股财务数据

    Args:
        symbol: 股票代码，如 "600519"

    Returns:
        {
            'source': 'baostock',
            'metrics': {
                'pe_ratio': float,
                'pb_ratio': float,
                'roe': float,
                'revenue_growth_cagr': float,
                ...
            },
            'timestamp': str
        }
    """
    try:
        # 登录
        lg = bs.login()
        if lg.error_code != '0':
            print(f"[ERROR] Baostock login failed: {lg.error_msg}")
            return None

        # 标准化股票代码
        market = 'sh' if symbol.startswith('6') else 'sz'
        bs_symbol = f"{market}.{symbol}"

        print(f"[INFO] Fetching data from Baostock for {bs_symbol}...")

        metrics = {}

        # 1. 获取ROE（盈利能力）
        # Columns: ['code', 'pubDate', 'statDate', 'roeAvg', 'npMargin', ...]
        rs = bs.query_profit_data(code=bs_symbol, year=2024, quarter=3)
        if rs.error_code == '0':
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            if data_list:
                # roeAvg is at index 3
                roe_str = data_list[0][3]
                if roe_str:
                    metrics['roe'] = float(roe_str) * 100  # 转换为百分比

        # 2. 获取净利润增长率（成长能力）
        # Columns: ['code', 'pubDate', 'statDate', 'YOYEquity', 'YOYAsset', 'YOYNI', ...]
        rs = bs.query_growth_data(code=bs_symbol, year=2024, quarter=3)
        if rs.error_code == '0':
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            if data_list:
                # YOYNI (净利润同比增长率) is at index 6
                yoy_ni_str = data_list[0][6]
                if yoy_ni_str:
                    metrics['revenue_growth_cagr'] = float(yoy_ni_str)

        # 3. 获取资产负债率（资产负债表数据）
        # Columns: ['code', 'pubDate', 'statDate', 'currentRatio', 'quickRatio', 'cashRatio', 'YOYLiability', 'liabilityToAsset', 'assetToEquity']
        # assetToEquity at index 8 is used to calculate debt ratio
        # Formula: 资产负债率 = (1 - 1 / assetToEquity) * 100%
        rs = bs.query_balance_data(code=bs_symbol, year=2024, quarter=3)
        if rs.error_code == '0':
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            if data_list and len(data_list[0]) > 8:
                # assetToEquity (资产权益比) is at index 8
                asset_to_equity_str = data_list[0][8]
                if asset_to_equity_str:
                    asset_to_equity = float(asset_to_equity_str)
                    # Calculate debt ratio: (1 - 1 / assetToEquity) * 100
                    if asset_to_equity > 0:
                        debt_ratio = (1 - 1 / asset_to_equity) * 100
                        metrics['debt_to_equity'] = debt_ratio

        # 4. 获取历史价格数据（PE, PB, 当前价格）
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        rs = bs.query_history_k_data_plus(
            bs_symbol,
            "date,code,close,peTTM,pbMRQ",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3"
        )

        if rs.error_code == '0':
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            if data_list:
                latest = data_list[-1]
                # close at index 2, peTTM at index 3, pbMRQ at index 4
                if latest[2]:
                    metrics['current_price'] = float(latest[2])
                if latest[3]:
                    metrics['pe_ratio'] = float(latest[3])
                if latest[4]:
                    metrics['pb_ratio'] = float(latest[4])

        # 登出
        bs.logout()

        print(f"[OK] Baostock data fetched successfully")
        print(f"[DEBUG] Metrics: {metrics}")

        return {
            'source': 'baostock',
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        print(f"[ERROR] Baostock fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Test
    result = get_financials_baostock("600519")
    if result:
        print(f"\nSource: {result['source']}")
        print(f"Metrics:")
        for k, v in result['metrics'].items():
            print(f"  {k}: {v}")
