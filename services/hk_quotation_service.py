# coding:utf8
"""
港股实时行情服务模块
基于腾讯港股接口，提供港股实时行情查询

数据源: http://sqt.gtimg.cn/utf8/q=r_hk{股票代码}

使用示例:
    service = HKQuotationService()
    
    # 获取单只港股
    data = service.get_realtime('00700')
    
    # 获取多只港股
    data = service.get_realtime(['00700', '00941', '09988'])
"""

import re
import time
from typing import Dict, List, Union, Optional
import requests

from utils.logger import get_logger
from services.data_config import REQUEST_TIMEOUT

logger = get_logger(__name__)


class HKQuotation:
    """港股实时行情获取"""
    
    max_num = 50  # 每次请求最大股票数
    
    def __init__(self):
        self._session = requests.Session()
    
    @property
    def stock_api(self) -> str:
        return "http://sqt.gtimg.cn/utf8/q="
    
    def _get_headers(self) -> dict:
        return {
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/54.0.2840.100 Safari/537.36"
            ),
        }
    
    def _format_stock_code(self, code: str) -> str:
        """格式化港股代码为标准格式"""
        # 移除可能的前缀
        if code.startswith(("hk", "HK")):
            code = code[2:]
        
        # 确保是5位数字
        code = code.zfill(5)
        return f"r_hk{code}"
    
    def _gen_stock_prefix(self, stock_codes: List[str]) -> List[str]:
        """为港股代码添加前缀"""
        return [self._format_stock_code(code) for code in stock_codes]
    
    def _fetch_stocks(self, stock_list: str) -> Optional[str]:
        """获取一批股票数据"""
        try:
            headers = self._get_headers()
            r = self._session.get(self.stock_api + stock_list, headers=headers, timeout=REQUEST_TIMEOUT)
            r.encoding = 'utf-8'
            return r.text
        except Exception as e:
            logger.warning(f"港股行情请求失败: {e}")
            return None
    
    def get_realtime(self, stock_codes: Union[str, List[str]], prefix: bool = False) -> Dict:
        """
        获取港股实时行情
        
        Args:
            stock_codes: 单个股票代码或代码列表 (如 '00700', '700', 'hk00700')
            prefix: 返回结果是否带有hk前缀
        
        Returns:
            行情字典 {代码: {name, price, change_pct, ...}}
        """
        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]
        
        # 添加市场前缀
        stock_with_prefix = self._gen_stock_prefix(stock_codes)
        
        # 分批请求
        results = []
        for i in range(0, len(stock_with_prefix), self.max_num):
            batch = stock_with_prefix[i:i + self.max_num]
            stock_list = ",".join(batch)
            data = self._fetch_stocks(stock_list)
            if data:
                results.append(data)
        
        return self._parse_response(results, prefix=prefix)
    
    def _parse_response(self, rep_data: List[str], prefix: bool = False) -> Dict:
        """解析响应数据"""
        stocks_detail = "".join(rep_data)
        stock_dict = {}
        
        # 匹配每条港股数据
        for raw_quotation in re.findall(r'v_r_hk\d+=".*?"', stocks_detail):
            try:
                quotation = re.search(r'"(.*?)"', raw_quotation).group(1).split("~")
                
                if len(quotation) < 70:
                    continue
                
                stock_code = quotation[2] if prefix else quotation[2]
                
                # 安全转换函数
                def safe_float(s, default=0.0):
                    try:
                        return float(s) if s else default
                    except (ValueError, TypeError):
                        return default
                
                def safe_int(s, default=0):
                    try:
                        return int(float(s)) if s else default
                    except (ValueError, TypeError):
                        return default
                
                stock_dict[stock_code] = {
                    "lot_size": safe_int(quotation[0]),              # 每手数量
                    "name": quotation[1],                            # 股票名称
                    "code": stock_code,                              # 股票代码
                    "price": safe_float(quotation[3]),               # 当前价格
                    "last_price": safe_float(quotation[4]),          # 昨收价
                    "open_price": safe_float(quotation[5]),          # 开盘价
                    "volume": safe_float(quotation[6]),              # 成交量
                    "now_1": safe_float(quotation[9]),               # 当前价格1
                    "now_2": safe_float(quotation[19]),              # 当前价格2
                    "volume_2": safe_float(quotation[29]),           # 成交量2
                    "date": (quotation[30][:10]).replace("/", "-") if len(quotation[30]) >= 10 else "",
                    "time": quotation[30][-8:] if len(quotation[30]) >= 8 else "",
                    "change": safe_float(quotation[31]),             # 涨跌
                    "change_pct": safe_float(quotation[32]),         # 涨跌%
                    "high": safe_float(quotation[33]),               # 最高价
                    "low": safe_float(quotation[34]),                # 最低价
                    "now_3": safe_float(quotation[35]),              # 当前价格3
                    "volume_3": safe_float(quotation[36]),           # 成交量3
                    "amount": safe_float(quotation[37]),             # 成交额
                    "amplitude": safe_float(quotation[43]),          # 振幅
                    "float_market_cap": safe_float(quotation[44]),   # 流通市值
                    "market_cap": safe_float(quotation[45]),         # 总市值
                    "year_high": safe_float(quotation[48]),          # 52周最高
                    "year_low": safe_float(quotation[49]),           # 52周最低
                    "order_ratio": safe_float(quotation[51]),        # 委比
                    "turnover": safe_float(quotation[59]),           # 换手率%
                    "lot_size_2": safe_int(quotation[60]),           # lotSize_2
                    "free_float": safe_float(quotation[69]),         # 流通股本
                    "total_equity": safe_float(quotation[70]) if len(quotation) > 70 else 0,  # 总股本
                    "ma": safe_float(quotation[73]) if len(quotation) > 73 else 0,  # 均价
                }
            except Exception as e:
                logger.warning(f"解析港股数据失败: {e}")
                continue
        
        return stock_dict


class HKQuotationService:
    """
    统一的港股行情服务
    提供单只/批量港股查询，支持缓存
    """
    
    # 类级别缓存
    _cache: Dict = {}
    _cache_time: float = 0
    _cache_ttl: int = 30  # 缓存30秒
    
    def __init__(self):
        self._quotation = HKQuotation()
    
    def get_realtime(self, codes: Union[str, List[str]], prefix: bool = False) -> Dict:
        """
        获取港股实时行情
        
        Args:
            codes: 港股代码或代码列表 (如 '00700' 或 ['00700', '09988'])
            prefix: 是否在返回结果中带有hk前缀
        
        Returns:
            {代码: {name, price, change_pct, high, low, volume, ...}}
        """
        return self._quotation.get_realtime(codes, prefix=prefix)
    
    def get_stock_detail(self, code: str) -> Optional[Dict]:
        """
        获取单只港股详细信息
        
        Args:
            code: 港股代码
        
        Returns:
            详细行情数据，包含市值、52周高低等信息
        """
        data = self._quotation.get_realtime(code)
        if data:
            # 返回第一个结果
            for stock_code, info in data.items():
                return info
        return None


# 全局单例
_hk_service: Optional[HKQuotationService] = None


def get_hk_quotation_service() -> HKQuotationService:
    """获取港股行情服务单例"""
    global _hk_service
    if _hk_service is None:
        _hk_service = HKQuotationService()
    return _hk_service
