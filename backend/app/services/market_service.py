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

# 数据源选择：优先使用 Tushare，降级到 Baostock，最后是 AkShare
_USE_TUSHARE = True  # 首要数据源
_USE_BAOSTOCK = True  # 备选数据源
_data_fetcher = None

# Always import AkShare as fallback
import akshare as ak

# Import Baostock for A-share data
try:
    from app.services.market_service_baostock import get_financials_baostock
    _BAOSTOCK_AVAILABLE = True
except ImportError:
    _BAOSTOCK_AVAILABLE = False

# 禁用代理，避免网络连接问题
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['NO_PROXY'] = '*'

# 禁用 requests 库的代理
try:
    import requests
    # 备份原始的 Session.request 方法
    _original_request = requests.Session.request

    # 创建新的方法，强制禁用代理
    def _request_no_proxy(self, method, url, *args, **kwargs):
        kwargs.setdefault('proxies', {})
        return _original_request(self, method, url, *args, **kwargs)

    # 替换 Session.request 方法
    requests.Session.request = _request_no_proxy
    print("[INFO] Disabled proxy for requests library")
except Exception as e:
    print(f"[WARN] Failed to disable proxy: {e}")

# 检查是否完全禁用 Tushare
try:
    from app.core.config import settings
    if getattr(settings, 'DISABLE_TUSHARE', False):
        _USE_TUSHARE = False
        print("[DATA SOURCE] Tushare disabled by configuration (DISABLE_TUSHARE=True)")
    else:
        from app.services.data_fetcher import DataFetcher
        _USE_TUSHARE = True
        print("[DATA SOURCE] DataFetcher module found - Tushare Pro support available")
except ImportError:
    print("[DATA SOURCE] DataFetcher module not found - will use AkShare only")

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
                print("[DATA SOURCE] Tushare Pro initialized successfully (Token configured)")
            else:
                print("[DATA SOURCE] TUSHARE_TOKEN not set in environment, falling back to AkShare")
                _USE_TUSHARE = False
                import akshare as ak
        except Exception as e:
            print(f"[DATA SOURCE] Failed to initialize Tushare Pro: {e}")
            print(f"[DATA SOURCE] Falling back to AkShare")
            _USE_TUSHARE = False
            import akshare as ak
    return _data_fetcher


# 本地股票数据库（常见股票）
_STOCK_DATABASE = {
    # A 股 - 科创板 (688xxx)
    '688008': {'name': '澜起科技', 'sector': '科技', 'industry': '半导体'},
    '688012': {'name': '澳华内镜', 'sector': '医疗健康', 'industry': '医疗器械'},
    '688981': {'name': '中芯国际', 'sector': '科技', 'industry': '半导体'},
    '688036': {'name': '传音控股', 'sector': '科技', 'industry': '消费电子'},
    '688111': {'name': '金山办公', 'sector': '科技', 'industry': '软件'},
    '688599': {'name': '天合光能', 'sector': '新能源', 'industry': '光伏'},
    # A 股 - 主板
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
    '002028': {'name': '思源电气', 'sector': '工业', 'industry': '电气设备'},
    '002572': {'name': '索菲亚', 'sector': '消费品', 'industry': '家居'},
    '600584': {'name': '长电科技', 'sector': '科技', 'industry': '半导体'},
    '300124': {'name': '汇川技术', 'sector': '工业', 'industry': '自动化'},
    '601390': {'name': '中国中铁', 'sector': '工业', 'industry': '基建'},
    '601766': {'name': '中国中车', 'sector': '工业', 'industry': '轨道交通'},
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

    优先级: 雪球接口 > Tushare > 东方财富接口

    Returns:
        {
            "name": str,
            "industry": str,
            "sector": str
        }
    """
    try:
        # 方案1: 优先使用雪球接口（更稳定）
        print(f"[INFO] Fetching stock details from 雪球 (xq) for {symbol}...")
        try:
            # 雪球接口需要带交易所前缀
            xq_symbol = symbol
            if len(symbol) == 6:
                if symbol.startswith('6'):
                    xq_symbol = f"SH{symbol}"
                else:
                    xq_symbol = f"SZ{symbol}"

            info_df = ak.stock_individual_basic_info_xq(symbol=xq_symbol, timeout=5)
            if info_df is not None and not info_df.empty:
                info_dict = dict(zip(info_df['item'], info_df['value']))

                stock_name = info_dict.get('org_short_name_cn', None)

                # 解析行业信息（雪球返回的是 dict 类型）
                industry_dict = info_dict.get('affiliate_industry', {})
                industry = None
                if isinstance(industry_dict, dict) and 'ind_name' in industry_dict:
                    industry = industry_dict['ind_name']

                if stock_name:
                    # 根据行业名称推测板块
                    sector = _infer_sector_from_industry(industry) if industry else "其他"

                    print(f"[OK] Got from 雪球: {stock_name}, industry={industry}, sector={sector}")
                    return {
                        "name": stock_name,
                        "industry": industry or "其他",
                        "sector": sector
                    }
        except Exception as e:
            print(f"[WARN] 雪球接口失败: {e}")

        # 方案2: 尝试 Tushare
        if _USE_TUSHARE:
            fetcher = _get_data_fetcher()
            if fetcher:
                print(f"[INFO] Trying Tushare for {symbol}...")
                try:
                    result = fetcher.get_stock_info(symbol)
                    if result:
                        print(f"[OK] Got from Tushare: {result.get('name')}, industry={result.get('industry')}, sector={result.get('sector')}")
                        return result
                except Exception as e:
                    print(f"[WARN] Tushare failed: {e}")

        # 方案3: 降级到东方财富接口
        print(f"[INFO] Trying 东方财富 (em) for {symbol}...")
        info_df = ak.stock_individual_info_em(symbol=symbol)
        if info_df is not None and not info_df.empty:
            # 将DataFrame转换为字典
            info_dict = dict(zip(info_df['item'], info_df['value']))

            stock_name = info_dict.get('股票简称', symbol)
            industry = info_dict.get('所属行业', None)

            if stock_name and stock_name != symbol:
                sector = _infer_sector_from_industry(industry) if industry else "其他"
                print(f"[OK] Got from 东方财富: {stock_name}, industry={industry}, sector={sector}")
                return {
                    "name": stock_name,
                    "industry": industry or "其他",
                    "sector": sector
                }

        print(f"[WARN] All AkShare sources failed for {symbol}")
        return None

    except Exception as e:
        print(f"[ERROR] Failed to fetch stock details: {e}")
        import traceback
        traceback.print_exc()
        return None


def _infer_sector_from_industry(industry: str | None) -> str:
    """根据行业名称推测板块"""
    if not industry:
        return "其他"

    if any(x in industry for x in ['银行', '保险', '证券', '信托']):
        return '金融'
    elif any(x in industry for x in ['医药', '生物', '医疗', '保健']):
        return '医疗健康'
    elif any(x in industry for x in ['电子', '计算机', '软件', '通信', '互联网', '半导体']):
        return '科技'
    elif any(x in industry for x in ['汽车', '新能源', '光伏', '风电', '锂电池']):
        return '新能源'
    elif any(x in industry for x in ['白酒', '食品', '家电', '纺织', '服饰']):
        return '消费品'
    elif any(x in industry for x in ['化工', '钢铁', '有色', '建材']):
        return '材料'
    elif any(x in industry for x in ['电力', '水务', '燃气']):
        return '公用事业'
    elif any(x in industry for x in ['建筑', '装修', '基建', '机械']):
        return '工业'
    elif any(x in industry for x in ['房地产']):
        return '房地产'
    elif any(x in industry for x in ['交通运输', '物流', '航空']):
        return '交通运输'
    elif any(x in industry for x in ['传媒', '娱乐', '教育']):
        return '文化娱乐'
    else:
        return '其他'


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


def _get_baostock_data(symbol: str, start_date, end_date):
    """从 Baostock 获取股票数据"""
    try:
        from app.services.market_service_baostock import get_financials_baostock
        import baostock as bs

        # 登录
        bs.login()

        # 标准化股票代码
        market = 'sh' if symbol.startswith('6') else 'sz'
        bs_symbol = f"{market}.{symbol}"

        # 获取历史数据
        rs = bs.query_history_k_data_plus(
            bs_symbol,
            fields="date,code,open,close,high,low,volume",
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            frequency="d",
            adjustflag="3"
        )

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        bs.logout()

        if not data_list:
            return None

        # 转换为 DataFrame
        import pandas as pd
        df = pd.DataFrame(data_list)
        df.columns = ['日期', '代码', '开盘', '收盘', '最高', '最低', '成交量']
        df['日期'] = pd.to_datetime(df['日期'])
        for col in ['开盘', '收盘', '最高', '最低', '成交量']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df
    except Exception as e:
        print(f"[WARN] Baostock data fetch failed: {e}")
        return None


def _get_akshare_data(symbol, start_date, end_date):
    """从 AkShare 获取股票和指数数据"""
    try:
        # 标准化股票代码
        market = _detect_market_type(symbol)
        normalized_symbol = _normalize_symbol(symbol, market)

        # 获取个股数据
        stock_df = _retry_akshare_call(
            ak.stock_zh_a_hist,
            symbol=normalized_symbol,
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d')
        )

        # 获取沪深300作为基准
        try:
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

        return stock_df, index_df
    except Exception as e:
        print(f"[ERROR] AkShare data fetch failed: {e}")
        return None, None


def _try_tushare_data(symbol, start_date, end_date):
    """尝试使用 Tushare 获取数据，失败则降级到 AkShare"""
    try:
        fetcher = _get_data_fetcher()
        if fetcher:
            print(f"[DATA SOURCE] Using Tushare Pro for {symbol}")
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')

            # 获取个股数据
            stock_df = fetcher.get_stock_daily(
                symbol=_normalize_symbol(symbol, _detect_market_type(symbol)),
                start_date=start_str,
                end_date=end_str
            )

            # 获取沪深300作为基准
            try:
                print(f"[DATA SOURCE] Using Tushare Pro for index 000300 (HS300)")
                index_df = fetcher.get_index_daily(
                    symbol="000300",
                    start_date=start_str,
                    end_date=end_str
                )
            except Exception as e:
                print(f"[WARN] Failed to fetch index data from Tushare: {e}")
                index_df = None

            if stock_df is not None and not stock_df.empty:
                return stock_df, index_df
            else:
                raise Exception("Tushare returned empty data")
        else:
            raise Exception("Tushare not available")
    except Exception as e:
        print(f"[WARN] Tushare failed, falling back to AkShare: {e}")
        return _get_akshare_data(symbol, start_date, end_date)


def get_stock_technical_analysis(symbol: str) -> Optional[Dict]:
    """
    Sentinel Ultra 技术分析 - 引入市场微观结构和筹码分布概念

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
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # 获取更多数据以计算60日均线

        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        print(f"[INFO] Fetching technical data for {symbol}...")

        # 数据源优先级: Tushare → Baostock → AkShare
        stock_df = None
        index_df = None

        # 1. 首先尝试 Tushare
        if _USE_TUSHARE:
            try:
                fetcher = _get_data_fetcher()
                if fetcher:
                    print(f"[DATA SOURCE] Using Tushare Pro for {symbol}")
                    stock_df = fetcher.get_stock_daily(
                        symbol=normalized_symbol,
                        start_date=start_str,
                        end_date=end_str
                    )
                    if stock_df is not None and not stock_df.empty:
                        print(f"[OK] Tushare stock data fetched: {len(stock_df)} records")
                    else:
                        print(f"[WARN] Tushare returned empty data")
                        stock_df = None

                    # 获取沪深300作为基准
                    try:
                        index_df = fetcher.get_index_daily(
                            symbol="000300",
                            start_date=start_str,
                            end_date=end_str
                        )
                    except Exception as e:
                        print(f"[WARN] Failed to fetch index data from Tushare: {e}")
            except Exception as e:
                print(f"[WARN] Tushare failed, trying Baostock: {e}")

        # 2. 备选：尝试 Baostock
        if (stock_df is None or stock_df.empty) and _BAOSTOCK_AVAILABLE:
            try:
                print(f"[DATA SOURCE] Using Baostock for {symbol}")
                stock_df = _get_baostock_data(symbol, start_date, end_date)
                index_df = None  # Baostock 暂不支持指数数据
                if stock_df is not None and not stock_df.empty:
                    print(f"[OK] Baostock stock data fetched: {len(stock_df)} records")
            except Exception as e:
                print(f"[WARN] Baostock failed: {e}")

        # 3. 最后备选：AkShare
        if stock_df is None or stock_df.empty:
            try:
                print(f"[DATA SOURCE] Using AkShare for {symbol}")
                stock_df = _retry_akshare_call(
                    ak.stock_zh_a_hist,
                    symbol=normalized_symbol,
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d')
                )
                if stock_df is not None and not stock_df.empty:
                    print(f"[OK] AkShare stock data fetched: {len(stock_df)} records")

                # 获取沪深300
                try:
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
            except Exception as e:
                print(f"[WARN] AkShare failed: {e}")

        if stock_df is None or stock_df.empty or len(stock_df) < 60:
            print(f"[WARN] Insufficient data for {symbol}")
            return None

        stock_df = stock_df.sort_values('日期').reset_index(drop=True)

        # ========================================
        # 1. 高级指标计算 (使用 Pandas)
        # ========================================

        # 基础均线
        stock_df['MA5'] = stock_df['收盘'].rolling(window=5).mean()
        stock_df['MA20'] = stock_df['收盘'].rolling(window=20).mean()
        stock_df['MA60'] = stock_df['收盘'].rolling(window=60).mean()

        # VWAP (20日成交量加权平均价) - 筹码成本
        stock_df['VWAP_20'] = (stock_df['收盘'] * stock_df['成交量']).rolling(window=20).sum() / \
                                stock_df['成交量'].rolling(window=20).sum()

        # Bollinger Bands (20, 2)
        stock_df['BB_Middle'] = stock_df['收盘'].rolling(window=20).mean()
        std_20 = stock_df['收盘'].rolling(window=20).std()
        stock_df['BB_Upper'] = stock_df['BB_Middle'] + 2 * std_20
        stock_df['BB_Lower'] = stock_df['BB_Middle'] - 2 * std_20
        stock_df['BB_Width'] = (stock_df['BB_Upper'] - stock_df['BB_Lower']) / stock_df['BB_Middle']

        # RSI (14日)
        delta = stock_df['收盘'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        stock_df['RSI_14'] = 100 - (100 / (1 + rs))

        # 获取最新数据
        latest = stock_df.iloc[-1]
        current_price = float(latest['收盘'])
        open_price = float(latest['开盘'])
        high_price = float(latest['最高'])
        low_price = float(latest['最低'])

        ma5 = float(latest['MA5'])
        ma20 = float(latest['MA20'])
        ma60 = float(latest['MA60'])
        vwap_20 = float(latest['VWAP_20']) if not pd.isna(latest['VWAP_20']) else current_price
        bb_upper = float(latest['BB_Upper'])
        bb_middle = float(latest['BB_Middle'])
        bb_lower = float(latest['BB_Lower'])
        bandwidth = float(latest['BB_Width'])
        rsi_14 = float(latest['RSI_14']) if not pd.isna(latest['RSI_14']) else 50

        # 换手率 (如果AkShare数据中包含)
        turnover = None
        if '换手率' in stock_df.columns:
            turnover = float(latest['换手率']) if not pd.isna(latest['换手率']) else None

        # 均线状态
        ma20_status = "站上均线" if current_price > ma20 else "跌破均线"
        ma5_status = "站上MA5" if current_price > ma5 else "跌破MA5"

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

        # 价格变化
        price_change = (current_price - float(stock_df.iloc[-2]['收盘'])) / float(stock_df.iloc[-2]['收盘'])

        # Alpha计算（相对沪深300，使用最近5个交易日）
        if index_df is not None and not index_df.empty:
            index_df = index_df.sort_values('日期')
            stock_start_price = float(stock_df.iloc[-5]['收盘'])
            stock_end_price = current_price
            index_start_price = float(index_df.iloc[-5]['收盘'])
            index_end_price = float(index_df.iloc[-1]['收盘'])
            stock_return = (stock_end_price - stock_start_price) / stock_start_price * 100
            index_return = (index_end_price - index_start_price) / index_start_price * 100
            alpha = stock_return - index_return
        else:
            alpha = 0.0

        # ========================================
        # 2. Sentinel Ultra 评分逻辑 (核心算法)
        # ========================================

        health_score = 50  # 基础分

        # --- A. 筹码与成本 (VWAP) [权重 ±15] ---
        # 逻辑：价格在成本之上=获利盘(支撑)；在成本之下=套牢盘(压力)
        if current_price > vwap_20:
            health_score += 15
        else:
            health_score -= 15

        # --- B. 趋势与均线 (Trend) [权重 ±20] ---
        # 逻辑：保留 Pro 版的缓冲带逻辑
        pct_diff_ma20 = (current_price - ma20) / ma20
        if pct_diff_ma20 > 0.03:
            health_score += 15
        elif 0 < pct_diff_ma20 <= 0.03:
            health_score += 5
        elif -0.03 <= pct_diff_ma20 <= 0:
            health_score -= 5
        else:
            health_score -= 15

        if current_price > ma60:
            health_score += 5  # 长期趋势加分

        # --- C. 爆发潜力 (Bollinger Squeeze) [权重 +10] ---
        # 逻辑：低波动率意味着变盘在即。配合趋势向上是绝佳买点。
        if bandwidth < 0.15:  # 布林带极度收窄
            if current_price > ma20:  # 趋势向上且收窄 -> 蓄势待发
                health_score += 10
            else:  # 趋势向下且收窄 -> 可能暴跌
                health_score -= 5

        # --- D. 活跃度 (Turnover) [权重 ±10] ---
        # 逻辑：拒绝僵尸股，警惕过热股
        if turnover is not None:
            if turnover < 1.0:
                health_score -= 10  # 僵尸股
            elif 3.0 <= turnover <= 12.0:
                health_score += 10  # 黄金活跃区
            elif turnover > 20.0:
                health_score -= 10  # 情绪过热风险

        # --- E. 量价配合 (Volume) [权重 ±15] ---
        # 逻辑：保留 Pro 版 (缩量回调是好事)
        if price_change > 0:
            if volume_status == "放量":
                health_score += 15
            elif volume_status == "缩量":
                health_score -= 5
        else:
            if volume_status == "放量":
                health_score -= 15
            elif volume_status == "缩量":
                health_score += 10  # 惜售/洗盘

        # --- F. 情绪风控 (RSI) [权重 -20 ~ +10] ---
        if rsi_14 > 80:
            health_score -= 20  # 超买惩罚
        elif rsi_14 < 20:
            health_score += 10  # 超跌奖励

        # Final Clamp
        health_score = max(0, min(100, health_score))

        # K线形态识别 (保留原逻辑，但权重降低)
        k_line_pattern = "普通震荡"
        pattern_signal = "neutral"

        body = abs(current_price - open_price)
        upper_shadow = high_price - max(current_price, open_price)
        lower_shadow = min(current_price, open_price) - low_price
        price_range = high_price - low_price

        if len(stock_df) >= 6:
            recent_5 = stock_df.iloc[-6:-1]['收盘'].values
            is_downtrend = recent_5[-1] < recent_5[0]
            is_uptrend = recent_5[-1] > recent_5[0]
        else:
            is_downtrend = False
            is_uptrend = False

        # 形态识别 (权重降低到 +/- 5)
        if (lower_shadow > 2 * body and lower_shadow > 0.02 * current_price and
            body < 0.03 * current_price and is_downtrend):
            k_line_pattern = "金针探底"
            pattern_signal = "bullish"
            health_score = min(100, health_score + 5)
        elif (upper_shadow > 2 * body and upper_shadow > 0.02 * current_price and
              body < 0.03 * current_price):
            k_line_pattern = "冲高回落"
            pattern_signal = "bearish"
            health_score = max(0, health_score - 5)
        elif body < 0.001 * current_price and price_range > 0.01 * current_price:
            k_line_pattern = "变盘十字星"
            pattern_signal = "warning"
        elif (current_price > open_price and
              (current_price - open_price) / open_price > 0.03 and
              upper_shadow < 0.005 * current_price):
            k_line_pattern = "光头大阳线"
            pattern_signal = "bullish"
            health_score = min(100, health_score + 5)
        elif (current_price < open_price and
              (open_price - current_price) / open_price > 0.03 and
              lower_shadow < 0.005 * current_price):
            k_line_pattern = "光脚大阴线"
            pattern_signal = "bearish"
            health_score = max(0, health_score - 5)

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

        # 生成AI分析文本 (增强版，包含新指标)
        analysis_parts = []

        # 趋势分析
        if current_price > ma20:
            analysis_parts.append("站上MA20均线")
            if current_price > vwap_20:
                analysis_parts.append("高于筹码成本(VWAP)")
        else:
            analysis_parts.append("跌破MA20均线")
            if current_price < vwap_20:
                analysis_parts.append("低于筹码成本")

        # 布林带分析
        if bandwidth < 0.15:
            if current_price > ma20:
                analysis_parts.append("布林带收窄蓄势待发")
            else:
                analysis_parts.append("布林带收窄需谨慎")
        elif current_price > bb_upper:
            analysis_parts.append("突破布林带上轨")
        elif current_price < bb_lower:
            analysis_parts.append("跌破布林带下轨")

        # Alpha分析
        if alpha > 3:
            analysis_parts.append(f"显著跑赢大盘(+{alpha:.1f}%)")
        elif alpha < -3:
            analysis_parts.append(f"明显弱于大盘({alpha:.1f}%)")

        # RSI分析
        if rsi_14 > 70:
            analysis_parts.append("RSI超买警惕回调")
        elif rsi_14 < 30:
            analysis_parts.append("RSI超跌可能反弹")

        # 换手率分析
        if turnover is not None:
            if turnover < 1:
                analysis_parts.append("交投冷清")
            elif turnover > 15:
                analysis_parts.append("交投过度活跃")

        # 根据信号给出建议
        if action_signal in ["STRONG_BUY", "BUY"]:
            advice = "建议积极配置或逢低买入。"
        elif action_signal == "HOLD":
            advice = "建议持有观望。"
        else:
            advice = "建议减仓或止盈防守。"

        analysis = "，".join(analysis_parts) + "。" + advice

        # 投资名言 (保留)
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

        print(f"[OK] {symbol} Sentinel Ultra: Score={health_score}, VWAP={vwap_20:.2f}, "
              f"BB_Width={bandwidth:.3f}, RSI={rsi_14:.1f}, Turnover={turnover}")

        # 获取日期
        date_value = latest['日期']
        if isinstance(date_value, str):
            date_str = date_value
        else:
            date_str = str(date_value)

        return {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "ma5": round(ma5, 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
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
            # 新增高级指标
            "vwap_20": round(vwap_20, 2),
            "bollinger_upper": round(bb_upper, 2),
            "bollinger_middle": round(bb_middle, 2),
            "bollinger_lower": round(bb_lower, 2),
            "bandwidth": round(bandwidth, 4),
            "turnover": round(turnover, 2) if turnover is not None else None,
            "rsi_14": round(rsi_14, 2),
            "date": date_str
        }

    except Exception as e:
        print(f"[ERROR] Failed to analyze {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================
# 市场快照 - 实时财务指标
# ============================================

def get_market_snapshot(symbol: str) -> Optional[Dict]:
    """
    获取股票市场快照数据，包含实时价格和核心财务指标

    专为 A 股设计，支持机构级投资决策

    Args:
        symbol: A 股代码 (6位数字)

    Returns:
        {
            "symbol": str,
            "current_price": float,
            "price_change": float,
            "price_change_pct": float,
            "fundamentals": {
                "pe_ttm": float,          # 市盈率-TTM
                "pb": float,              # 市净率
                "total_mv": float,        # 总市值(亿元)
                "turnover": float,        # 换手率(%)
                "roe": float,             # ROE估算(%)
                "volume_ratio": float     # 量比
            }
        }
    """
    market = _detect_market_type(symbol)
    normalized_symbol = _normalize_symbol(symbol, market)

    if market != 'A':
        print(f"[WARN] Market snapshot only supports A-shares, not {market}")
        return None

    try:
        print(f"[INFO] Fetching market snapshot for {symbol}...")

        # 获取实时行情数据
        spot_info = _retry_akshare_call(ak.stock_zh_a_spot_em, timeout=10)

        if spot_info is None or spot_info.empty:
            print(f"[WARN] Failed to fetch spot data for {symbol}")
            return None

        stock_info = spot_info[spot_info['代码'] == normalized_symbol]

        if stock_info.empty:
            print(f"[WARN] Symbol {symbol} not found in spot data")
            return None

        stock_row = stock_info.iloc[0]

        # 基础价格数据
        current_price = _safe_float(stock_row.get('最新价', 0))
        price_change = _safe_float(stock_row.get('涨跌幅', 0))

        # 计算涨跌额
        open_price = _safe_float(stock_row.get('今开', 0))
        if open_price and open_price > 0:
            price_change_amt = current_price - open_price
        else:
            price_change_amt = 0

        # 获取个股财务指标
        fundamentals = {}

        try:
            pe_ttm = _safe_float(stock_row.get('市盈率-动态', 0))
            pb = _safe_float(stock_row.get('市净率', 0))
            total_mv_raw = _safe_float(stock_row.get('总市值', 0))
            turnover = _safe_float(stock_row.get('换手率', 0))
            volume_ratio = _safe_float(stock_row.get('量比', 1))

            # 转换市值单位: 元 → 亿元
            total_mv = (total_mv_raw / 100000000) if total_mv_raw else 0

            # 简单的 ROE 估算: PB / PE * 100
            roe = (pb / pe_ttm * 100) if pe_ttm and pe_ttm > 0 else 0

            fundamentals = {
                "pe_ttm": round(pe_ttm, 2) if pe_ttm else None,
                "pb": round(pb, 2) if pb else None,
                "total_mv": round(total_mv, 2) if total_mv else None,
                "turnover": round(turnover, 2) if turnover else None,
                "roe": round(roe, 2) if roe else None,
                "volume_ratio": round(volume_ratio, 2) if volume_ratio else None
            }

            print(f"[OK] {symbol} PE:{pe_ttm} PB:{pb} MV:{total_mv}亿 ROE:{roe:.2f}%")

        except Exception as e:
            print(f"[WARN] Failed to extract fundamentals for {symbol}: {e}")
            fundamentals = {"error": "数据缺失"}

        result = {
            "symbol": symbol.upper(),
            "current_price": round(current_price, 2) if current_price else None,
            "price_change": round(price_change_amt, 2),
            "price_change_pct": round(price_change, 2) if price_change else 0,
            "fundamentals": fundamentals,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        return result

    except Exception as e:
        print(f"[ERROR] Failed to get market snapshot for {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================
# 新闻标题获取 - 支持全脑协同分析
# ============================================

def get_news_titles(symbol: str, limit: int = 5) -> list:
    """
    获取股票相关新闻标题

    Args:
        symbol: A股代码
        limit: 返回数量

    Returns:
        新闻标题列表
    """
    try:
        # 使用AkShare获取股票新闻
        news_data = _retry_akshare_call(
            lambda: ak.stock_news_em(symbol=symbol),
            timeout=10
        )
        if news_data is not None and not news_data.empty:
            return news_data['新闻标题'].head(limit).tolist()
    except Exception as e:
        print(f"[WARN] Failed to get news for {symbol}: {e}")

    return []


# ============================================
# 财务指标分析 - 支持 AI 投委会
# ============================================

def calculate_financial_metrics(symbol: str) -> Dict:
    """
    计算股票的硬核财务指标，为 AI 投委会提供数据支撑

    支持 A 股财务指标计算：
    - Warren Buffett (价值因子): ROE, Debt-to-Equity, FCF Yield
    - Cathie Wood (成长因子): Revenue Growth CAGR, PEG, R&D Intensity
    - Jim Simons (动量因子): RSI(14), Beta

    Args:
        symbol: A 股代码 (6位数字)

    Returns:
        {
            "symbol": str,
            "market": str,
            "metrics": {
                # 价值因子
                "roe": float | None,
                "debt_to_equity": float | None,
                "fcf_yield": float | None,
                "pe_ratio": float | None,
                "pb_ratio": float | None,
                # 成长因子
                "revenue_growth_cagr": float | None,
                "peg_ratio": float | None,
                "rd_intensity": float | None,
                # 动量因子
                "rsi_14": float | None,
                "beta": float | None,
                "volatility": float | None,
            },
            "context": str,  # 格式化的文本上下文，直接喂给 LLM
        }
    """
    market = _detect_market_type(symbol)
    normalized_symbol = _normalize_symbol(symbol, market)

    if market != 'A':
        print(f"[WARN] Financial metrics only supports A-shares, not {market}")
        return {
            "symbol": symbol.upper(),
            "market": market,
            "metrics": {},
            "context": f"Financial metrics not available for {market} stocks."
        }

    try:
        print(f"[INFO] Calculating financial metrics for {symbol}...")

        # ============================================
        # 优先使用 Tushare 获取数据
        # ============================================
        fundamental_data = {}
        stock_df = None
        index_df = None

        if _USE_TUSHARE:
            try:
                fetcher = _get_data_fetcher()
                if fetcher:
                    print(f"[DATA SOURCE] Using Tushare Pro for {symbol} financial metrics")

                    # 使用 Tushare 获取价格数据
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=120)
                    start_str = start_date.strftime('%Y%m%d')
                    end_str = end_date.strftime('%Y%m%d')

                    stock_df = fetcher.get_stock_daily(
                        symbol=normalized_symbol,
                        start_date=start_date.strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d')
                    )

                    if stock_df is not None and not stock_df.empty:
                        print(f"[OK] Tushare price data fetched: {len(stock_df)} records")
                    else:
                        print(f"[WARN] Tushare returned empty data, falling back to AkShare")
                        stock_df = None

                    # 获取沪深300数据
                    try:
                        index_df = fetcher.get_index_daily(
                            symbol="000300",
                            start_date=start_date.strftime('%Y-%m-%d'),
                            end_date=end_date.strftime('%Y-%m-%d')
                        )
                    except Exception as e:
                        print(f"[WARN] Failed to fetch index data from Tushare: {e}")
                        index_df = None
            except Exception as e:
                print(f"[WARN] Tushare financial metrics failed: {e}, falling back to AkShare")

        # ============================================
        # 1. 获取价格数据 (如果 Tushare 失败，使用 AkShare)
        # ============================================
        if stock_df is None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=120)
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')

            stock_df = _retry_akshare_call(
                ak.stock_zh_a_hist,
                symbol=normalized_symbol,
                period="daily",
                start_date=start_str,
                end_date=end_str
            )

        if stock_df is None or stock_df.empty or len(stock_df) < 20:
            print(f"[WARN] Insufficient price data for {symbol}")
            return _build_financial_fallback(symbol, market, "Insufficient price data")

        stock_df = stock_df.sort_values('日期')

        # 获取沪深300数据 (用于计算 Beta)
        if index_df is None:
            index_df = _retry_akshare_call(
                ak.index_zh_a_hist,
                symbol="000300",
                period="daily",
                start_date=start_str,
                end_date=end_str
            )

        # ============================================
        # 2. 获取基本面数据 (Tushare → Baostock → AkShare)
        # ============================================
        fundamental_data = {}

        # 优先使用 Tushare 获取财务指标
        if _USE_TUSHARE:
            try:
                fetcher = _get_data_fetcher()
                if fetcher:
                    print(f"[DATA SOURCE] Using Tushare Pro for {symbol} fundamental metrics")

                    # 使用 daily_basic 获取 PE, PB, 市值
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)

                    daily_basic_df = fetcher.get_daily_basic(
                        symbol=normalized_symbol,
                        start_date=start_date.strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d')
                    )

                    if daily_basic_df is not None and not daily_basic_df.empty:
                        latest = daily_basic_df.iloc[-1]
                        fundamental_data['pe_ratio'] = _safe_float(latest.get('pe_ttm', None))
                        fundamental_data['pb_ratio'] = _safe_float(latest.get('pb', None))
                        fundamental_data['market_cap'] = _safe_float(latest.get('total_mv', None))
                        fundamental_data['current_price'] = _safe_float(latest.get('close', None))
                        print(f"[OK] Tushare daily_basic: PE={fundamental_data.get('pe_ratio')}, PB={fundamental_data.get('pb_ratio')}")

                    # 使用 fina_indicator 获取 ROE, 资产负债率
                    fina_indicator_df = fetcher.get_financial_indicator(
                        symbol=normalized_symbol,
                        start_date=(end_date - timedelta(days=365)).strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d')
                    )

                    if fina_indicator_df is not None and not fina_indicator_df.empty:
                        latest = fina_indicator_df.iloc[-1]
                        fundamental_data['roe'] = _safe_float(latest.get('roe', None))
                        fundamental_data['debt_to_equity'] = _safe_float(latest.get('debt_to_assets', None))
                        print(f"[OK] Tushare fina_indicator: ROE={fundamental_data.get('roe')}, D/E={fundamental_data.get('debt_to_equity')}")

                    # 如果所有数据都已获取，跳过后续数据源
                    if all(fundamental_data.get(k) is not None for k in ['pe_ratio', 'pb_ratio', 'roe']):
                        print(f"[OK] Tushare complete data, skipping other sources")
            except Exception as e:
                print(f"[WARN] Tushare fundamental metrics failed: {e}")

        # 备选：使用 Baostock 获取财务指标
        if _BAOSTOCK_AVAILABLE and _USE_BAOSTOCK and not fundamental_data.get('pe_ratio'):
            try:
                print(f"[DATA SOURCE] Using Baostock for {symbol} financial metrics")
                baostock_result = get_financials_baostock(symbol)
                if baostock_result and baostock_result.get('metrics'):
                    metrics = baostock_result['metrics']
                    if not fundamental_data.get('pe_ratio'):
                        fundamental_data['pe_ratio'] = metrics.get('pe_ratio')
                    if not fundamental_data.get('pb_ratio'):
                        fundamental_data['pb_ratio'] = metrics.get('pb_ratio')
                    if not fundamental_data.get('roe'):
                        fundamental_data['roe'] = metrics.get('roe')
                    if not fundamental_data.get('debt_to_equity'):
                        fundamental_data['debt_to_equity'] = metrics.get('debt_to_equity')
                    if not fundamental_data.get('revenue_growth_cagr'):
                        fundamental_data['revenue_growth_cagr'] = metrics.get('revenue_growth_cagr')
                    if not fundamental_data.get('current_price'):
                        fundamental_data['current_price'] = metrics.get('current_price')
                    if not fundamental_data.get('market_cap'):
                        fundamental_data['market_cap'] = metrics.get('market_cap')
                    print(f"[OK] Baostock financial data: PE={fundamental_data.get('pe_ratio')}, ROE={fundamental_data.get('roe')}")
            except Exception as e:
                print(f"[WARN] Baostock financial metrics failed: {e}")

        try:
            # 获取个股信息 (包含 PE, PB)
            stock_info = ak.stock_zh_a_spot_em()
            if stock_info is not None and not stock_info.empty:
                stock_row = stock_info[stock_info['代码'] == normalized_symbol]
                if not stock_row.empty:
                    fundamental_data['pe_ratio'] = _safe_float(stock_row.iloc[0].get('市盈率-动态', None))
                    fundamental_data['pb_ratio'] = _safe_float(stock_row.iloc[0].get('市净率', None))
                    fundamental_data['market_cap'] = _safe_float(stock_row.iloc[0].get('总市值', None))
        except Exception as e:
            print(f"[WARN] Failed to fetch spot data: {e}")

        try:
            # 获取财务数据 (ROE, 负债率, 研发投入等)
            # AkShare 财务接口: ak.stock_financial_analysis_indicator_em
            financial_df = ak.stock_financial_analysis_indicator_em(symbol=normalized_symbol)
            if financial_df is not None and not financial_df.empty:
                # 获取最新一期的财务数据
                latest = financial_df.iloc[0]
                fundamental_data['roe'] = _safe_float(latest.get('净资产收益率', None))
                fundamental_data['debt_to_equity'] = _safe_float(latest.get('资产负债率', None))
                fundamental_data['rd_expense'] = _safe_float(latest.get('研发费用', None))
        except Exception as e:
            print(f"[WARN] Failed to fetch financial analysis: {e}")

        try:
            # 获取现金流数据 (用于 FCF Yield)
            cashflow_df = ak.stock_cash_flow_sheet_by_report_em(symbol=normalized_symbol)
            if cashflow_df is not None and not cashflow_df.empty:
                latest_cf = cashflow_df.iloc[0]
                # 经营活动现金流
                ocf = _safe_float(latest_cf.get('经营活动产生的现金流量净额', None))
                fundamental_data['operating_cash_flow'] = ocf
        except Exception as e:
            print(f"[WARN] Failed to fetch cash flow data: {e}")

        try:
            # 获取营收数据 (用于计算 CAGR)
            profit_df = ak.stock_profit_sheet_by_report_em(symbol=normalized_symbol)
            if profit_df is not None and not profit_df.empty and len(profit_df) >= 3:
                # 获取最近3年的营收数据
                revenues = []
                for i in range(min(3, len(profit_df))):
                    revenue = _safe_float(profit_df.iloc[i].get('营业总收入', None))
                    if revenue:
                        revenues.append(revenue)

                if len(revenues) >= 2:
                    # 计算 CAGR
                    cagr = _calculate_cagr(revenues)
                    fundamental_data['revenue_growth_cagr'] = cagr
        except Exception as e:
            print(f"[WARN] Failed to fetch profit data: {e}")

        # ============================================
        # 3. 计算动量指标 (RSI, Beta, Volatility)
        # ============================================
        momentum_metrics = _calculate_momentum_metrics(stock_df, index_df)

        # ============================================
        # 4. 组装最终指标
        # ============================================
        latest_price = float(stock_df.iloc[-1]['收盘'])

        # PEG Ratio 计算
        pe_ratio = fundamental_data.get('pe_ratio')
        revenue_cagr = fundamental_data.get('revenue_growth_cagr')
        peg_ratio = None
        if pe_ratio and revenue_cagr and revenue_cagr != 0:
            peg_ratio = pe_ratio / (revenue_cagr * 100)  # PE / (增长率% * 100)

        # FCF Yield 计算
        market_cap = fundamental_data.get('market_cap')
        ocf = fundamental_data.get('operating_cash_flow')
        fcf_yield = None
        if market_cap and market_cap > 0 and ocf:
            # 如果有自由现金流数据更好，这里用经营现金流替代
            fcf_yield = (ocf / market_cap) * 100

        # R&D Intensity 计算
        rd_expense = fundamental_data.get('rd_expense')
        rd_intensity = None
        if rd_expense and revenue_cagr:
            # 研发费用 / 营收 (这里用最新营收估计)
            latest_revenue = None
            if 'revenues' in locals() and len(revenues) > 0:
                latest_revenue = revenues[0]
            if latest_revenue and latest_revenue > 0:
                rd_intensity = (rd_expense / latest_revenue) * 100

        metrics = {
            # 价值因子
            "roe": fundamental_data.get('roe'),
            "debt_to_equity": fundamental_data.get('debt_to_equity'),
            "fcf_yield": fcf_yield,
            "pe_ratio": pe_ratio,
            "pb_ratio": fundamental_data.get('pb_ratio'),
            # 成长因子
            "revenue_growth_cagr": revenue_cagr,
            "peg_ratio": peg_ratio,
            "rd_intensity": rd_intensity,
            # 动量因子
            "rsi_14": momentum_metrics.get('rsi_14'),
            "beta": momentum_metrics.get('beta'),
            "volatility": momentum_metrics.get('volatility'),
        }

        # 生成文本上下文
        context = _format_financial_context(symbol, latest_price, metrics)

        print(f"[OK] Financial metrics calculated for {symbol}")

        return {
            "symbol": symbol.upper(),
            "market": market,
            "metrics": metrics,
            "context": context
        }

    except Exception as e:
        print(f"[ERROR] Failed to calculate financial metrics for {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return _build_financial_fallback(symbol, market, str(e))


def _safe_float(value) -> Optional[float]:
    """安全地将值转换为 float"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _calculate_cagr(values: list) -> Optional[float]:
    """
    计算复合增长率 (CAGR)

    Formula: (Ending Value / Beginning Value)^(1/n) - 1
    """
    if not values or len(values) < 2:
        return None

    try:
        begin_value = values[-1]  # 最早的值
        end_value = values[0]      # 最新的值
        n = len(values) - 1

        if begin_value <= 0 or end_value <= 0:
            return None

        cagr = ((end_value / begin_value) ** (1 / n) - 1) * 100
        return cagr
    except Exception:
        return None


def _calculate_momentum_metrics(stock_df: pd.DataFrame, index_df: pd.DataFrame) -> Dict:
    """
    计算动量指标 (RSI, Beta, Volatility)
    """
    metrics = {}

    try:
        # 计算 RSI (14)
        close_prices = stock_df['收盘'].values
        delta = pd.Series(close_prices).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        metrics['rsi_14'] = float(rsi.iloc[-1])
    except Exception as e:
        print(f"[WARN] Failed to calculate RSI: {e}")

    try:
        # 计算 Beta (相对沪深300)
        if index_df is not None and not index_df.empty:
            # 对齐时间序列
            stock_returns = stock_df['收盘'].pct_change().dropna()
            index_returns = index_df['收盘'].pct_change().dropna()

            # 计算协方差和方差
            if len(stock_returns) > 30 and len(index_returns) > 30:
                min_len = min(len(stock_returns), len(index_returns))
                covariance = stock_returns.iloc[:min_len].cov(index_returns.iloc[:min_len])
                index_variance = index_returns.iloc[:min_len].var()

                if index_variance > 0:
                    beta = covariance / index_variance
                    metrics['beta'] = float(beta)
    except Exception as e:
        print(f"[WARN] Failed to calculate Beta: {e}")

    try:
        # 计算 Volatility (年化波动率)
        returns = stock_df['收盘'].pct_change().dropna()
        if len(returns) > 0:
            volatility = returns.std() * (252 ** 0.5) * 100  # 年化
            metrics['volatility'] = float(volatility)
    except Exception as e:
        print(f"[WARN] Failed to calculate volatility: {e}")

    return metrics


def _format_financial_context(symbol: str, price: float, metrics: Dict) -> str:
    """
    将财务指标格式化为 LLM 可读的文本上下文
    """
    lines = [
        f"## {symbol} - Financial Analysis Dashboard",
        f"Current Price: ¥{price:.2f}",
        "",
        "### Warren Buffett (Value Factors):",
    ]

    # 价值因子
    roe = metrics.get('roe')
    debt_to_equity = metrics.get('debt_to_equity')
    fcf_yield = metrics.get('fcf_yield')

    lines.append(f"- **ROE (净资产收益率)**: {roe:.2f}%" if roe is not None else "- **ROE**: N/A")
    lines.append(f"  → {'Excellent (>20%)' if roe and roe > 20 else 'Good (>15%)' if roe and roe > 15 else 'Mediocre' if roe else 'No data'}")

    lines.append(f"- **Debt-to-Equity (产权比率)**: {debt_to_equity:.2f}" if debt_to_equity is not None else "- **D/E**: N/A")
    lines.append(f"  → {'Conservative (<0.3)' if debt_to_equity and debt_to_equity < 0.3 else 'Manageable (<1.0)' if debt_to_equity and debt_to_equity < 1.0 else 'Risky (>1.0)' if debt_to_equity else 'No data'}")

    lines.append(f"- **FCF Yield (自由现金流收益率)**: {fcf_yield:.2f}%" if fcf_yield is not None else "- **FCF Yield**: N/A")
    lines.append(f"  → {'Beats bonds (>4%)' if fcf_yield and fcf_yield > 4 else 'Underperforms bonds' if fcf_yield else 'No data'}")

    # 成长因子
    lines.extend([
        "",
        "### Cathie Wood (Growth Factors):",
    ])

    revenue_cagr = metrics.get('revenue_growth_cagr')
    peg_ratio = metrics.get('peg_ratio')
    rd_intensity = metrics.get('rd_intensity')

    lines.append(f"- **Revenue Growth CAGR (3年营收复合增长)**: {revenue_cagr:.2f}%" if revenue_cagr is not None else "- **Revenue Growth**: N/A")
    lines.append(f"  → {'Hypergrowth (>30%)' if revenue_cagr and revenue_cagr > 30 else 'Strong (>20%)' if revenue_cagr and revenue_cagr > 20 else 'Moderate' if revenue_cagr else 'No data'}")

    lines.append(f"- **PEG Ratio**: {peg_ratio:.2f}" if peg_ratio is not None else "- **PEG**: N/A")
    lines.append(f"  → {'Undervalued (<1.0)' if peg_ratio and peg_ratio < 1.0 else 'Fair (1.0-2.0)' if peg_ratio and peg_ratio <= 2.0 else 'Overvalued (>2.0)' if peg_ratio else 'No data'}")

    lines.append(f"- **R&D Intensity (研发费用占比)**: {rd_intensity:.2f}%" if rd_intensity is not None else "- **R&D Intensity**: N/A")
    lines.append(f"  → {'True innovator (>15%)' if rd_intensity and rd_intensity > 15 else 'Adequate (>10%)' if rd_intensity and rd_intensity >= 10 else 'Fake tech (<10%)' if rd_intensity else 'No data'}")

    # 动量因子
    lines.extend([
        "",
        "### Jim Simons (Momentum Factors):",
    ])

    rsi = metrics.get('rsi_14')
    beta = metrics.get('beta')
    volatility = metrics.get('volatility')

    lines.append(f"- **RSI (14)**: {rsi:.2f}" if rsi is not None else "- **RSI**: N/A")
    lines.append(f"  → {'Oversold (<30)' if rsi and rsi < 30 else 'Overbought (>70)' if rsi and rsi > 70 else 'Neutral' if rsi else 'No data'}")

    lines.append(f"- **Beta**: {beta:.2f}" if beta is not None else "- **Beta**: N/A")
    lines.append(f"  → {'Low volatility (<0.8)' if beta and beta < 0.8 else 'High volatility (>1.5)' if beta and beta > 1.5 else 'Normal' if beta else 'No data'}")

    lines.append(f"- **Volatility (年化波动率)**: {volatility:.2f}%" if volatility is not None else "- **Volatility**: N/A")

    return "\n".join(lines)


def _build_financial_fallback(symbol: str, market: str, error: str) -> Dict:
    """构建财务指标的降级响应"""
    return {
        "symbol": symbol.upper(),
        "market": market,
        "metrics": {
            "roe": None,
            "debt_to_equity": None,
            "fcf_yield": None,
            "pe_ratio": None,
            "pb_ratio": None,
            "revenue_growth_cagr": None,
            "peg_ratio": None,
            "rd_intensity": None,
            "rsi_14": None,
            "beta": None,
            "volatility": None,
        },
        "context": f"## {symbol.upper()} - Financial Data Unavailable\n\nUnable to fetch financial metrics due to: {error}\n\nPlease try again later or use default analysis."
    }


# ============================================
# Tushare 主营业务获取 - 解决行业幻觉问题
# ============================================

def get_stock_main_business_tushare(symbol: str) -> Optional[Dict]:
    """
    从 Tushare 获取股票的主营业务信息，解决 AI 行业幻觉问题

    Args:
        symbol: A股代码 (6位数字)

    Returns:
        {
            "symbol": str,
            "main_business": str,      # 主营业务描述
            "business_scope": str,     # 经营范围
            "industry": str,           # 所属行业
            "area": str,               # 所在地
            "name": str,               # 股票名称
            "source": "tushare_custom"
        }
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()

        # 自定义 Tushare 配置
        _CUSTOM_TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', '')
        _CUSTOM_TUSHARE_URL = 'http://lianghua.nanyangqiankun.top'

        if not _CUSTOM_TUSHARE_TOKEN:
            print("[TUSHARE] No TUSHARE_TOKEN configured")
            return None

        import tushare as ts

        # 配置自定义代理
        pro = ts.pro_api(_CUSTOM_TUSHARE_TOKEN)
        pro._DataApi__token = _CUSTOM_TUSHARE_TOKEN
        pro._DataApi__http_url = _CUSTOM_TUSHARE_URL

        print(f"[TUSHARE] Fetching main_business for {symbol}...")

        # 标准化股票代码格式为 Tushare 格式 (如 600519.SH)
        ts_symbol = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"

        result = {
            "symbol": symbol,
            "main_business": "",
            "business_scope": "",
            "industry": "",
            "area": "",
            "name": "",
            "source": "tushare_custom"
        }

        # 从 stock_basic 获取基础信息
        try:
            basic_data = pro.stock_basic(ts_code=ts_symbol, fields='ts_code,name,industry,area,list_date')
            if basic_data is not None and not basic_data.empty:
                row = basic_data.iloc[0]
                result["industry"] = row.get("industry", "")
                result["area"] = row.get("area", "")
                result["name"] = row.get("name", "")
        except Exception as e:
            print(f"[TUSHARE] Failed to fetch basic data: {e}")

        # 尝试获取公司信息 (包含主营业务)
        try:
            company_data = pro.stock_company(ts_code=ts_symbol, fields='ts_code,main_business,business_scope')
            if company_data is not None and not company_data.empty:
                row = company_data.iloc[0]
                result["main_business"] = row.get("main_business", "")
                result["business_scope"] = row.get("business_scope", "")
        except Exception as e:
            print(f"[TUSHARE] Failed to fetch company data: {e}")

        # 如果还是没有，尝试从 income 接口获取业务构成
        if not result["main_business"]:
            try:
                from datetime import datetime
                current_year = datetime.now().year
                income_data = pro.income(ts_code=ts_symbol, period=str(current_year), fields='ts_code,ann_date,main_business')
                if income_data is not None and not income_data.empty:
                    latest = income_data.iloc[-1]
                    result["main_business"] = latest.get("main_business", "")
            except Exception as e:
                print(f"[TUSHARE] Failed to fetch income data: {e}")

        print(f"[TUSHARE] Got main_business for {symbol}: {result['main_business'][:100] if result['main_business'] else 'N/A'}...")

        return result if result["main_business"] or result["industry"] else None

    except Exception as e:
        print(f"[ERROR] Tushare main_business fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================
# 新闻数据 - 支持情绪分析
# ============================================

def get_news_titles(symbol: str, limit: int = 5) -> str:
    """
    获取股票相关新闻标题，用于情绪分析

    Args:
        symbol: A股代码 (6位数字)
        limit: 返回新闻数量

    Returns:
        新闻标题文本（用分号分隔）
    """
    market = _detect_market_type(symbol)
    normalized_symbol = _normalize_symbol(symbol, market)

    if market != 'A':
        return "[新闻] 仅支持A股"

    try:
        print(f"[INFO] Fetching news for {symbol}...")

        # 使用AkShare获取新闻标题
        news_df = _retry_akshare_call(
            ak.stock_news_em,
            symbol=normalized_symbol,
            max_retries=2,
            timeout=10
        )

        if news_df is None or news_df.empty:
            return "[新闻] 暂无最新新闻"

        # 获取最近的几条新闻
        titles = news_df.head(limit)['新闻标题'].tolist()

        # 格式化输出
        formatted = " | ".join(titles)

        print(f"[OK] Found {len(titles)} news items")
        return formatted

    except Exception as e:
        print(f"[WARN] Failed to fetch news for {symbol}: {e}")
        return "[新闻] 暂无最新新闻"

