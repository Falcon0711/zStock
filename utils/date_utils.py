"""
日期时间工具函数
提供交易日判断、日期格式化等功能
"""

from datetime import datetime, date, timedelta
from typing import Optional


# 交易时段配置
MORNING_START = "09:30"
MORNING_END = "11:30"
AFTERNOON_START = "13:00"
AFTERNOON_END = "15:00"


def is_trading_day(check_date: Optional[date] = None) -> bool:
    """
    判断指定日期是否为交易日（仅检查周末，不含节假日）
    
    Args:
        check_date: 要检查的日期，默认今天
    
    Returns:
        True - 交易日, False - 非交易日（周末）
    """
    if check_date is None:
        check_date = date.today()
    
    # 周末不是交易日
    return check_date.weekday() < 5  # 0-4 是周一到周五


def is_trading_time(check_time: Optional[datetime] = None) -> bool:
    """
    判断当前是否在交易时间
    
    Args:
        check_time: 要检查的时间，默认当前时间
    
    Returns:
        True - 交易时间, False - 非交易时间
    """
    if check_time is None:
        check_time = datetime.now()
    
    # 先检查是否交易日
    if not is_trading_day(check_time.date()):
        return False
    
    current = check_time.strftime('%H:%M')
    
    # 上午交易时段
    if MORNING_START <= current <= MORNING_END:
        return True
    
    # 下午交易时段
    if AFTERNOON_START <= current <= AFTERNOON_END:
        return True
    
    return False


def get_last_trading_day(from_date: Optional[date] = None) -> date:
    """
    获取最近的交易日
    
    如果是交易日且在交易时段后返回今天
    如果是交易日但在交易时段前返回昨天的交易日
    如果是非交易日返回最近的交易日
    
    Args:
        from_date: 从哪天开始往前找，默认今天
    
    Returns:
        最近的交易日日期
    """
    if from_date is None:
        from_date = date.today()
    
    check_date = from_date
    
    # 最多往前找10天
    for _ in range(10):
        if is_trading_day(check_date):
            return check_date
        check_date -= timedelta(days=1)
    
    return check_date


def get_previous_trading_day(from_date: Optional[date] = None) -> date:
    """
    获取上一个交易日
    
    Args:
        from_date: 从哪天开始往前找，默认今天
    
    Returns:
        上一个交易日日期
    """
    if from_date is None:
        from_date = date.today()
    
    check_date = from_date - timedelta(days=1)
    
    # 最多往前找10天
    for _ in range(10):
        if is_trading_day(check_date):
            return check_date
        check_date -= timedelta(days=1)
    
    return check_date


def format_date(d: date, fmt: str = '%Y-%m-%d') -> str:
    """
    格式化日期
    
    Args:
        d: 日期对象
        fmt: 格式字符串
    
    Returns:
        格式化后的日期字符串
    """
    return d.strftime(fmt)


def parse_date(date_str: str, fmt: str = '%Y-%m-%d') -> Optional[date]:
    """
    解析日期字符串
    
    Args:
        date_str: 日期字符串
        fmt: 格式字符串
    
    Returns:
        日期对象，解析失败返回 None
    """
    try:
        return datetime.strptime(date_str, fmt).date()
    except (ValueError, TypeError):
        return None


def get_trading_day_range(days: int = 30) -> tuple:
    """
    获取交易日日期范围
    
    Args:
        days: 往前多少天
    
    Returns:
        (开始日期, 结束日期)
    """
    end_date = get_last_trading_day()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date
