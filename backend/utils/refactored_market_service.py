"""
Enhanced Market Service with Improved Structure
重构版本，具有更好的函数分解和可读性
"""
from typing import Optional, Dict, Tuple, List
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import warnings
warnings.filterwarnings('ignore')


# 导入帮助函数
from utils.tech_analysis_helpers import (
    _get_stock_data,
    _calculate_technical_indicators,
    _calculate_health_score,
    _determine_action_signal
)

# 检查Tushare可用性
try:
    from app.core.config import settings
    _tushare_available = not settings.DISABLE_TUSHARE and settings.TUSHARE_TOKEN is not None
    if _tushare_available:
        import tushare as ts
        ts.set_token(settings.TUSHARE_TOKEN)
        from .data_fetcher import DataFetcher
except Exception:
    _tushare_available = False


def _detect_market_type(symbol: str) -> str:
    """检测股票市场类型 (A/H/N/M/X/O)"""
    if len(symbol) == 6:
        if symbol.startswith(('000', '001', '002', '003', '300', '301', '600', '601', '603', '605', '688', '689')):
            return 'A'  # A股
        elif symbol.startswith('110') or symbol.startswith('120') or symbol.startswith('121') or symbol.startswith('122'):
            return 'B'  # 可转债
    elif symbol.startswith('hk.'):
        return 'H'  # 港股
    elif symbol.startswith('gb_') or symbol.startswith('sb_'):
        return 'N'  # 美股

    # 尝试通过正则表达式识别
    import re
    if re.match(r'^[A-Z]+$', symbol):  # 美股通常为大写字母
        return 'N'
    elif re.match(r'^[A-Z]+\.[A-Z]{2}$', symbol):  # 如 IBM.N (纽约证券交易所)
        return 'N'

    return 'A'  # 默认A股


def _normalize_symbol(symbol: str, market: str) -> str:
    """标准化股票代码"""
    if market == 'A':
        if symbol.startswith(('00', '12', '10')):
            return symbol + '.SZ'
        elif symbol.startswith(('60', '68', '56')):
            return symbol + '.SH'
        elif symbol.startswith(('11', '50', '51')):
            return symbol + '.SH'  # ETF基金
    elif market == 'H':
        return symbol.replace('hk.', '') + '.HK'
    elif market == 'N':
        return symbol  # 美股一般不需要后缀

    return symbol


def get_stock_technical_analysis_refactored(symbol: str) -> Optional[Dict]:
    """
    重构版股票技术分析函数 - 更清晰的结构和更小的函数块

    Returns:
        {
            "symbol": str,
            "current_price": float,
            "ma20_status": "站上均线" | "跌破均线",
            "volume_status": "放量" | "缩量" | "持平",
            "volume_change_pct": float,
            "alpha": float,
            "health_score": 0-100,
            "vwap_20": float,           # 20日VWAP (筹码成本)
            "bollinger_upper": float,    # 布林带上轨
            "bollinger_middle": float,   # 布林带中轨
            "bollinger_lower": float,    # 布林带下轨
            "bandwidth": float,          # 布林带宽度
            "turnover": float,           # 换手率
            "rsi_14": float,             # 14日RSI
            "action_signal": str,
            "date": str
        }
    """
    market = _detect_market_type(symbol)
    normalized_symbol = _normalize_symbol(symbol, market)

    if market != 'A':
        print(f"[WARN] Technical analysis only supports A-shares, not {market}")
        return None

    try:
        # 1. 获取股票数据（使用专门的帮助函数）
        stock_df, index_df = _get_stock_data(symbol)

        if stock_df is None or stock_df.empty:
            print(f"[ERROR] Failed to fetch data for {symbol}")
            return None

        # 2. 计算技术指标（使用专门的帮助函数）
        tech_indicators = _calculate_technical_indicators(stock_df, index_df)

        # 3. 计算健康评分（使用专门的帮助函数）
        health_score = _calculate_health_score(tech_indicators)

        # 4. 确定行动信号（使用专门的帮助函数）
        action_signal = _determine_action_signal(health_score, tech_indicators)

        # 5. 构建返回结果
        result = {
            "symbol": symbol,
            "current_price": tech_indicators["current_price"],
            "ma20_status": tech_indicators["ma20_status"],
            "ma5_status": tech_indicators["ma5_status"],
            "volume_status": tech_indicators["volume_status"],
            "volume_change_pct": tech_indicators["volume_change_pct"],
            "rsi_14": tech_indicators["rsi_14"],
            "bollinger_upper": tech_indicators["bollinger_upper"],
            "bollinger_middle": tech_indicators["bollinger_middle"],
            "bollinger_lower": tech_indicators["bollinger_lower"],
            "bandwidth": tech_indicators["bandwidth"],
            "vwap_20": tech_indicators["vwap_20"],
            "alpha": tech_indicators["alpha"],
            "health_score": health_score,
            "k_line_pattern": tech_indicators["k_line_pattern"],
            "pattern_signal": tech_indicators["pattern_signal"],
            "action_signal": action_signal,
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        print(f"[OK] Technical analysis complete for {symbol}")
        return result

    except Exception as e:
        print(f"[ERROR] Failed to analyze {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_stock_technical_analysis(symbol: str) -> Optional[Dict]:
    """
    原始函数保留兼容性，调用重构版本
    """
    return get_stock_technical_analysis_refactored(symbol)