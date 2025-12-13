# coding:utf8
"""
Yahoo Finance 数据源
提供美股指数和个股数据（作为备用）

使用 yfinance 库
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd

from .base import DataSource
from utils.logger import get_logger

logger = get_logger(__name__)


class YahooDataSource(DataSource):
    """
    Yahoo Finance 数据源（备用）
    
    用途:
    - 美股指数 (备用)
    - 美股个股
    
    特点: 免费稳定，但速度较慢
    """
    
    def __init__(self):
        self._available = True
        try:
            import yfinance as yf
            self._yf = yf
        except ImportError:
            logger.warning("[Yahoo] yfinance 未安装")
            self._available = False
            self._yf = None
    
    @property
    def name(self) -> str:
        return "Yahoo"
    
    @property
    def max_days(self) -> int:
        return 9999  # 支持全量历史
    
    def is_available(self) -> bool:
        return self._available and self._yf is not None
    
    def get_realtime(self, codes: List[str]) -> Dict[str, Dict]:
        """
        获取实时行情（Yahoo主要用于美股，A股实时行情不支持）
        
        Returns:
            空字典
        """
        logger.warning("[Yahoo] A股实时行情不支持")
        return {}
    
    # ==================== K线数据 ====================
    
    def fetch_kline(
        self, 
        code: str, 
        days: int = 365,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取历史K线数据
        
        Args:
            code: 股票代码 (Yahoo格式，如 AAPL, ^DJI)
            days: 获取天数
            end_date: 结束日期
        
        Returns:
            DataFrame or None
        """
        if not self._yf:
            return None
        
        try:
            ticker = self._yf.Ticker(code)
            
            # 计算期间
            if days <= 7:
                period = "5d"
            elif days <= 30:
                period = "1mo"
            elif days <= 90:
                period = "3mo"
            elif days <= 180:
                period = "6mo"
            elif days <= 365:
                period = "1y"
            elif days <= 730:
                period = "2y"
            else:
                period = "max"
            
            hist = ticker.history(period=period)
            
            if hist is not None and not hist.empty:
                df = hist.reset_index()
                df = df.rename(columns={
                    'Date': 'date',
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                })
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
                
                logger.info(f" [Yahoo] {code} 获取 {len(df)} 条K线")
                return df
            
            return None
            
        except (ValueError, KeyError, TypeError) as e:
            logger.warning(f" [Yahoo] {code} 获取失败: {e}")
            return None
    
    # ==================== 美股指数 ====================
    
    def get_us_index(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取美股指数
        
        Args:
            symbol: 指数代码，如 '^DJI', '^IXIC', '^GSPC'
        
        Returns:
            {price, change, change_pct, time}
        """
        if not self._yf:
            return None
        
        try:
            ticker = self._yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            
            if hist is not None and len(hist) >= 2:
                latest = hist.iloc[-1]
                previous = hist.iloc[-2]
                
                price = float(latest['Close'])
                change = float(latest['Close'] - previous['Close'])
                change_pct = (change / previous['Close'] * 100)
                
                logger.info(f" [Yahoo] {symbol}: {price:.2f}, {change_pct:.2f}%")
                
                return {
                    "price": price,
                    "change": change,
                    "change_pct": change_pct,
                    "time": datetime.now().strftime('%Y-%m-%d')
                }
            elif hist is not None and len(hist) == 1:
                latest = hist.iloc[-1]
                price = float(latest['Close'])
                
                return {
                    "price": price,
                    "change": 0.0,
                    "change_pct": 0.0,
                    "time": datetime.now().strftime('%Y-%m-%d')
                }
                
        except (ValueError, KeyError, TypeError) as e:
            logger.warning(f" [Yahoo] {symbol} 获取失败: {e}")
        
        return None
