# coding:utf8
"""
实时行情服务模块
支持新浪和腾讯数据源获取 A股实时行情

使用示例:
    service = RealtimeQuotationService(source='sina')
    
    # 获取单只股票
    data = service.get_realtime('600519')
    
    # 获取多只股票
    data = service.get_realtime(['600519', '000001', '300750'])
    
    # 获取全市场快照
    data = service.get_market_snapshot(limit=100)
"""

import re
import time
import json
import os
from typing import Dict, List, Union, Optional
from concurrent.futures import ThreadPoolExecutor
import requests
from datetime import datetime

from utils.logger import get_logger
from services.data_config import REQUEST_TIMEOUT

logger = get_logger(__name__)


from datetime import datetime

from utils.stock_utils import get_stock_type  # 使用统一的工具函数
# 使用统一的数据源模块
from services.data_sources import SinaDataSource, TencentDataSource


# 股票代码路径
STOCK_CODE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "stock_codes.json")



class RealtimeQuotationService:
    """
    统一的实时行情服务
    
    支持新浪和腾讯两个数据源，默认使用新浪（更稳定）
    """
    
    # 类级别缓存
    _cache: Dict = {}
    _cache_time: float = 0
    _cache_ttl: int = 3  # 缓存3秒
    
    def __init__(self, source: str = 'sina'):
        """
        初始化实时行情服务
        
        Args:
            source: 数据源，'sina' 或 'tencent'
        """
        self.source = source.lower()
        
        # 直接使用数据源类
        from services.data_sources import SinaDataSource, TencentDataSource
        
        if self.source == 'sina':
            self._quotation = SinaDataSource()
        elif self.source == 'tencent':
            self._quotation = TencentDataSource()
        else:
            raise ValueError(f"不支持的数据源: {source}，请使用 'sina' 或 'tencent'")
        
        # 加载股票代码列表
        self._stock_codes: List[str] = []
        self._load_stock_codes()
    
    def _load_stock_codes(self):
        """加载全市场股票代码"""
        try:
            if os.path.exists(STOCK_CODE_PATH):
                with open(STOCK_CODE_PATH) as f:
                    data = json.load(f)
                    self._stock_codes = data.get("stock", [])
                    logger.info(f"加载股票代码列表: {len(self._stock_codes)} 只")
            else:
                logger.warning(f"股票代码文件不存在: {STOCK_CODE_PATH}")
        except Exception as e:
            logger.warning(f"加载股票代码列表失败: {e}")
    
    def get_realtime(self, codes: Union[str, List[str]], prefix: bool = False) -> Dict:
        """
        获取实时行情
        
        Args:
            codes: 股票代码或代码列表 (如 '600519' 或 ['600519', '000001'])
            prefix: 是否在返回结果中带有市场前缀 (sh/sz/bj)
        
        Returns:
            {代码: {name, now, open, close, high, low, volume, ...}}
        """
        if isinstance(codes, str):
            codes = [codes]
        return self._quotation.get_realtime(codes)
    
    def get_market_snapshot(self, limit: int = 100, prefix: bool = False) -> Dict:
        """
        获取全市场行情快照
        
        Args:
            limit: 获取前N只股票 (0表示全部)
            prefix: 是否带市场前缀
        
        Returns:
            {代码: {name, now, open, close, high, low, ...}}
        """
        # 检查缓存
        current_time = time.time()
        cache_key = f"market_{limit}_{prefix}"
        
        if (cache_key in self._cache and 
            (current_time - self._cache_time) < self._cache_ttl):
            return self._cache[cache_key]
        
        # 获取股票列表
        if not self._stock_codes:
            logger.warning("股票代码列表为空")
            return {}
        
        codes = self._stock_codes[:limit] if limit > 0 else self._stock_codes
        
        # 获取行情
        result = self._quotation.get_realtime(codes)
        
        # 更新缓存
        self._cache[cache_key] = result
        self._cache_time = current_time
        
        return result
    
    def get_realtime_with_fallback(self, codes: Union[str, List[str]], prefix: bool = False) -> Dict:
        """
        获取实时行情（带容灾切换）
        
        数据源优先级: 新浪 → 腾讯 → 东方财富（配置驱动）
        
        Args:
            codes: 股票代码或代码列表
            prefix: 是否带市场前缀
        
        Returns:
            {代码: {name, now, open, close, high, low, ...}}
        """
        from services.data_source_factory import create_realtime_executor
        
        # 规范化为列表
        if isinstance(codes, str):
            codes = [codes]
        
        executor = create_realtime_executor(codes)
        result = executor.execute()
        
        return result if result else {}
    
    def _get_realtime_from_eastmoney(self, code: str) -> Optional[Dict]:
        """
        从东方财富获取单只股票实时行情 (委托给 EastmoneyDataSource)
        
        Args:
            code: 6位股票代码
        
        Returns:
            {name, now, open, close, high, low, volume, ...} 或 None
        """
        from services.data_sources import EastmoneyDataSource
        eastmoney = EastmoneyDataSource()
        return eastmoney.get_realtime(code)
    
    def get_stock_codes(self) -> List[str]:
        """获取全市场股票代码列表"""
        return self._stock_codes.copy()
    
    def get_intraday(self, stock_code: str) -> Dict:
        """
        获取股票当日分时走势数据（带容灾）
        
        数据源优先级: 东方财富 → 腾讯
        
        Args:
            stock_code: 6位股票代码，如 '600519'
        
        Returns:
            {
                'code': '600519',
                'name': '贵州茅台',
                'now': 1825.00,
                'change_pct': 0.85,
                'data': [{'time': '09:30', 'price': 1820.00, 'avg': 1820.00, 'volume': 1234}, ...],
                'date': '2025-12-09'
            }
        """
        # 获取当日基础行情
        quote_data = self.get_realtime(stock_code)
        quote = quote_data.get(stock_code, {})
        
        if not quote:
            return {'error': f'无法获取股票 {stock_code} 的行情数据'}
        
        from services.fallback import FallbackExecutor
        from utils.logger import get_logger
        from services.data_config import REQUEST_TIMEOUT
        logger = get_logger(__name__)
        
        # 使用容灾执行器获取分时数据
        def get_from_eastmoney():
            data, data_date, preClose = self._get_intraday_from_eastmoney(stock_code)
            if data and len(data) > 0:
                return {'data': data, 'date': data_date, 'preClose': preClose}
            return None
        
        def get_from_tencent():
            data, data_date = self._get_intraday_from_tencent(stock_code)
            if data and len(data) > 0:
                return {'data': data, 'date': data_date, 'preClose': 0}
            return None
        
        executor = FallbackExecutor(
            providers=[get_from_eastmoney, get_from_tencent],
            names=['东方财富', '腾讯'],
            context=f"[{stock_code}]"
        )
        
        result = executor.execute()
        
        if result:
            if result.get('preClose', 0) > 0:
                quote['close'] = result['preClose']
            return self._build_intraday_response(stock_code, quote, result['data'], result['date'])
        
        # 所有数据源都失败
        return self._build_intraday_response(stock_code, quote, [], None)
    
    def _get_intraday_from_eastmoney(self, stock_code: str) -> tuple:
        """从东方财富获取分时数据"""
        try:
            prefix = get_stock_type(stock_code)
            if prefix == 'sz':
                secid = f"0.{stock_code}"
            elif prefix == 'sh':
                secid = f"1.{stock_code}"
            else:
                secid = f"0.{stock_code}"
            
            url = f"https://push2his.eastmoney.com/api/qt/stock/trends2/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&fields2=f51,f52,f53,f54,f55,f56,f57,f58&iscr=0&iscca=0&ndays=1"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://quote.eastmoney.com/"
            }
            
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code != 200:
                return [], None, 0
            
            result = response.json()
            
            if result.get('rc') != 0 or not result.get('data'):
                return [], None, 0
            
            data = result['data']
            trends = data.get('trends', [])
            preClose = float(data.get('preClose', 0))
            
            if not trends:
                return [], None, preClose
            
            # 解析分时数据
            formatted_data = []
            data_date = None
            
            for trend in trends:
                try:
                    parts = trend.split(',')
                    if len(parts) < 7:
                        continue
                    
                    time_str = parts[0]
                    if ' ' in time_str:
                        date_part, time_part = time_str.split(' ')
                        if not data_date:
                            data_date = date_part
                        time_str = time_part[:5]
                    
                    price = float(parts[1]) if parts[1] else 0
                    volume = int(float(parts[5])) if parts[5] else 0
                    avg_price = float(parts[7]) if len(parts) > 7 and parts[7] else price
                    
                    formatted_data.append({
                        'time': time_str,
                        'price': price,
                        'avg': round(avg_price, 2),
                        'volume': volume
                    })
                except (ValueError, IndexError):
                    continue
            
            logger.debug(f"[东方财富] {stock_code} 分时数据 {len(formatted_data)} 条")
            return formatted_data, data_date, preClose
            
        except Exception as e:
            logger.warning(f"[东方财富] {stock_code} 分时数据失败: {e}")
            return [], None, 0
    
    def _get_intraday_from_tencent(self, stock_code: str) -> tuple:
        """从腾讯获取分时数据"""
        try:
            prefix = get_stock_type(stock_code)
            tc_code = f"{prefix}{stock_code}"
            
            url = f"http://data.gtimg.cn/flashdata/hushen/minute/{tc_code}.js"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://gu.qq.com/"
            }
            
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code != 200:
                return [], None
            
            # 解析腾讯分时数据格式
            text = response.text
            # 数据格式: min_data="日期\\nhhmm 价格 成交量\\n..."
            
            lines = text.split('\\n')
            if len(lines) < 2:
                return [], None
            
            data_date = lines[0].strip() if lines[0] else datetime.now().strftime('%Y%m%d')
            # 转换日期格式
            if len(data_date) == 8:
                data_date = f"{data_date[:4]}-{data_date[4:6]}-{data_date[6:8]}"
            
            formatted_data = []
            prices = []
            
            for line in lines[1:]:
                if not line.strip():
                    continue
                try:
                    parts = line.strip().split(' ')
                    if len(parts) < 3:
                        continue
                    
                    time_raw = parts[0]  # 格式: 0930
                    if len(time_raw) == 4:
                        time_str = f"{time_raw[:2]}:{time_raw[2:]}"
                    else:
                        time_str = time_raw
                    
                    price = float(parts[1])
                    volume = int(parts[2])
                    
                    prices.append(price)
                    avg_price = sum(prices) / len(prices)
                    
                    formatted_data.append({
                        'time': time_str,
                        'price': price,
                        'avg': round(avg_price, 2),
                        'volume': volume
                    })
                except (ValueError, IndexError):
                    continue
            
            if formatted_data:
                logger.debug(f"[腾讯] {stock_code} 分时数据 {len(formatted_data)} 条")
            return formatted_data, data_date
            
        except Exception as e:
            logger.warning(f"[腾讯] {stock_code} 分时数据失败: {e}")
            return [], None
    
    def _build_intraday_response(self, stock_code: str, quote: Dict, data: List, data_date: Optional[str]) -> Dict:
        """构建分时数据响应"""
        now = float(quote.get('now', 0))
        close = float(quote.get('close', now))
        change_pct = round((now - close) / close * 100, 2) if close > 0 else 0
        
        return {
            'code': stock_code,
            'name': quote.get('name', ''),
            'now': now,
            'open': float(quote.get('open', 0)),
            'close': close,
            'high': float(quote.get('high', 0)),
            'low': float(quote.get('low', 0)),
            'change_pct': change_pct,
            'volume': int(quote.get('turnover', 0)),
            'turnover': float(quote.get('volume', 0)),
            'data': data,
            'date': data_date or datetime.now().strftime('%Y-%m-%d'),  # 数据日期
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    @property
    def stock_count(self) -> int:
        """获取股票数量"""
        return len(self._stock_codes)


# 全局单例
_realtime_service: Optional[RealtimeQuotationService] = None


def get_realtime_service(source: str = None) -> RealtimeQuotationService:
    """
    获取实时行情服务单例
    
    Args:
        source: 数据源，默认从 REALTIME_PROVIDERS 配置取第一个
    """
    from services.data_config import REALTIME_PROVIDERS
    
    global _realtime_service
    
    # 使用配置的第一个数据源作为默认
    if source is None:
        source = REALTIME_PROVIDERS[0] if REALTIME_PROVIDERS else 'sina'
    
    if _realtime_service is None or _realtime_service.source != source:
        _realtime_service = RealtimeQuotationService(source=source)
    return _realtime_service

