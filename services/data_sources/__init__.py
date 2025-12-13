# coding:utf8
"""
数据源模块
提供统一的数据源接口和多个数据源实现
"""

from .base import DataSource
from .tencent import TencentDataSource
from .akshare import AkShareDataSource
from .sina import SinaDataSource
from .eastmoney import EastmoneyDataSource
from .yahoo import YahooDataSource

__all__ = [
    "DataSource",
    "TencentDataSource",
    "AkShareDataSource",
    "SinaDataSource",
    "EastmoneyDataSource",
    "YahooDataSource",
]
