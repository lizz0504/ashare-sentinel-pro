# -*- coding: utf-8 -*-
"""
Market Service - Fetches stock market data using AkShare/Tushare
使用 AkShare 或 Tushare 获取股票市场数据，支持 A 股、美股和港股
"""
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd

# 数据源选择：优先使用 Tushare，降级到 AkShare
_USE_TUSHARE = False
_data_fetcher = None

# Always import AkShare as fallback
import akshare as ak

# 检查是否完全禁用 Tushare
try:
    from app.core.config import settings
    if getattr(settings, 'DISABLE_TUSHARE', False):
        _USE_TUSHARE = False
        print("[DATA SOURCE] 📈 Tushare disabled by configuration (DISABLE_TUSHARE=True)")
    else:
        from app.services.data_fetcher import DataFetcher
        _USE_TUSHARE = True
        print("[DATA SOURCE] 🔍 DataFetcher module found - Tushare Pro support available")
except ImportError:
    print("[DATA SOURCE] 📈 DataFetcher module not found - will use AkShare only")

# ============================================
# 缓存配置
# ============================================
_CACHE = {}
_CACHE_TTL = 300  # 缓存5分钟

def _get_cache_key(key: str) -> tuple:
    """从缓存获取数据"""
    if key in _CACHE:
        data, timestamp = _CACHE[key]
        if time.time() - timestamp < _CACHE_TTL:
            return data
        else:
            del _CACHE[key]
    return None

def _set_cache(key: str, data):
    """设置缓存"""
    _CACHE[key] = (data, time.time())

# 导入股票数据库模块
try:
    from app.services.stock_db import get_stock_from_db
    _USE_STOCK_DB = True
except ImportError:
    _USE_STOCK_DB = False
    print("[WARN] stock_db module not available, using fallback database")


# ============================================
# DataFetcher 初始化
# ============================================
def _get_data_fetcher():
    """获取或创建 DataFetcher 实例"""
    global _data_fetcher, _USE_TUSHARE
    if _USE_TUSHARE and _data_fetcher is None:
        try:
            # 从配置读取 Tushare Token
            from app.core.config import settings
            token = settings.TUSHARE_TOKEN

            if token:
                _data_fetcher = DataFetcher(token=token)
                print("[DATA SOURCE] ✅ Tushare Pro initialized successfully (Token configured)")
            else:
                print("[DATA SOURCE] ⚠️  TUSHARE_TOKEN not set in environment, falling back to AkShare")
                _USE_TUSHARE = False
                import akshare as ak
        except Exception as e:
            print(f"[DATA SOURCE] ❌ Failed to initialize Tushare Pro: {e}")
            print(f"[DATA SOURCE] 📈 Falling back to AkShare")
            _USE_TUSHARE = False
            import akshare as ak
    return _data_fetcher


# 本地股票数据库（常见股票）
_STOCK_DATABASE = {
    # A 股
    '600519': {'name': '贵州茅台', 'sector': '消费品', 'industry': '白酒'},
    '000858': {'name': '五粮液', 'sector': '消费品', 'industry': '白酒'},
    '600036': {'name': '招商银行', 'sector': '金融', 'industry': '银行'},
    '601318': {'name': '中国平安', 'sector': '金融', 'industry': '保险'},
    '600900': {'name': '长江电力', 'sector': '公用事业', 'industry': '电力'},
    '600030': {'name': '中信证券', 'sector': '金融', 'industry': '证券'},
    '000001': {'name': '平安银行', 'sector': '金融', 'industry': '银行'},
    '002415': {'name': '海康威视', 'sector': '科技', 'industry': '安防'},
    '300750': {'name': '宁德时代', 'sector': '新能源', 'industry': '锂电池'},
    '002594': {'name': '比亚迪', 'sector': '新能源', 'industry': '新能源汽车'},
    '600276': {'name': '恒瑞医药', 'sector': '医疗健康', 'industry': '化学制药'},
    '000333': {'name': '美的集团', 'sector': '消费品', 'industry': '家电'},
    '002050': {'name': '三花智控', 'sector': '工业', 'industry': '制冷设备'},
    '600547': {'name': '山东黄金', 'sector': '材料', 'industry': '贵金属'},
    '600887': {'name': '伊利股份', 'sector': '消费品', 'industry': '食品'},
    '000651': {'name': '格力电器', 'sector': '消费品', 'industry': '家电'},
    '601012': {'name': '隆基绿能', 'sector': '新能源', 'industry': '光伏'},
    '300059': {'name': '东方财富', 'sector': '金融', 'industry': '证券'},
    '000725': {'name': '京东方A', 'sector': '科技', 'industry': '半导体'},
    '002475': {'name': '立讯精密', 'sector': '科技', 'industry': '消费电子'},
    '002028': {'name': '索菲亚', 'sector': '消费品', 'industry': '家居'},
    '300124': {'name': '汇川技术', 'sector': '工業', 'industry': '自动化'},
    '601390': {'name': '中国中铁', 'sector': '工業', 'industry': '基建'},
    '601766': {'name': '中国中车', 'sector': '工業', 'industry': '轨道交通'},
    # 美股
    'AAPL': {'name': 'Apple Inc.', 'sector': '科技', 'industry': 'Technology'},
    'MSFT': {'name': 'Microsoft', 'sector': '科技', 'industry': 'Software'},
    'GOOGL': {'name': 'Alphabet', 'sector': '科技', 'industry': 'Internet'},
    'AMZN': {'name': 'Amazon', 'sector': '消费品', 'industry': 'E-Commerce'},
    'TSLA': {'name': 'Tesla', 'sector': '科技', 'industry': 'Automotive'},
    'NVDA': {'name': 'NVIDIA', 'sector': '科技', 'industry': 'Semiconductor'},
    'META': {'name': 'Meta', 'sector': '科技', 'industry': 'Social Media'},
    'JPM': {'name': 'JPMorgan', 'sector': '金融', 'industry': 'Banking'},
    'V': {'name': 'Visa', 'sector': '金融', 'industry': 'Payment'},
    'JNJ': {'name': 'Johnson & Johnson', 'sector': '医疗健康', 'industry': 'Pharma'},
    'WMT': {'name': 'Walmart', 'sector': '消费品', 'industry': 'Retail'},
    'DIS': {'name': 'Disney', 'sector': '消费品', 'industry': 'Entertainment'},
    'NFLX': {'name': 'Netflix', 'sector': '通信', 'industry': 'Streaming'},
    'AMD': {'name': 'AMD', 'sector': '科技', 'industry': 'Semiconductor'},
    'INTC': {'name': 'Intel', 'sector': '科技', 'industry': 'Semiconductor'},
    # 港股
    '00700': {'name': '腾讯控股', 'sector': '科技', 'industry': '互联网'},
    '09988': {'name': '阿里巴巴', 'sector': '科技', 'industry': '电商'},
    '00005': {'name': '汇丰控股', 'sector': '金融', 'industry': '银行'},
    '09399': {'name': '美团', 'sector': '消费品', 'industry': '本地服务'},
    '02020': {'name': '安踏体育', 'sector': '消费品', 'industry': '体育用品'},
}


def _detect_market_type(symbol: str) -> str:
    """检测股票类型: A(6位数字), US(字母), HK(4-5位数字)"""
    symbol = symbol.upper().strip()

    if re.match(r'^\d{6}$', symbol):
        return 'A'
    if re.match(r'^\d{4,5}\.HK$', symbol) or re.match(r'^0?\d{4,5}$', symbol):
        return 'HK'
    if re.match(r'^[A-Z]+$', symbol):
        return 'US'
    return 'UNKNOWN'


def _normalize_symbol(symbol: str, market: str) -> str:
    """标准化股票代码"""
    symbol = symbol.upper().strip()

    if market == 'A':
        return symbol.zfill(6)
    if market == 'HK':
        return symbol.replace('.HK', '').zfill(5)
    return symbol


def _get_realtime_price(symbol: str, market: str) -> Optional[float]:
    """
    获取实时股价

    Args:
        symbol: 标准化的股票代码
        market: 市场类型 (A/US/HK)

    Returns:
        最新股价或None
    """
    try:
        if market == 'A':
            # A股实时行情 - 使用历史数据接口获取最新价格
            print(f"[INFO] Fetching realtime price for A-share {symbol}...")
            end_date = datetime.now()
            end_str = end_date.strftime('%Y-%m-%d')

            if _USE_TUSHARE:
                # 使用 Tushare
                fetcher = _get_data_fetcher()
                if fetcher:
                    hist_df = fetcher.get_stock_daily(
                        symbol=symbol,
                        end_date=end_str
                    )
                    if hist_df is not None and not hist_df.empty:
                        price = float(hist_df.iloc[-1]['收盘'])
                        print(f"[OK] {symbol} realtime price: {price}")
                        return price
            else:
                # 使用 AkShare
                hist_df = _retry_akshare_call(
                    ak.stock_zh_a_hist,
                    symbol=symbol,
                    period="daily",
                    end_date=end_date.strftime('%Y%m%d'),
                    adjust="",
                    max_retries=2
                )
                if hist_df is not None and not hist_df.empty:
                    price = float(hist_df.iloc[-1]['收盘'])
                    print(f"[OK] {symbol} realtime price: {price}")
                    return price

        elif market == 'US':
            # 美股暂不支持实时
            print(f"[WARN] US stocks realtime price not supported")
            return None

        elif market == 'HK':
            # 港股暂不支持实时
            print(f"[WARN] HK stocks realtime price not supported")
            return None

    except Exception as e:
        print(f"[WARN] Failed to fetch realtime price: {e}")

    return None


def _fetch_stock_detail_from_akshare(symbol: str) -> Optional[Dict]:
    """
    从Tushare/AkShare获取股票详细信息（包括行业）

    Returns:
        {
            "name": str,
            "industry": str,
            "sector": str
        }
    """
    try:
        # 优先使用 Tushare
        if _USE_TUSHARE:
            fetcher = _get_data_fetcher()
            if fetcher:
                print(f"[INFO] Fetching stock details from Tushare for {symbol}...")
                result = fetcher.get_stock_info(symbol)
                if result:
                    print(f"[OK] Got stock details from Tushare: {result.get('name')}, industry={result.get('industry')}, sector={result.get('sector')}")
                    return result

        # 降级到 AkShare
        print(f"[INFO] Fetching stock details from AkShare for {symbol}...")
        # 使用 stock_individual_info_em 获取个股信息
        info_df = ak.stock_individual_info_em(symbol=symbol)
        if info_df is not None and not info_df.empty:
            # 将DataFrame转换为字典
            info_dict = dict(zip(info_df['item'], info_df['value']))

            stock_name = info_dict.get('股票简称', symbol)

            # 获取行业信息
            industry = info_dict.get('所属行业', None)

            # 根据行业名称推测板块
            sector = "其他"
            if industry:
                if any(x in industry for x in ['银行', '保险', '证券', '信托']):
                    sector = '金融'
                elif any(x in industry for x in ['医药', '生物', '医疗', '保健']):
                    sector = '医疗健康'
                elif any(x in industry for x in ['电子', '计算机', '软件', '通信', '互联网']):
                    sector = '科技'
                elif any(x in industry for x in ['汽车', '新能源', '光伏', '风电']):
                    sector = '新能源'
                elif any(x in industry for x in ['白酒', '食品', '家电', '纺织', '服饰']):
                    sector = '消费品'
                elif any(x in industry for x in ['化工', '钢铁', '有色', '建材']):
                    sector = '材料'
                elif any(x in industry for x in ['电力', '水务', '燃气']):
                    sector = '公用事业'
                elif any(x in industry for x in ['建筑', '装修', '基建']):
                    sector = '工业'
                elif any(x in industry for x in ['房地产']):
                    sector = '房地产'
                elif any(x in industry for x in ['交通运输', '物流', '航空']):
                    sector = '交通运输'
                elif any(x in industry for x in ['传媒', '娱乐', '教育']):
                    sector = '文化娱乐'
                else:
                    sector = '其他'
            else:
                # 如果没有行业信息，根据股票代码推测
                # 600xxx, 601xxx, 603xxx, 605xxx = 上海主板
                # 000xxx, 001xxx = 深圳主板
                # 002xxx = 深圳中小板
                # 300xxx = 深圳创业板
                # 688xxx = 上海科创板
                if symbol.startswith('688'):
                    sector = '科技'  # 科创板多为科技股
                elif symbol.startswith('300'):
                    sector = '科技'  # 创业板多为科技/成长股
                elif symbol.startswith('002'):
                    sector = '工业'  # 中小板
                else:
                    sector = '其他'

            # 如果还是没有行业，设置默认值
            if not industry:
                industry = sector  # 用板块作为行业

            print(f"[OK] Got stock details from AkShare: {stock_name}, industry={industry}, sector={sector}")
            return {
                "name": stock_name,
                "industry": industry,
                "sector": sector
            }
    except Exception as e:
        print(f"[WARN] Failed to fetch stock details: {e}")
        import traceback
        traceback.print_exc()

    return None


def get_stock_info(symbol: str, fetch_price: bool = True, max_retries: int = 0) -> Optional[Dict]:
    """
    获取股票基本信息（含实时股价）

    Args:
        symbol: 股票代码
        fetch_price: 是否获取实时股价（默认True）
        max_retries: 最大重试次数（已废弃，保留兼容性）

    Returns:
        {
            "symbol": str,
            "name": str,
            "sector_en": str,
            "industry_en": str,
            "current_price": float | None,
            "currency": str,
            "market_cap": float | None,
            "description": str
        }
    """
    market = _detect_market_type(symbol)
    normalized_symbol = _normalize_symbol(symbol, market)

    print(f"[INFO] Fetching stock info for {symbol} (market: {market})")

    # 标准化查询键
    lookup_key = normalized_symbol if market != 'HK' else symbol.upper().replace('.HK', '').zfill(5)

    stock_name = None
    stock_sector = None
    stock_industry = None

    # 1. 优先尝试新的股票数据库文件
    if _USE_STOCK_DB and market == 'A':
        stock_data = get_stock_from_db(lookup_key)
        if stock_data:
            print(f"[DEBUG] Found in stock DB file: {lookup_key}")
            stock_name = stock_data['name']
            stock_sector = stock_data.get('sector', '未知')
            stock_industry = stock_data.get('industry', '未知')

    # 2. 回退到旧的硬编码数据库
    if not stock_name and lookup_key in _STOCK_DATABASE:
        local_data = _STOCK_DATABASE[lookup_key]
        print(f"[DEBUG] Found in fallback DB: {lookup_key}")
        stock_name = local_data['name']
        stock_sector = local_data['sector']
        stock_industry = local_data['industry']

    # 3. 如果本地都没有，尝试从AkShare获取
    if not stock_name or stock_sector == "其他" or stock_industry == "其他":
        print(f"[INFO] Trying AkShare for {symbol}...")
        akshare_data = _fetch_stock_detail_from_akshare(normalized_symbol)
        if akshare_data:
            stock_name = akshare_data['name']
            stock_sector = akshare_data['sector']
            stock_industry = akshare_data['industry']
            print(f"[OK] Got data from AkShare for {symbol}")

    # 4. 如果还是没有，返回默认值
    if not stock_name:
        print(f"[WARN] Not found in any DB, using default for {symbol}")
        stock_name = symbol.upper()
        stock_sector = "其他"
        stock_industry = "其他"

    # 5. 获取实时股价（如果需要）
    current_price = None
    if fetch_price and market == 'A':
        current_price = _get_realtime_price(normalized_symbol, market)

    # 确定货币
    currency = "CNY" if market == 'A' else "HKD" if market == 'HK' else "USD"

    return {
        "symbol": symbol.upper(),
        "name": stock_name,
        "sector_en": stock_sector,
        "industry_en": stock_industry,
        "current_price": current_price,
        "currency": currency,
        "market_cap": None,
        "description": "",
    }


def get_weekly_performance(symbol: str, days: int = 7) -> Optional[Dict]:
    """获取股票週度表现（仅支持 A 股）"""
    market = _detect_market_type(symbol)
    normalized_symbol = _normalize_symbol(symbol, market)

    print(f"[INFO] Fetching weekly performance for {symbol} (market: {market})")

    if market != 'A':
        print(f"[WARN] Weekly performance only supports A-shares, not {market}")
        return None

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + 10)

    try:
        if _USE_TUSHARE:
            # 使用 Tushare
            fetcher = _get_data_fetcher()
            if fetcher:
                start_str = start_date.strftime('%Y-%m-%d')
                end_str = end_date.strftime('%Y-%m-%d')
                print(f"[DEBUG] Calling Tushare for {normalized_symbol}...")

                hist_df = fetcher.get_stock_daily(
                    symbol=normalized_symbol,
                    start_date=start_str,
                    end_date=end_str
                )
            else:
                # 降级到 AkShare
                start_str = start_date.strftime('%Y%m%d')
                end_str = end_date.strftime('%Y%m%d')
                print(f"[DEBUG] Calling AkShare for {normalized_symbol}...")

                hist_df = _retry_akshare_call(
                    ak.stock_zh_a_hist,
                    symbol=normalized_symbol,
                    period="daily",
                    start_date=start_str,
                    end_date=end_str,
                    adjust="qfq"
                )
        else:
            # 只使用 AkShare
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            print(f"[DEBUG] Calling AkShare for {normalized_symbol}...")

            hist_df = _retry_akshare_call(
                ak.stock_zh_a_hist,
                symbol=normalized_symbol,
                period="daily",
                start_date=start_str,
                end_date=end_str,
                adjust="qfq"
            )

        if hist_df is None or hist_df.empty or len(hist_df) < 2:
            print(f"[WARN] Insufficient data for {symbol}")
            return None

        hist_df = hist_df.sort_values('日期')
        start_price = float(hist_df.iloc[0]['收盘'])
        end_price = float(hist_df.iloc[-1]['收盘'])

        price_change = end_price - start_price
        price_change_pct = (price_change / start_price) * 100 if start_price > 0 else 0

        print(f"[OK] {symbol}: {price_change_pct:.2f}%")
        return {
            "symbol": symbol,
            "start_price": round(start_price, 4),
            "end_price": round(end_price, 4),
            "price_change": round(price_change, 4),
            "price_change_pct": round(price_change_pct, 4),
            "period_days": days,
        }

    except Exception as e:
        print(f"[ERROR] Failed to fetch performance: {e}")
        return None


def validate_symbol(symbol: str) -> bool:
    """验证股票代码格式"""
    market = _detect_market_type(symbol)
    if market == 'UNKNOWN':
        print(f"[WARN] Unknown symbol format: {symbol}")
        return False
    print(f"[INFO] Symbol {symbol} valid (market: {market})")
    return True


# ============================================
# 技术分析函数
# ============================================


def _retry_akshare_call(func, *args, max_retries=3, timeout=15, **kwargs):
    """带重试机制的 AkShare 调用"""
    last_error = None
    for attempt in range(max_retries):
        try:
            # 尝试添加超时参数
            if 'timeout' in func.__code__.co_varnames:
                kwargs['timeout'] = timeout
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3  # 增加等待时间到3秒
                print(f"[WARN] API call failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] API call failed after {max_retries} attempts: {e}")
    raise last_error


def get_market_sentiment() -> Optional[Dict]:
    """
    获取市场贪婪指数（基于沪深300 RSI）

    Returns:
        {
            "score": 0-100,  # RSI值，反向作为贪婪指数
            "label": "极度恐慌" | "恐慌" | "中性" | "贪婪" | "极度贪婪",
            "rsi": float,
            "date": str
        }
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # 获取60个交易日左右

        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        print(f"[INFO] Fetching CSI 300 data for sentiment analysis...")

        # 获取沪深300历史数据
        hist_df = None
        if _USE_TUSHARE:
            fetcher = _get_data_fetcher()
            if fetcher:
                try:
                    hist_df = fetcher.get_index_daily(
                        symbol="000300",
                        start_date=start_str,
                        end_date=end_str
                    )
                    print("[INFO] Using Tushare Pro data source for index")
                except Exception as e:
                    print(f"[WARN] Tushare index data fetch failed: {e}, falling back to AkShare")
                    hist_df = None

        # 如果 Tushare 失败或未启用，使用 AkShare
        if hist_df is None:
            print("[INFO] Using AkShare as fallback for index data")
            try:
                hist_df = _retry_akshare_call(
                    ak.index_zh_a_hist,
                    symbol="000300",
                    period="daily",
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d')
                )
            except Exception as e:
                print(f"[WARN] AkShare index data fetch also failed: {e}")
                hist_df = None

        # 如果两种数据源都失败，返回中性默认值
        if hist_df is None or hist_df.empty or len(hist_df) < 60:
            print(f"[WARN] Insufficient CSI 300 data from all sources, using neutral default")
            # 返回中性默认值
            return {
                "score": 50.0,
                "label": "中性 (数据暂不可用)",
                "rsi": 50.0,
                "date": datetime.now().strftime('%Y-%m-%d'),
                "data_source": "default"
            }

        hist_df = hist_df.sort_values('日期')

        # 计算RSI (使用pandas_ta)
        try:
            import pandas_ta as ta
            close = hist_df['收盘'].values
            rsi_values = ta.rsi(close, length=14)
            current_rsi = float(rsi_values[-1])
        except ImportError:
            print("[WARN] pandas_ta not installed, using manual RSI calculation")
            # 手动计算RSI
            close = hist_df['收盘'].values
            delta = pd.Series(close).diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi_values = 100 - (100 / (1 + rs))
            current_rsi = float(rsi_values.iloc[-1])

        # RSI作为贪婪指数（RSI低=恐慌=贪婪机会高）
        # 我们反转RSI：RSI越低，市场越恐慌，贪婪指数越高
        greed_index = 100 - current_rsi

        # 标签映射
        if current_rsi < 20:
            label = "极度恐慌 (机会)"
        elif current_rsi < 40:
            label = "恐慌"
        elif current_rsi < 60:
            label = "中性"
        elif current_rsi < 80:
            label = "贪婪"
        else:
            label = "极度贪婪 (风险)"

        print(f"[OK] Market sentiment: {label}, RSI={current_rsi:.2f}, Greed={greed_index:.2f}")

        # 获取日期（确保是字符串格式）
        date_value = hist_df.iloc[-1]['日期']
        if isinstance(date_value, str):
            date_str = date_value
        else:
            date_str = str(date_value)

        return {
            "score": round(greed_index, 2),
            "label": label,
            "rsi": round(current_rsi, 2),
            "date": date_str
        }

    except Exception as e:
        print(f"[ERROR] Failed to calculate market sentiment: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_stock_technical_analysis(symbol: str) -> Optional[Dict]:
    """
    获取个股技术分析

    Returns:
        {
            "symbol": str,
            "ma20_status": "站上均线" | "跌破均线",
            "volume_status": "放量" | "缩量" | "持平",
            "volume_change_pct": float,
            "alpha": float,  # 相对沪深300的超额收益
            "health_score": 0-100,
            "date": str
        }
    """
    market = _detect_market_type(symbol)
    normalized_symbol = _normalize_symbol(symbol, market)

    if market != 'A':
        print(f"[WARN] Technical analysis only supports A-shares, not {market}")
        return None

    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=45)  # 获取30个交易日左右

        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        print(f"[INFO] Fetching technical data for {symbol}...")

        # 获取个股数据
        if _USE_TUSHARE:
            fetcher = _get_data_fetcher()
            if fetcher:
                print(f"[DATA SOURCE] 📊 Using Tushare Pro for {symbol}")
                stock_df = fetcher.get_stock_daily(
                    symbol=normalized_symbol,
                    start_date=start_str,
                    end_date=end_str
                )
                # 获取沪深300作为基准
                try:
                    print(f"[DATA SOURCE] 📊 Using Tushare Pro for index 000300 (HS300)")
                    index_df = fetcher.get_index_daily(
                        symbol="000300",
                        start_date=start_str,
                        end_date=end_str
                    )
                except Exception as e:
                    print(f"[WARN] Failed to fetch index data: {e}")
                    index_df = None
            else:
                # 降级到 AkShare
                print(f"[DATA SOURCE] 📈 Tushare unavailable, falling back to AkShare for {symbol}")
                stock_df = _retry_akshare_call(
                    ak.stock_zh_a_hist,
                    symbol=normalized_symbol,
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d')
                )
                try:
                    print(f"[DATA SOURCE] 📈 Using AkShare for index 000300 (HS300)")
                    index_df = _retry_akshare_call(
                        ak.index_zh_a_hist,
                        symbol="000300",
                        period="daily",
                        start_date=start_date.strftime('%Y%m%d'),
                        end_date=end_date.strftime('%Y%m%d')
                    )
                except Exception as e:
                    print(f"[WARN] Failed to fetch index data: {e}")
                    index_df = None
        else:
            print(f"[DATA SOURCE] 📈 Using AkShare for {symbol} (Tushare not enabled)")
            stock_df = _retry_akshare_call(
                ak.stock_zh_a_hist,
                symbol=normalized_symbol,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )
            try:
                print(f"[DATA SOURCE] 📈 Using AkShare for index 000300 (HS300)")
                index_df = _retry_akshare_call(
                    ak.index_zh_a_hist,
                    symbol="000300",
                    period="daily",
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d')
                )
            except Exception as e:
                print(f"[WARN] Failed to fetch index data: {e}")
                index_df = None

        if stock_df is None or stock_df.empty or len(stock_df) < 20:
            print(f"[WARN] Insufficient data for {symbol}")
            return None

        stock_df = stock_df.sort_values('日期')

        # 计算MA20和MA5
        stock_df['MA20'] = stock_df['收盘'].rolling(window=20).mean()
        stock_df['MA5'] = stock_df['收盘'].rolling(window=5).mean()

        latest = stock_df.iloc[-1]
        current_price = float(latest['收盘'])
        ma20 = float(latest['MA20'])
        ma5 = float(latest['MA5'])

        # 均线状态
        ma20_status = "站上均线" if current_price > ma20 else "跌破均线"

        # 量能分析
        volume_20 = stock_df.tail(20)['成交量'].mean()
        volume_prev_20 = stock_df.iloc[-40:-20]['成交量'].mean() if len(stock_df) > 40 else volume_20

        if volume_prev_20 > 0:
            volume_change_pct = ((volume_20 - volume_prev_20) / volume_prev_20) * 100
            if volume_change_pct > 10:
                volume_status = "放量"
            elif volume_change_pct < -10:
                volume_status = "缩量"
            else:
                volume_status = "持平"
        else:
            volume_change_pct = 0
            volume_status = "持平"

        # Alpha计算（相对沪深300，使用最近5个交易日）
        if index_df is not None and not index_df.empty:
            index_df = index_df.sort_values('日期')

            # 对齐时间范围 - 使用最近5个交易日
            stock_start_price = float(stock_df.iloc[-5]['收盘'])
            stock_end_price = float(stock_df.iloc[-1]['收盘'])

            index_start_price = float(index_df.iloc[-5]['收盘'])
            index_end_price = float(index_df.iloc[-1]['收盘'])

            stock_return = (stock_end_price - stock_start_price) / stock_start_price * 100
            index_return = (index_end_price - index_start_price) / index_start_price * 100

            alpha = stock_return - index_return
        else:
            alpha = 0.0

        # 健康评分 (0-100)
        health_score = 50

        # MA20状态 (+30 or -30)
        if ma20_status == "站上均线":
            health_score += 30
        else:
            health_score -= 30

        # 量能状态 (+20 or -20)
        if volume_status == "放量":
            health_score += 20
        elif volume_status == "缩量":
            health_score -= 20

        # Alpha (+50 or -50, 限制在 +/-30)
        alpha_score = max(-30, min(30, alpha))
        health_score += alpha_score

        health_score = max(0, min(100, health_score))

        # ===== K线形态识别 =====
        k_line_pattern = "普通震荡"
        pattern_signal = "neutral"

        # 获取最新K线数据
        open_price = float(latest['开盘'])
        high_price = float(latest['最高'])
        low_price = float(latest['最低'])
        close_price = float(latest['收盘'])

        # 计算K线要素
        body = abs(close_price - open_price)  # 实体
        upper_shadow = high_price - max(close_price, open_price)  # 上影线
        lower_shadow = min(close_price, open_price) - low_price  # 下影线
        price_range = high_price - low_price  # 振幅

        # 判断趋势（使用前5天数据判断）
        if len(stock_df) >= 6:
            recent_5 = stock_df.iloc[-6:-1]['收盘'].values
            is_downtrend = recent_5[-1] < recent_5[0]
            is_uptrend = recent_5[-1] > recent_5[0]
        else:
            is_downtrend = False
            is_uptrend = False

        # 形态识别逻辑
        # 1. 金针探底 (Hammer) - 下影线长，发生在下跌趋势中
        if (lower_shadow > 2 * body and lower_shadow > 0.02 * close_price and
            body < 0.03 * close_price and is_downtrend):
            k_line_pattern = "金针探底"
            pattern_signal = "bullish"
            health_score += 15  # 底部支撑，加分

        # 2. 冲高回落 (Shooting Star) - 上影线长
        elif (upper_shadow > 2 * body and upper_shadow > 0.02 * close_price and
              body < 0.03 * close_price):
            k_line_pattern = "冲高回落"
            pattern_signal = "bearish"
            health_score -= 15  # 顶部压力，减分

        # 3. 变盘十字星 (Doji) - 实体极小
        elif body < 0.001 * close_price and price_range > 0.01 * close_price:
            k_line_pattern = "变盘十字星"
            pattern_signal = "warning"

        # 4. 光头大阳线 (Strong Bull) - 大涨，几乎无上影线
        elif (close_price > open_price and
              (close_price - open_price) / open_price > 0.03 and
              upper_shadow < 0.005 * close_price):
            k_line_pattern = "光头大阳线"
            pattern_signal = "bullish"
            health_score += 10

        # 5. 光脚大阴线 (Strong Bear) - 大跌，几乎无下影线
        elif (close_price < open_price and
              (open_price - close_price) / open_price > 0.03 and
              lower_shadow < 0.005 * close_price):
            k_line_pattern = "光脚大阴线"
            pattern_signal = "bearish"
            health_score -= 10

        # MA5状态
        ma5_status = "站上MA5" if current_price > ma5 else "跌破MA5"

        # 生成操作建议信号
        if health_score >= 80:
            action_signal = "STRONG_BUY"
        elif health_score >= 60:
            action_signal = "BUY"
        elif health_score >= 40:
            action_signal = "HOLD"
        elif health_score >= 20:
            action_signal = "SELL"
        else:
            action_signal = "STRONG_SELL"

        # 生成AI分析文本
        analysis_parts = []
        if ma20_status == "站上均线":
            analysis_parts.append("站上MA20均线")
        else:
            analysis_parts.append("跌破MA20均线")

        if alpha > 3:
            analysis_parts.append(f"显著跑赢大盘(+{alpha:.1f}%)")
        elif alpha < -3:
            analysis_parts.append(f"明显弱于大盘({alpha:.1f}%)")
        else:
            analysis_parts.append("与大盘表现相当")

        if volume_status == "放量":
            analysis_parts.append("量价配合良好")
        elif volume_status == "缩量":
            analysis_parts.append("量能萎缩")

        # 根据信号给出建议
        if action_signal in ["STRONG_BUY", "BUY"]:
            advice = "建议积极配置或逢低买入。"
        elif action_signal == "HOLD":
            advice = "建议持有观望。"
        else:
            advice = "建议减仓或止盈防守。"

        analysis = "，".join(analysis_parts) + "。" + advice

        # 投资名言
        quotes = [
            "在别人贪婪时恐惧，在别人恐惧时贪婪。(巴菲特)",
            "时间是优秀企业的朋友。(巴菲特)",
            "趋势是你的朋友。(杰西·利弗莫尔)",
            "截断亏损，让利润奔跑。(亚历山大·埃尔德)",
            "投资最重要的品质是理智，而不是智力。(巴菲特)",
            "股市从短期看是投票机，从长期看是称重机。(巴菲特)"
        ]
        import random
        quote = random.choice(quotes)

        print(f"[OK] {symbol} Technical: MA20={ma20_status}, MA5={ma5_status}, Pattern={k_line_pattern}, Alpha={alpha:.2f}%")

        # 获取日期（确保是字符串格式）
        date_value = latest['日期']
        if isinstance(date_value, str):
            date_str = date_value
        else:
            date_str = str(date_value)

        return {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "ma20": round(ma20, 2),
            "ma5": round(ma5, 2),
            "ma20_status": ma20_status,
            "ma5_status": ma5_status,
            "volume_status": volume_status,
            "volume_change_pct": round(volume_change_pct, 2),
            "alpha": round(alpha, 2),
            "health_score": round(health_score, 0),
            "k_line_pattern": k_line_pattern,
            "pattern_signal": pattern_signal,
            "action_signal": action_signal,
            "analysis": analysis,
            "quote": quote,
            "date": date_str
        }

    except Exception as e:
        print(f"[ERROR] Failed to analyze {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None

