# -*- coding: utf-8 -*-
"""
DataFetcher - Tushare Pro 数据获取类
封装 Tushare Pro 接口，提供 AkShare 兼容的数据格式
"""
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
import pandas as pd
import tushare as ts


class DataFetcher:
    """
    数据获取类 - 封装 Tushare Pro 接口
    提供 AkShare 兼容的接口，便于迁移
    """

    def __init__(self, token: str = None):
        """
        初始化 DataFetcher

        Args:
            token: Tushare Pro API token
        """
        self.token = token or os.getenv("TUSHARE_TOKEN")
        if not self.token:
            raise ValueError("Tushare token not provided")

        # 初始化 Tushare
        ts.set_token(self.token)
        self.pro = ts.pro_api()

        # 频率控制
        self.last_request_time = 0
        self.min_request_interval = 0.3  # 每次请求最小间隔(秒)

        # 缓存配置
        self.cache = {}
        self.cache_ttl = 300  # 5分钟缓存

        # 重试配置
        self.max_retries = 3
        self.retry_delay = 2

    def _add_suffix(self, symbol: str) -> str:
        """
        为6位股票代码添加交易所后缀

        Args:
            symbol: 6位股票代码 (如 '600000')

        Returns:
            带后缀的代码 (如 '600000.SH')
        """
        if '.' in symbol:
            return symbol  # 已有后缀

        # 上海证券交易所: 6开头、689开头
        if symbol.startswith('6') or symbol.startswith('689'):
            return f"{symbol}.SH"
        # 深圳证券交易所: 0、2、3开头
        elif symbol.startswith(('0', '2', '3')):
            return f"{symbol}.SZ"
        else:
            # 默认上海
            return f"{symbol}.SH"

    def _remove_suffix(self, symbol: str) -> str:
        """
        移除交易所后缀，返回6位代码

        Args:
            symbol: 带后缀的代码 (如 '600000.SH')

        Returns:
            6位代码 (如 '600000')
        """
        return symbol.split('.')[0]

    def _convert_date_format(self, date_str: str) -> str:
        """
        日期格式转换: YYYY-MM-DD -> YYYYMMDD

        Args:
            date_str: YYYY-MM-DD 格式

        Returns:
            YYYYMMDD 格式
        """
        return date_str.replace('-', '')

    def _convert_date_format_reverse(self, date_str: str) -> str:
        """
        日期格式转换: YYYYMMDD -> YYYY-MM-DD

        Args:
            date_str: YYYYMMDD 格式

        Returns:
            YYYY-MM-DD 格式
        """
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str

    def _map_fields(self, df: pd.DataFrame, data_type: str = 'stock') -> pd.DataFrame:
        """
        字段映射: Tushare 字段 -> AkShare 字段

        Args:
            df: Tushare 返回的 DataFrame
            data_type: 数据类型 ('stock', 'index')

        Returns:
            映射后的 DataFrame
        """
        if df.empty:
            return df

        # Tushare -> AkShare 字段映射表
        field_mapping = {
            'stock': {
                'trade_date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'vol': '成交量',
                'amount': '成交额',
                'pct_chg': '涨跌幅'
            },
            'index': {
                'trade_date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'vol': '成交量',
                'amount': '成交额',
                'pct_chg': '涨跌幅'
            }
        }

        mapping = field_mapping.get(data_type, field_mapping['stock'])

        # 重命名列
        df_mapped = df.rename(columns=mapping)

        # 确保日期格式正确
        if '日期' in df_mapped.columns:
            df_mapped['日期'] = df_mapped['日期'].apply(
                lambda x: self._convert_date_format_reverse(str(x))
            )

        # 排序: 按日期升序
        if '日期' in df_mapped.columns:
            df_mapped = df_mapped.sort_values('日期')

        return df_mapped

    def _rate_limit(self):
        """频率控制: 确保请求间隔符合限制"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _retry_request(self, func, *args, **kwargs):
        """
        带重试机制的请求

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                self._rate_limit()  # 应用频率控制
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    print(f"[WARN] Request failed (attempt {attempt + 1}/{self.max_retries}), "
                          f"retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    print(f"[ERROR] Request failed after {self.max_retries} attempts: {e}")

        raise last_error

    def _get_cache_key(self, prefix: str, **params) -> str:
        """生成缓存键"""
        param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        return f"{prefix}:{param_str}"

    def _get_from_cache(self, key: str) -> Optional:
        """从缓存获取数据"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return data
            else:
                del self.cache[key]
        return None

    def _set_cache(self, key: str, data):
        """设置缓存"""
        self.cache[key] = (data, time.time())

    def get_stock_daily(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        adjust: str = ''
    ) -> pd.DataFrame:
        """
        获取A股日线数据 (对应 AkShare: stock_zh_a_hist)

        Args:
            symbol: 6位股票代码 (如 '600000')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            adjust: 复权类型 (''/'qfq'/'hfq')

        Returns:
            DataFrame with columns: 日期, 开盘, 收盘, 最高, 最低, 成交量
        """
        # 转换为 Tushare 格式
        ts_symbol = self._add_suffix(symbol)
        ts_start = self._convert_date_format(start_date) if start_date else '19700101'
        ts_end = self._convert_date_format(end_date) if end_date else '20500101'

        # 检查缓存
        cache_key = self._get_cache_key('stock_daily', symbol=ts_symbol,
                                        start=ts_start, end=ts_end, adjust=adjust)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data

        # 获取数据
        def fetch_data():
            # Tushare daily 接口
            df = self.pro.daily(
                ts_code=ts_symbol,
                start_date=ts_start,
                end_date=ts_end
            )
            return df

        df = self._retry_request(fetch_data)

        if df is None or df.empty:
            return pd.DataFrame()

        # 字段映射
        df_mapped = self._map_fields(df, data_type='stock')

        # 缓存
        self._set_cache(cache_key, df_mapped)

        return df_mapped

    def get_stock_info(self, symbol: str) -> Dict:
        """
        获取个股基本信息 (对应 AkShare: stock_individual_info_em)

        Args:
            symbol: 6位股票代码

        Returns:
            {
                'name': str,
                'industry': str,
                'sector': str
            }
        """
        ts_symbol = self._add_suffix(symbol)

        # 检查缓存
        cache_key = self._get_cache_key('stock_info', symbol=ts_symbol)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data

        # 获取数据
        def fetch_data():
            # Tushare stock_basic 接口
            df = self.pro.stock_basic(
                ts_code=ts_symbol,
                fields='ts_code,name,industry,market'
            )
            return df

        try:
            df = self._retry_request(fetch_data)

            if df is None or df.empty:
                return {
                    'name': symbol,
                    'industry': '其他',
                    'sector': '其他'
                }

            # 提取信息
            info = df.iloc[0]
            industry = info.get('industry', '其他')

            # 根据 industry 推测 sector
            sector = self._infer_sector(industry)

            result = {
                'name': info['name'],
                'industry': industry,
                'sector': sector
            }

            # 缓存
            self._set_cache(cache_key, result)

            return result
        except Exception as e:
            print(f"[WARN] Failed to fetch stock info for {symbol}: {e}")
            return {
                'name': symbol,
                'industry': '其他',
                'sector': '其他'
            }

    def _infer_sector(self, industry: str) -> str:
        """根据行业推测板块"""
        sector_mapping = {
            '银行': '金融',
            '保险': '金融',
            '证券': '金融',
            '信托': '金融',
            '医药': '医疗健康',
            '生物': '医疗健康',
            '医疗': '医疗健康',
            '化学制药': '医疗健康',
            '电子': '科技',
            '计算机': '科技',
            '软件': '科技',
            '通信': '科技',
            '半导体': '科技',
            '汽车': '新能源',
            '新能源': '新能源',
            '光伏': '新能源',
            '风电': '新能源',
            '锂电池': '新能源',
            '白酒': '消费品',
            '食品': '消费品',
            '家电': '消费品',
            '纺织': '消费品',
            '服饰': '消费品',
            '化工': '材料',
            '钢铁': '材料',
            '有色': '材料',
            '建材': '材料',
            '电力': '公用事业',
            '水务': '公用事业',
            '燃气': '公用事业',
            '建筑': '工业',
            '装修': '工业',
            '基建': '工业',
            '机械': '工业',
            '房地产': '房地产',
            '交通运输': '交通运输',
            '物流': '交通运输',
            '航空': '交通运输',
            '传媒': '文化娱乐',
            '娱乐': '文化娱乐',
            '教育': '文化娱乐',
        }

        for key, sector in sector_mapping.items():
            if key in industry:
                return sector

        return '其他'

    def get_index_daily(
        self,
        symbol: str,  # 如 '000300'
        start_date: str = None,
        end_date: str = None
    ) -> pd.DataFrame:
        """
        获取指数日线数据 (对应 AkShare: index_zh_a_hist)

        Args:
            symbol: 指数代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            DataFrame with columns: 日期, 开盘, 收盘, 最高, 最低, 成交量
        """
        # 沪深300等指数需要特殊处理
        # Tushare 中指数代码格式: 000300.SH
        ts_symbol = self._add_suffix(symbol)
        ts_start = self._convert_date_format(start_date) if start_date else '19700101'
        ts_end = self._convert_date_format(end_date) if end_date else '20500101'

        # 检查缓存
        cache_key = self._get_cache_key('index_daily', symbol=ts_symbol,
                                        start=ts_start, end=ts_end)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data

        # 获取数据
        def fetch_data():
            # Tushare index_daily 接口
            df = self.pro.index_daily(
                ts_code=ts_symbol,
                start_date=ts_start,
                end_date=ts_end
            )
            return df

        df = self._retry_request(fetch_data)

        if df is None or df.empty:
            return pd.DataFrame()

        # 字段映射
        df_mapped = self._map_fields(df, data_type='index')

        # 缓存
        self._set_cache(cache_key, df_mapped)

        return df_mapped
