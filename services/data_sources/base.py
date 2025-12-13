# coding:utf8
"""
数据源抽象基类
定义统一的数据源接口，所有数据源实现都必须遵循此接口
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
import pandas as pd
from datetime import datetime


class DataSource(ABC):
    """
    数据源抽象基类
    
    所有数据源（腾讯、AkShare、新浪等）都必须实现此接口
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """数据源名称"""
        pass
    
    @property
    @abstractmethod
    def max_days(self) -> int:
        """单次请求最大天数限制"""
        pass
    
    @abstractmethod
    def fetch_kline(
        self, 
        code: str, 
        days: int = 365,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取K线数据
        
        Args:
            code: 股票代码 (6位)
            days: 获取天数
            end_date: 结束日期 (YYYY-MM-DD)，为空则获取最新数据
        
        Returns:
            DataFrame with columns: [date, open, high, low, close, volume]
            失败返回 None
        """
        pass
    
    @abstractmethod
    def get_realtime(self, codes: List[str]) -> Dict[str, Dict]:
        """
        获取实时行情
        
        Args:
            codes: 股票代码列表 (6位)
        
        Returns:
            {code: {name, now, open, close, high, low, volume, ...}}
            失败返回 {}
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查数据源是否可用"""
        pass
