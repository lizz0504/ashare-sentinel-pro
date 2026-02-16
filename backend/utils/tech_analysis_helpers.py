"""
Technical Analysis Helper Functions
将长函数分解为更小、更易管理的功能块
"""
from typing import Optional, Dict, Tuple
import pandas as pd
from datetime import datetime, timedelta


def _get_stock_data(symbol: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    获取股票数据，包含多个数据源

    Returns:
        Tuple of (stock_df, index_df) or (None, None) if failed
    """
    market = _detect_market_type(symbol)
    normalized_symbol = _normalize_symbol(symbol, market)

    if market != 'A':
        print(f"[WARN] Technical analysis only supports A-shares, not {market}")
        return None, None

    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 获取更多数据以计算60日均线

    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    print(f"[INFO] Fetching technical data for {symbol}...")

    # 数据源优先级: Tushare → Baostock → AkShare
    stock_df = None
    index_df = None

    # 1. 首先尝试 Tushare
    if _tushare_available:
        try:
            from . import _get_data_fetcher
            fetcher = _get_data_fetcher()
            if fetcher:
                print(f"[DATA SOURCE] Using Tushare Pro for {symbol}")

                def fetch_data():
                    df = fetcher.pro.daily(
                        ts_code=normalized_symbol,
                        start_date=start_str.replace('-', ''),
                        end_date=end_str.replace('-', '')
                    )
                    return df

                df = fetcher._retry_request(fetch_data)

                if df is not None and not df.empty:
                    stock_df = df.copy()

                    # 获取指数数据 (000001.SH 对应上证指数)
                    def fetch_index_data():
                        idx_df = fetcher.pro.index_daily(
                            ts_code='000001.SH',
                            start_date=start_str.replace('-', ''),
                            end_date=end_str.replace('-', '')
                        )
                        return idx_df

                    idx_df = fetcher._retry_request(fetch_index_data)
                    if idx_df is not None and not idx_df.empty:
                        index_df = idx_df.copy()

                    print(f"[OK] Tushare Pro data fetched: {len(stock_df)} rows")

        except Exception as e:
            print(f"[WARN] Tushare failed for {symbol}: {e}")

    # 2. 备选：Baostock
    if stock_df is None or stock_df.empty:
        try:
            print(f"[DATA SOURCE] Trying Baostock for {symbol}")
            from .market_service_baostock import get_stock_info_baostock
            baostock_data = get_stock_info_baostock(symbol)
            if baostock_data and 'daily_data' in baostock_data:
                stock_df = baostock_data['daily_data']
                print(f"[OK] Baostock data fetched: {len(stock_df)} rows")
        except Exception as e:
            print(f"[WARN] Baostock failed for {symbol}: {e}")

    # 3. 备选：AkShare
    if stock_df is None or stock_df.empty:
        try:
            print(f"[DATA SOURCE] Trying AkShare for {symbol}")
            import akshare as ak
            stock_df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_str,
                end_date=end_str,
                adjust=""
            )
            if stock_df is not None and not stock_df.empty:
                stock_df = stock_df.rename(columns={
                    '日期': 'trade_date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'vol',
                    '成交额': 'amount'
                })
                stock_df['trade_date'] = pd.to_datetime(stock_df['trade_date'])
                stock_df['ts_code'] = symbol
                print(f"[OK] AkShare data fetched: {len(stock_df)} rows")

                # 获取上证指数数据
                index_df = ak.stock_zh_index_hist_csindex(
                    symbol="000001",
                    start_date=start_str,
                    end_date=end_str
                )
                if index_df is not None and not index_df.empty:
                    index_df['trade_date'] = pd.to_datetime(index_df['日期'])
                    print(f"[OK] Index data fetched: {len(index_df)} rows")

        except Exception as e:
            print(f"[WARN] AkShare failed for {symbol}: {e}")

    return stock_df, index_df


def _calculate_technical_indicators(stock_df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> Dict:
    """
    计算技术指标

    Args:
        stock_df: 股票数据
        index_df: 指数数据（可选）

    Returns:
        计算得到的技术指标字典
    """
    import numpy as np

    # 确保数据按时间升序排序
    stock_df = stock_df.sort_values('trade_date').reset_index(drop=True)

    # 计算各项技术指标
    closes = stock_df['close'].values
    highs = stock_df['high'].values
    lows = stock_df['low'].values
    volumes = stock_df['vol'].values if 'vol' in stock_df.columns else stock_df['volume'].values
    dates = stock_df['trade_date']

    current_price = closes[-1]
    prev_close = closes[-2] if len(closes) > 1 else current_price

    # 1. MA20 - 20日移动平均线
    if len(closes) >= 20:
        ma20 = np.mean(closes[-20:])
        ma20_status = "站上均线" if current_price >= ma20 else "跌破均线"
    else:
        ma20 = current_price
        ma20_status = "数据不足"

    # 2. MA5 - 5日移动平均线
    if len(closes) >= 5:
        ma5 = np.mean(closes[-5:])
        ma5_status = "站上均线" if current_price >= ma5 else "跌破均线"
    else:
        ma5 = current_price
        ma5_status = "数据不足"

    # 3. 成交量状态
    recent_avg_vol = np.mean(volumes[-10:]) if len(volumes) >= 10 else volumes[-1]
    current_vol = volumes[-1]
    vol_pct_change = ((current_vol - recent_avg_vol) / recent_avg_vol) * 100

    if vol_pct_change > 20:
        volume_status = "放量"
    elif vol_pct_change < -20:
        volume_status = "缩量"
    else:
        volume_status = "持平"

    # 4. RSI (14日)
    def calculate_rsi(prices, period=14):
        if len(prices) < period + 1:
            return 50.0

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gains = np.zeros_like(gains)
        avg_losses = np.zeros_like(losses)

        avg_gains[period-1] = np.mean(gains[:period])
        avg_losses[period-1] = np.mean(losses[:period])

        for i in range(period, len(gains)):
            avg_gains[i] = (avg_gains[i-1] * (period-1) + gains[i]) / period
            avg_losses[i] = (avg_losses[i-1] * (period-1) + losses[i]) / period

        rs = avg_gains / (avg_losses + 1e-10)  # 避免除零
        rsi = 100 - (100 / (1 + rs))
        return rsi[-1] if len(rsi) > 0 else 50.0

    rsi_14 = calculate_rsi(closes)

    # 5. 布林带
    bb_period = 20
    if len(closes) >= bb_period:
        bb_middle = np.mean(closes[-bb_period:])
        bb_std = np.std(closes[-bb_period:])
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)
        bb_bandwidth = (bb_upper - bb_lower) / bb_middle * 100  # 布林带宽度百分比
    else:
        bb_middle = current_price
        bb_upper = current_price * 1.05
        bb_lower = current_price * 0.95
        bb_bandwidth = 10.0

    # 6. VWAP (Volume Weighted Average Price) - 20日
    vwap_period = 20
    if len(closes) >= vwap_period:
        recent_df = stock_df.tail(vwap_period).copy()
        # 计算典型价格 (High + Low + Close) / 3
        typical_prices = (recent_df['high'] + recent_df['low'] + recent_df['close']) / 3
        volumes_recent = recent_df['vol'].values if 'vol' in recent_df.columns else recent_df['volume'].values

        # 计算VWAP
        price_volume = typical_prices * volumes_recent
        vwap_20 = price_volume.sum() / volumes_recent.sum()
    else:
        vwap_20 = current_price

    # 7. Alpha (相对于大盘的超额收益)
    alpha = 0.0
    if index_df is not None and len(index_df) >= len(stock_df):
        # 计算股票和指数的近期收益率
        stock_returns = (closes[-1] - closes[-21]) / closes[-21] if len(closes) >= 21 else 0
        index_returns = 0.0  # 这里需要获取对应的指数收益率
        # TODO: 实现Alpha计算逻辑

    # 8. K线形态识别
    def recognize_k_line_pattern(df):
        if len(df) < 3:
            return "普通震荡"

        recent_3 = df.tail(3)
        closes_3 = recent_3['close'].values
        opens_3 = recent_3['open'].values
        highs_3 = recent_3['high'].values
        lows_3 = recent_3['low'].values

        # 当前K线特征
        current_body_size = abs(closes_3[-1] - opens_3[-1])
        current_upper_shadow = highs_3[-1] - max(closes_3[-1], opens_3[-1])
        current_lower_shadow = min(closes_3[-1], opens_3[-1]) - lows_3[-1]
        current_range = highs_3[-1] - lows_3[-1]

        # 识别特定形态
        if current_range > 0 and current_lower_shadow / current_range > 0.6 and current_body_size / current_range < 0.1:
            return "金针探底"
        elif current_range > 0 and current_upper_shadow / current_range > 0.6 and current_body_size / current_range < 0.1:
            return "冲高回落"
        elif current_body_size / current_range > 0.8:
            if closes_3[-1] > opens_3[-1]:
                return "光头大阳线"
            else:
                return "光脚大阴线"
        elif current_body_size / current_range < 0.1:
            return "变盘十字星"
        else:
            return "普通震荡"

    k_line_pattern = recognize_k_line_pattern(stock_df)

    # 9. 形态信号
    pattern_signal = "N/A"
    if k_line_pattern == "金针探底":
        pattern_signal = "买入信号"
    elif k_line_pattern == "冲高回落":
        pattern_signal = "卖出信号"
    elif k_line_pattern == "光头大阳线":
        pattern_signal = "强势买入"
    elif k_line_pattern == "光脚大阴线":
        pattern_signal = "弱势卖出"
    elif k_line_pattern == "变盘十字星":
        pattern_signal = "观望信号"
    else:
        pattern_signal = "中性信号"

    return {
        "current_price": current_price,
        "ma20": ma20,
        "ma20_status": ma20_status,
        "ma5": ma5,
        "ma5_status": ma5_status,
        "volume_status": volume_status,
        "volume_change_pct": vol_pct_change,
        "rsi_14": rsi_14,
        "bollinger_upper": bb_upper,
        "bollinger_middle": bb_middle,
        "bollinger_lower": bb_lower,
        "bandwidth": bb_bandwidth,
        "vwap_20": vwap_20,
        "alpha": alpha,
        "k_line_pattern": k_line_pattern,
        "pattern_signal": pattern_signal
    }


def _calculate_health_score(tech_data: Dict) -> int:
    """
    计算技术健康评分 (0-100)

    Args:
        tech_data: 技术指标数据

    Returns:
        健康评分 (0-100)
    """
    score = 50  # 基础分

    # MA20 状态 (±20分)
    if tech_data.get("ma20_status") == "站上均线":
        score += 20
    elif tech_data.get("ma20_status") == "跌破均线":
        score -= 20

    # MA5 状态 (±15分)
    if tech_data.get("ma5_status") == "站上均线":
        score += 15
    elif tech_data.get("ma5_status") == "跌破均线":
        score -= 15

    # RSI 状态 (±10分)
    rsi = tech_data.get("rsi_14", 50)
    if 30 <= rsi <= 70:  # 正常区间
        score += 5
    elif rsi < 30:  # 超卖
        score += 10
    elif rsi > 70:  # 超买
        score -= 10

    # 成交量状态 (±10分)
    vol_status = tech_data.get("volume_status")
    if vol_status == "放量":
        score += 10  # 放量通常是积极信号
    elif vol_status == "缩量":
        score -= 5   # 缩量可能是消极信号

    # K线形态 (±15分)
    k_pattern = tech_data.get("k_line_pattern")
    pattern_scores = {
        "金针探底": 15,   # 强烈买入信号
        "光头大阳线": 12,  # 强势买入
        "变盘十字星": 5,   # 中性偏积极
        "普通震荡": 0,    # 中性
        "冲高回落": -10,  # 强烈卖出信号
        "光脚大阴线": -15  # 强势卖出
    }
    score += pattern_scores.get(k_pattern, 0)

    # 限制分数在0-100范围内
    return max(0, min(100, int(score)))


def _determine_action_signal(health_score: int, tech_data: Dict) -> str:
    """
    根据健康评分和技术数据确定行动信号

    Args:
        health_score: 健康评分
        tech_data: 技术指标数据

    Returns:
        行动信号字符串
    """
    if health_score >= 80:
        return "STRONG_BUY"
    elif health_score >= 60:
        return "BUY"
    elif health_score >= 40:
        return "HOLD"
    elif health_score >= 20:
        return "SELL"
    else:
        return "STRONG_SELL"