"""
数据模型 - K线数据
定义统一的K线数据结构
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class KLineData:
    """K线数据模型（单条）"""
    
    date: str              # 日期 YYYY-MM-DD
    open: float            # 开盘价
    high: float            # 最高价
    low: float             # 最低价
    close: float           # 收盘价
    volume: int            # 成交量
    amount: Optional[float] = None  # 成交额
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'date': self.date,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'amount': self.amount,
        }
