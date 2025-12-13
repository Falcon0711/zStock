# coding:utf8
"""
AkShare数据源
提供A股日K线前复权数据（东方财富底层）
"""

import time
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import pandas as pd

from .base import DataSource
from utils.logger import get_logger

logger = get_logger(__name__)


class AkShareDataSource(DataSource):
    """
    AkShare数据源（备用）
    
    底层使用东方财富数据，作为腾讯数据源的备用
    限制: 最多640天（避免全量请求触发封禁）
    """
    
    def __init__(self):
        self._available = True
        self._max_retries = 3
    
    @property
    def name(self) -> str:
        return "AkShare"
    
    @property
    def max_days(self) -> int:
        """支持获取的最大的天数 (动态计算)"""
        from datetime import datetime
        start = datetime(1990, 12, 19)
        return (datetime.now() - start).days + 365  # 支持超长历史
    
    def is_available(self) -> bool:
        return self._available
    
    def get_realtime(self, codes: List[str]) -> Dict[str, Dict]:
        """
        获取实时行情（AkShare不支持实时行情）
        
        Returns:
            空字典
        """
        logger.warning("[AkShare] 不支持实时行情")
        return {}
    
    def fetch_kline(
        self, 
        code: str, 
        days: int = 365,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取日K线前复权数据
        
        Args:
            code: 股票代码 (6位)
            days: 获取天数
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            DataFrame or None
        """
        try:
            import akshare as ak
        except ImportError:
            logger.warning("[AkShare] 未安装 akshare")
            self._available = False
            return None
        
        delay = 2.0
        
        for attempt in range(self._max_retries + 1):
            try:
                # 移除640天限制，支持全量获取
                actual_days = days
                
                # 计算日期范围
                if end_date:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                else:
                    end_dt = datetime.now()
                
                start_dt = end_dt - timedelta(days=actual_days + 60)
                
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period='daily',
                    start_date=start_dt.strftime('%Y%m%d'),
                    end_date=end_dt.strftime('%Y%m%d'),
                    adjust='qfq'
                )
                
                if df is None or df.empty:
                    return None
                
                # 标准化列名
                df = df.rename(columns={
                    '日期': 'date', '开盘': 'open', '最高': 'high',
                    '最低': 'low', '收盘': 'close', '成交量': 'volume'
                })
                df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
                
                logger.info(f"[AkShare] {code} 获取 {len(df)} 条记录")
                self._available = True
                return df
                
            except Exception as e:
                if attempt < self._max_retries:
                    logger.warning(f"[AkShare] {code} 尝试 {attempt + 1}/{self._max_retries + 1}: {e}")
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.warning(f"[AkShare] {code} 获取失败: {e}")
                    self._available = False
        
        return None
