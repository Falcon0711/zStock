# coding:utf8
"""
实时K线服务模块
整合历史K线数据与实时行情，提供统一的K线数据接口

使用示例:
    service = RealtimeKlineService()
    
    # 获取历史K线 + 实时数据
    klines = service.get_kline_with_realtime('600519', days=90)
    
    # 仅获取实时行情（格式化为K线结构）
    realtime = service.get_realtime_as_kline('600519')
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Union
import pandas as pd

from utils.logger import get_logger
from .realtime_quotation_service import get_realtime_service, RealtimeQuotationService
from .local_data_service import get_local_data_service, LocalDataService

logger = get_logger(__name__)


class RealtimeKlineService:
    """
    实时K线服务
    
    整合历史数据与实时行情，提供：
    1. 历史K线 + 当日实时数据合并
    2. 实时行情格式化为K线结构
    """
    
    def __init__(self, 
                 realtime_source: str = 'sina',
                 local_service: Optional[LocalDataService] = None,
                 realtime_service: Optional[RealtimeQuotationService] = None):
        """
        初始化实时K线服务
        
        Args:
            realtime_source: 实时数据源 ('sina' 或 'tencent')
            local_service: 本地数据服务实例（可选）
            realtime_service: 实时行情服务实例（可选）
        """
        self._local_service = local_service or get_local_data_service()
        self._realtime_service = realtime_service or get_realtime_service(realtime_source)
    
    def get_kline_with_realtime(self, code: str, days: int = 90) -> List[dict]:
        """
        获取历史K线 + 当日实时数据
        
        如果当日有实时行情，会合并到K线数据中：
        - 如果历史数据已包含当日，则用实时数据更新当日收盘价/最高/最低
        - 如果历史数据不包含当日，则添加新的K线条目
        
        Args:
            code: 股票代码 (6位数字)
            days: 获取历史天数
        
        Returns:
            K线数据列表 [{time, open, high, low, close, volume, ...}]
        """
        # 1. 获取历史K线
        history = self._get_history_klines(code, days)
        
        # 2. 获取实时行情
        realtime = self._get_realtime_quote(code)
        
        if not realtime:
            return history
        
        # 3. 合并实时数据
        return self._merge_realtime(history, realtime)
    
    def get_realtime_as_kline(self, code: str) -> Optional[dict]:
        """
        获取实时行情，格式化为K线结构
        
        Args:
            code: 股票代码
        
        Returns:
            {time, open, high, low, close, volume, name, change_pct, ...}
        """
        realtime = self._get_realtime_quote(code)
        if not realtime:
            return None
        
        return self._format_realtime_to_kline(realtime)
    
    def get_batch_realtime(self, codes: List[str]) -> List[dict]:
        """
        批量获取实时行情（K线格式）
        
        Args:
            codes: 股票代码列表
        
        Returns:
            [{code, name, time, open, high, low, close, volume, change_pct, ...}]
        """
        if not codes:
            return []
        
        result = []
        data = self._realtime_service.get_realtime(codes)
        
        for code in codes:
            if code in data:
                kline = self._format_realtime_to_kline(data[code])
                if kline:
                    kline['code'] = code
                    result.append(kline)
        
        return result
    
    def _get_history_klines(self, code: str, days: int) -> List[dict]:
        """从本地数据库获取历史K线"""
        df = self._local_service.get_stock_data(code, days=days)
        
        if df is None or df.empty:
            return []
        
        history = []
        for _, row in df.iterrows():
            history.append({
                "time": row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": int(row['volume']) if pd.notna(row.get('volume')) else 0,
            })
        
        return history
    
    def _get_realtime_quote(self, code: str) -> Optional[dict]:
        """获取单只股票实时行情"""
        try:
            data = self._realtime_service.get_realtime(code)
            if data and code in data:
                return data[code]
            # 尝试去掉前缀
            for key in data:
                if key.endswith(code):
                    return data[key]
        except (KeyError, TypeError, AttributeError) as e:
            logger.warning(f"获取 {code} 实时行情失败: {e}")
        return None
    
    def _format_realtime_to_kline(self, quote: dict) -> Optional[dict]:
        """将实时行情格式化为K线结构"""
        if not quote or quote.get('now', 0) == 0:
            return None
        
        now = quote.get('now', 0)
        close = quote.get('close', now)  # 昨收
        
        # 计算涨跌幅
        change_pct = 0
        if close and close > 0:
            change_pct = round((now - close) / close * 100, 2)
        
        return {
            "time": quote.get('date', datetime.now().strftime('%Y-%m-%d')),
            "open": float(quote.get('open', 0)),
            "high": float(quote.get('high', 0)),
            "low": float(quote.get('low', 0)),
            "close": float(now),
            "volume": int(quote.get('turnover', 0)),
            "turnover": float(quote.get('volume', 0)),  # 成交额
            "name": quote.get('name', ''),
            "change_pct": change_pct,
            "bid1": float(quote.get('bid1', 0)),
            "ask1": float(quote.get('ask1', 0)),
            "update_time": quote.get('time', datetime.now().strftime('%H:%M:%S')),
        }
    
    def _merge_realtime(self, history: List[dict], realtime: dict) -> List[dict]:
        """合并历史K线与实时行情"""
        if not realtime or realtime.get('now', 0) == 0:
            return history
        
        today = datetime.now().strftime('%Y-%m-%d')
        realtime_date = realtime.get('date', today)
        
        # 如果实时数据日期不是今天，直接返回历史数据
        if realtime_date != today:
            return history
        
        # 格式化实时数据为K线
        realtime_kline = self._format_realtime_to_kline(realtime)
        if not realtime_kline:
            return history
        
        # 查找并更新/添加当日K线
        result = history.copy()
        found_today = False
        
        for i, kline in enumerate(result):
            if kline.get('time') == today:
                # 更新当日K线（用实时数据覆盖）
                result[i] = {
                    **kline,
                    "close": realtime_kline['close'],
                    "high": max(kline.get('high', 0), realtime_kline['high']),
                    "low": min(kline.get('low', float('inf')), realtime_kline['low']) if realtime_kline['low'] > 0 else kline.get('low', 0),
                    "volume": realtime_kline['volume'],
                }
                found_today = True
                break
        
        # 如果历史数据中没有当日，添加新的K线
        if not found_today and realtime_kline['close'] > 0:
            result.append({
                "time": today,
                "open": realtime_kline['open'],
                "high": realtime_kline['high'],
                "low": realtime_kline['low'],
                "close": realtime_kline['close'],
                "volume": realtime_kline['volume'],
            })
        
        return result


# 全局单例
_kline_service: Optional[RealtimeKlineService] = None


def get_realtime_kline_service(source: str = 'sina') -> RealtimeKlineService:
    """获取实时K线服务单例"""
    global _kline_service
    if _kline_service is None:
        _kline_service = RealtimeKlineService(realtime_source=source)
    return _kline_service
