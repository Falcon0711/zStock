"""
date_utils 单元测试
测试日期时间工具函数
"""

import pytest
from datetime import date, datetime, timedelta
from utils.date_utils import (
    is_trading_day,
    is_trading_time,
    get_last_trading_day,
    get_previous_trading_day,
    format_date,
    parse_date,
)


class TestIsTradingDay:
    """测试 is_trading_day 函数"""
    
    def test_weekday(self):
        """工作日"""
        monday = date(2025, 12, 8)  # 周一
        assert is_trading_day(monday) is True
        
        friday = date(2025, 12, 12)  # 周五
        assert is_trading_day(friday) is True
    
    def test_weekend(self):
        """周末"""
        saturday = date(2025, 12, 7)  # 周六
        assert is_trading_day(saturday) is False
        
        sunday = date(2025, 12, 14)  # 周日
        assert is_trading_day(sunday) is False


class TestIsTradingTime:
    """测试 is_trading_time 函数"""
    
    def test_morning_session(self):
        """上午交易时段"""
        # 2025-12-09 10:00 (周二上午)
        trading_time = datetime(2025, 12, 9, 10, 0)
        assert is_trading_time(trading_time) is True
    
    def test_afternoon_session(self):
        """下午交易时段"""
        trading_time = datetime(2025, 12, 9, 14, 0)
        assert is_trading_time(trading_time) is True
    
    def test_lunch_break(self):
        """午休时间"""
        lunch_time = datetime(2025, 12, 9, 12, 0)
        assert is_trading_time(lunch_time) is False
    
    def test_after_close(self):
        """收盘后"""
        after_close = datetime(2025, 12, 9, 16, 0)
        assert is_trading_time(after_close) is False
    
    def test_weekend(self):
        """周末"""
        saturday = datetime(2025, 12, 7, 10, 0)
        assert is_trading_time(saturday) is False


class TestGetLastTradingDay:
    """测试 get_last_trading_day 函数"""
    
    def test_from_weekday(self):
        """从工作日查询"""
        tuesday = date(2025, 12, 9)
        result = get_last_trading_day(tuesday)
        assert result.weekday() < 5  # 结果是工作日
    
    def test_from_weekend(self):
        """从周末查询"""
        saturday = date(2025, 12, 7)
        result = get_last_trading_day(saturday)
        assert result.weekday() == 4  # 应该是周五


class TestGetPreviousTradingDay:
    """测试 get_previous_trading_day 函数"""
    
    def test_from_tuesday(self):
        """从周二查询"""
        tuesday = date(2025, 12, 9)
        result = get_previous_trading_day(tuesday)
        assert result == date(2025, 12, 8)  # 周一
    
    def test_from_monday(self):
        """从周一查询"""
        monday = date(2025, 12, 8)
        result = get_previous_trading_day(monday)
        assert result == date(2025, 12, 5)  # 周五


class TestFormatDate:
    """测试 format_date 函数"""
    
    def test_default_format(self):
        """默认格式"""
        d = date(2025, 12, 9)
        assert format_date(d) == "2025-12-09"
    
    def test_custom_format(self):
        """自定义格式"""
        d = date(2025, 12, 9)
        assert format_date(d, "%Y%m%d") == "20251209"


class TestParseDate:
    """测试 parse_date 函数"""
    
    def test_valid_date(self):
        """有效日期"""
        result = parse_date("2025-12-09")
        assert result == date(2025, 12, 9)
    
    def test_invalid_date(self):
        """无效日期"""
        result = parse_date("invalid")
        assert result is None
    
    def test_custom_format(self):
        """自定义格式"""
        result = parse_date("20251209", "%Y%m%d")
        assert result == date(2025, 12, 9)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
