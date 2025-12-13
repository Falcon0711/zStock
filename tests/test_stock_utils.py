"""
stock_utils 单元测试
测试股票代码工具函数
"""

import pytest
from utils.stock_utils import (
    get_stock_type,
    format_stock_code,
    validate_stock_code,
    is_index_code,
    format_hk_code,
)


class TestGetStockType:
    """测试 get_stock_type 函数"""
    
    def test_shanghai_main_board(self):
        """上海主板"""
        assert get_stock_type("600519") == "sh"  # 贵州茅台
        assert get_stock_type("601318") == "sh"  # 中国平安
        assert get_stock_type("603288") == "sh"  # 海天味业
    
    def test_shanghai_star_board(self):
        """科创板"""
        assert get_stock_type("688111") == "sh"
    
    def test_shenzhen_main_board(self):
        """深圳主板"""
        assert get_stock_type("000001") == "sz"  # 平安银行
        assert get_stock_type("000858") == "sz"  # 五粮液
    
    def test_shenzhen_gem_board(self):
        """创业板"""
        assert get_stock_type("300750") == "sz"  # 宁德时代
    
    def test_beijing_exchange(self):
        """北交所"""
        assert get_stock_type("430047") == "bj"
        assert get_stock_type("830946") == "bj"
    
    def test_with_prefix(self):
        """带前缀的代码"""
        assert get_stock_type("sh600519") == "sh"
        assert get_stock_type("sz000001") == "sz"
        assert get_stock_type("bj430047") == "bj"
    
    def test_empty_code(self):
        """空代码"""
        assert get_stock_type("") == "sz"
        assert get_stock_type(None) is not None  # 不应崩溃


class TestFormatStockCode:
    """测试 format_stock_code 函数"""
    
    def test_basic_format(self):
        """基本格式化"""
        assert format_stock_code("600519") == "600519"
        assert format_stock_code("1") == "000001"  # 补零
    
    def test_with_prefix(self):
        """带前缀输出"""
        assert format_stock_code("600519", with_prefix=True) == "sh600519"
        assert format_stock_code("000001", with_prefix=True) == "sz000001"
    
    def test_remove_existing_prefix(self):
        """移除已有前缀"""
        assert format_stock_code("sh600519") == "600519"
        assert format_stock_code("SZ000001") == "000001"


class TestValidateStockCode:
    """测试 validate_stock_code 函数"""
    
    def test_valid_codes(self):
        """有效代码"""
        assert validate_stock_code("600519") is True
        assert validate_stock_code("000001") is True
        assert validate_stock_code("300750") is True
    
    def test_invalid_codes(self):
        """无效代码"""
        assert validate_stock_code("") is False
        assert validate_stock_code("12345") is False  # 5位
        assert validate_stock_code("1234567") is False  # 7位
        assert validate_stock_code("abcdef") is False  # 非数字
    
    def test_with_prefix(self):
        """带前缀的代码"""
        assert validate_stock_code("sh600519") is True
        assert validate_stock_code("sz000001") is True


class TestIsIndexCode:
    """测试 is_index_code 函数"""
    
    def test_us_index(self):
        """美股指数"""
        assert is_index_code("^NDX") is True
        assert is_index_code("^GSPC") is True
    
    def test_hk_index(self):
        """港股指数"""
        assert is_index_code("^HSI") is True
        assert is_index_code("HSTECH.HK") is True
    
    def test_a_share_index(self):
        """A股指数"""
        assert is_index_code("sh000001") is True
        assert is_index_code("sz399001") is True
    
    def test_not_index(self):
        """非指数"""
        assert is_index_code("600519") is False


class TestFormatHkCode:
    """测试 format_hk_code 函数"""
    
    def test_basic_format(self):
        """基本格式化"""
        assert format_hk_code("700") == "00700"
        assert format_hk_code("9988") == "09988"
    
    def test_already_5_digits(self):
        """已是5位"""
        assert format_hk_code("00700") == "00700"
    
    def test_with_prefix(self):
        """带前缀"""
        assert format_hk_code("hk700") == "00700"
        assert format_hk_code("HK9988") == "09988"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
