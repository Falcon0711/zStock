"""
数据模型 - 实时行情
定义统一的实时行情数据结构
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RealtimeQuotation:
    """实时行情数据模型"""
    
    code: str              # 股票代码（6位）
    name: str              # 股票名称
    now: float             # 当前价
    open: float            # 今开
    close: float           # 昨收
    high: float            # 最高
    low: float             # 最低
    volume: int            # 成交量
    amount: float          # 成交额
    change: float          # 涨跌额
    change_pct: float      # 涨跌幅(%)
    
    # 可选字段
    buy1: Optional[float] = None      # 买一价
    sell1: Optional[float] = None     # 卖一价
    turnover: Optional[float] = None  # 换手率
    
    def to_dict(self) -> dict:
        """转换为字典（兼容旧代码）"""
        return {
            'code': self.code,
            'name': self.name,
            'now': self.now,
            'open': self.open,
            'close': self.close,
            'high': self.high,
            'low': self.low,
            'volume': self.volume,
            'amount': self.amount,
            'change': self.change,
            'change_pct': self.change_pct,
            'buy1': self.buy1,
            'sell1': self.sell1,
            'turnover': self.turnover,
        }
