# coding:utf8
"""
港股历史K线服务模块
基于腾讯港股K线接口，提供港股历史日K线数据（前复权）

使用示例:
    service = HKDayKlineService()
    
    # 获取港股日K线
    klines = service.get_day_kline('00700', days=90)
"""

import json
import re
from typing import Dict, List, Optional
import requests

from utils.logger import get_logger

# 使用统一的数据源模块
from services.data_sources import TencentDataSource

logger = get_logger(__name__)



class HKDayKline:
    """港股日K线获取（代理到 TencentDataSource）"""
    
    def __init__(self):
        self._source = TencentDataSource()
    
    def _format_stock_code(self, code: str) -> str:
        """格式化港股代码为标准格式"""
        if code.startswith(("hk", "HK")):
            code = code[2:]
        code = code.zfill(5)
        return f"hk{code}"
    
    def get_day_kline(self, stock_code: str, days: int = 660) -> Optional[List[List]]:
        """
        获取港股日K线数据（前复权）
        
        委托给 TencentDataSource.fetch_hk_kline()
        """
        stock_with_prefix = self._format_stock_code(stock_code)
        return self._source.fetch_hk_kline(stock_with_prefix, days=days)


class HKDayKlineService:
    """
    港股日K线服务
    提供格式化的港股历史K线数据，支持本地缓存
    """
    
    def __init__(self):
        self._kline = HKDayKline()
        self._local_service = None  # 延迟初始化
    
    def _get_local_service(self):
        """获取本地数据服务（延迟初始化）"""
        if self._local_service is None:
            from services.local_data_service import get_local_data_service
            self._local_service = get_local_data_service()
        return self._local_service
    
    def _normalize_code(self, code: str) -> str:
        """标准化港股代码为 hk00700 格式"""
        if code.startswith(("hk", "HK")):
            code = code[2:]
        return f"hk{code.zfill(5)}"
    
    def get_day_kline(self, code: str, days: int = 90) -> List[Dict]:
        """
        获取港股日K线数据（格式化为标准K线结构）
        
        Args:
            code: 港股代码
            days: 获取天数，默认90天
        
        Returns:
            [{date, open, close, high, low, volume}, ...]
        """
        raw_data = self._kline.get_day_kline(code, days=days)
        
        if not raw_data:
            return []
        
        result = []
        for item in raw_data:
            try:
                # K线数据格式: [日期, 开盘, 收盘, 最高, 最低, 成交量, ...]
                if len(item) < 6:
                    continue
                
                result.append({
                    "date": item[0],
                    "open": float(item[1]),
                    "close": float(item[2]),
                    "high": float(item[3]),
                    "low": float(item[4]),
                    "volume": float(item[5]) if item[5] else 0,
                })
            except (ValueError, IndexError) as e:
                logger.warning(f"解析K线数据失败: {e}")
                continue
        
        return result
    
    def get_kline_smart(self, code: str, days: int = 90):
        """
        智能获取港股K线数据（带本地缓存 + 渐进式补全）
        
        逻辑：
        1. 首次访问 → 获取最近660天数据并缓存
        2. 后续访问 → 增量更新 + 向前补全
        3. 返回本地数据
        
        Args:
            code: 港股代码
            days: 返回最近N天的数据
        
        Returns:
            pandas.DataFrame or None
        """
        import pandas as pd
        import time
        
        local_service = self._get_local_service()
        hk_code = self._normalize_code(code)
        
        # 1. 检查是否已有数据
        if not local_service.is_full_sync_completed(hk_code):
            logger.info(f"[港股初始同步] {hk_code}: 首次访问，获取历史数据...")
            time.sleep(0.5)
            
            # 获取初始数据
            initial_data = self.get_day_kline(code, days=660)
            if initial_data:
                df = pd.DataFrame(initial_data)
                local_service.save_stock_data(hk_code, df)
                local_service.mark_full_sync_completed(hk_code)
                logger.info(f"[港股初始同步] {hk_code}: 完成，获取 {len(initial_data)} 条记录")
        
        # 2. 增量更新
        last_date = local_service.get_last_data_date(hk_code)
        if last_date and local_service.needs_update(last_date):
            logger.debug(f"[港股增量更新] {hk_code}: 最后日期{last_date}")
            time.sleep(0.5)
            new_data = self.get_day_kline(code, days=30)
            if new_data:
                df = pd.DataFrame(new_data)
                local_service.save_stock_data(hk_code, df)
        
        # 3. 向前补全
        first_date = local_service.get_first_data_date(hk_code)
        if first_date:
            backward_data = self._fetch_backward(code, first_date)
            if backward_data:
                df = pd.DataFrame(backward_data)
                saved = local_service.save_stock_data(hk_code, df)
                if saved > 0:
                    logger.debug(f"[港股向前补全] {hk_code}: 新增 {saved} 条更早记录")
        
        # 4. 返回本地数据
        return local_service.get_stock_data(hk_code, days)
    
    def _fetch_backward(self, code: str, first_date: str) -> List[Dict]:
        """向前获取更早的历史数据"""
        from datetime import datetime, timedelta
        
        try:
            # 计算结束日期
            end_dt = datetime.strptime(first_date, '%Y-%m-%d') - timedelta(days=1)
            
            # 获取更早的数据
            raw_data = self._kline.get_day_kline(code, days=660)
            if not raw_data:
                return []
            
            result = []
            for item in raw_data:
                if len(item) < 6:
                    continue
                record_date = item[0]
                # 只保留 first_date 之前的数据
                if record_date >= first_date:
                    continue
                result.append({
                    "date": record_date,
                    "open": float(item[1]),
                    "close": float(item[2]),
                    "high": float(item[3]),
                    "low": float(item[4]),
                    "volume": float(item[5]) if item[5] else 0,
                })
            
            return result
        except (ValueError, IndexError, KeyError):
            return []
    
    def get_kline_dataframe(self, code: str, days: int = 90):
        """
        获取港股日K线数据（DataFrame格式，带缓存）
        
        Args:
            code: 港股代码
            days: 获取天数
        
        Returns:
            pandas.DataFrame or None
        """
        # 使用智能获取方法（带缓存）
        return self.get_kline_smart(code, days)


# 全局单例
_hk_kline_service: Optional[HKDayKlineService] = None


def get_hk_kline_service() -> HKDayKlineService:
    """获取港股K线服务单例"""
    global _hk_kline_service
    if _hk_kline_service is None:
        _hk_kline_service = HKDayKlineService()
    return _hk_kline_service

