# -*- coding: utf-8 -*-
"""
Custom Exceptions for AShare Sentinel Pro
"""


class DataFetchError(Exception):
    """Base exception for data fetch errors"""
    pass


class TushareConnectionError(DataFetchError):
    """Tushare API connection error"""
    pass


class TushareAPIError(DataFetchError):
    """Tushare API returned an error"""
    pass


class AkShareError(DataFetchError):
    """AkShare data fetch error"""
    pass


class InvalidStockSymbol(Exception):
    """Invalid stock symbol provided"""
    pass
