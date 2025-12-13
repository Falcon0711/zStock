# coding:utf8
"""
外汇牌价服务模块
提供中国银行外汇牌价查询

数据源: http://www.boc.cn/sourcedb/whpj/

使用示例:
    service = ExchangeRateService()
    
    # 获取美元汇率
    rate = service.get_exchange_rate('USD')
    logger.info(f"美元买入价: {rate['buy_price']}")
"""

import re
import time
from typing import Dict, Optional
import requests
from datetime import datetime

from utils.logger import get_logger
from services.data_config import REQUEST_TIMEOUT

logger = get_logger(__name__)


class BocExchangeRate:
    """中国银行外汇牌价获取"""
    
    url = "http://www.boc.cn/sourcedb/whpj/"
    
    def __init__(self):
        self._session = requests.Session()
    
    def _get_headers(self) -> dict:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ),
        }
    
    def get_usd_rate(self) -> Dict:
        """
        获取美元汇率
        
        Returns:
            {
                'currency': '美元',
                'buy_price': 7.25,
                'sell_price': 7.28,
                'middle_price': 7.265,
                'update_time': '2025-12-08 10:30:00'
            }
        """
        try:
            headers = self._get_headers()
            r = self._session.get(self.url, headers=headers, timeout=REQUEST_TIMEOUT)
            r.encoding = 'utf-8'
            
            # 提取所有的表格单元格数据
            data = re.findall(r"<td>(.*?)</td>", r.text)
            
            if len(data) < 15:
                logger.warning("外汇数据解析失败: 数据不足")
                return {}
            
            # 美元数据通常在特定位置
            # 中行页面格式: 货币名称, 现汇买入价, 现钞买入价, 现汇卖出价, 现钞卖出价, 中行折算价, 发布时间
            try:
                # 查找美元相关数据
                usd_index = -1
                for i, cell in enumerate(data):
                    if "美元" in cell or "USD" in cell:
                        usd_index = i
                        break
                
                if usd_index == -1:
                    logger.warning("未找到美元数据")
                    return {}
                
                # 提取买入价和卖出价（现汇）
                # 一般格式: 货币名, 现汇买入, 现钞买入, 现汇卖出, 现钞卖出, 中行折算价, 时间
                buy_price = float(data[usd_index + 1]) if usd_index + 1 < len(data) else 0
                sell_price = float(data[usd_index + 3]) if usd_index + 3 < len(data) else 0
                middle_price = (buy_price + sell_price) / 2 if buy_price and sell_price else 0
                
                return {
                    "currency": "美元",
                    "currency_code": "USD",
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "middle_price": round(middle_price, 4),
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            except (ValueError, IndexError) as e:
                logger.warning(f"解析美元汇率数据失败: {e}")
                return {}
        
        except requests.RequestException as e:
            logger.error(f"获取外汇牌价失败: {e}")
            return {}
    
    def get_all_rates(self) -> Dict:
        """
        获取所有外汇牌价
        
        Returns:
            {'USD': {...}, 'EUR': {...}, ...}
        """
        # 简化版本，只返回美元
        # 可以扩展支持更多币种
        usd_rate = self.get_usd_rate()
        if usd_rate:
            return {"USD": usd_rate}
        return {}


class ExchangeRateService:
    """
    外汇牌价服务
    提供汇率查询，支持缓存
    """
    
    # 类级别缓存
    _cache: Dict = {}
    _cache_time: float = 0
    _cache_ttl: int = 3600  # 缓存1小时（外汇更新不频繁）
    
    def __init__(self):
        self._exchange = BocExchangeRate()
    
    def get_exchange_rate(self, currency: str = "USD") -> Dict:
        """
        获取指定货币的汇率
        
        Args:
            currency: 货币代码，如 'USD', 'EUR'（当前仅支持USD）
        
        Returns:
            {
                'currency': '美元',
                'currency_code': 'USD',
                'buy_price': 7.25,
                'sell_price': 7.28,
                'middle_price': 7.265,
                'update_time': '2025-12-08 10:30:00'
            }
        """
        # 标准化货币代码
        currency = currency.upper()
        
        # 检查缓存
        current_time = time.time()
        cache_key = f"rate_{currency}"
        
        if (cache_key in self._cache and 
            (current_time - self._cache_time) < self._cache_ttl):
            return self._cache[cache_key]
        
        # 获取汇率
        if currency == "USD":
            result = self._exchange.get_usd_rate()
        else:
            logger.warning(f"暂不支持货币: {currency}")
            return {}
        
        # 更新缓存
        if result:
            self._cache[cache_key] = result
            self._cache_time = current_time
        
        return result
    
    def get_all_rates(self) -> Dict:
        """
        获取所有支持的汇率
        
        Returns:
            {'USD': {...}, ...}
        """
        # 检查缓存
        current_time = time.time()
        cache_key = "all_rates"
        
        if (cache_key in self._cache and 
            (current_time - self._cache_time) < self._cache_ttl):
            return self._cache[cache_key]
        
        # 获取所有汇率
        result = self._exchange.get_all_rates()
        
        # 更新缓存
        if result:
            self._cache[cache_key] = result
            self._cache_time = current_time
        
        return result


# 全局单例
_exchange_service: Optional[ExchangeRateService] = None


def get_exchange_rate_service() -> ExchangeRateService:
    """获取外汇服务单例"""
    global _exchange_service
    if _exchange_service is None:
        _exchange_service = ExchangeRateService()
    return _exchange_service
