"""
配置驱动的数据源工厂函数
根据配置文件动态创建 FallbackExecutor
"""

from typing import List, Callable
from services.fallback import FallbackExecutor
from services.data_sources import (
    SinaDataSource,
    TencentDataSource,
    EastmoneyDataSource,
    AkShareDataSource
)
from services.data_config import (
    REALTIME_PROVIDERS,
    INTRADAY_PROVIDERS,
    KLINE_PROVIDERS
)


# 数据源实例缓存（单例模式）
_sina = None
_tencent = None
_eastmoney = None
_akshare = None


def _get_sina():
    global _sina
    if _sina is None:
        _sina = SinaDataSource()
    return _sina


def _get_tencent():
    global _tencent
    if _tencent is None:
        _tencent = TencentDataSource()
    return _tencent


def _get_eastmoney():
    global _eastmoney
    if _eastmoney is None:
        _eastmoney = EastmoneyDataSource()
    return _eastmoney


def _get_akshare():
    global _akshare
    if _akshare is None:
        _akshare = AkShareDataSource()
    return _akshare


# 数据源映射
_SOURCE_MAP = {
    'sina': _get_sina,
    'tencent': _get_tencent,
    'eastmoney': _get_eastmoney,
    'akshare': _get_akshare,
}


def create_realtime_executor(codes: List[str]) -> FallbackExecutor:
    """
    创建实时行情容灾执行器（配置驱动）
    
    Args:
        codes: 股票代码列表
    
    Returns:
        FallbackExecutor 实例
    """
    providers = []
    names = []
    
    for source_name in REALTIME_PROVIDERS:
        if source_name in _SOURCE_MAP:
            source = _SOURCE_MAP[source_name]()
            providers.append(lambda s=source: s.get_realtime(codes))
            names.append(source.name)
    
    context = f"[{codes[0]}]" if len(codes) == 1 else f"[{len(codes)}只股票]"
    
    return FallbackExecutor(
        providers=providers,
        names=names,
        context=context
    )


def create_kline_executor(code: str, days: int = 365) -> FallbackExecutor:
    """
    创建K线数据容灾执行器（配置驱动）
    
    Args:
        code: 股票代码
        days: 天数
    
    Returns:
        FallbackExecutor 实例
    """
    providers = []
    names = []
    
    for source_name in KLINE_PROVIDERS:
        if source_name in _SOURCE_MAP:
            source = _SOURCE_MAP[source_name]()
            providers.append(lambda s=source: s.fetch_kline(code, days))
            names.append(source.name)
    
    return FallbackExecutor(
        providers=providers,
        names=names,
        context=f"[{code}]"
    )
