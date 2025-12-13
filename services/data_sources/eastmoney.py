# coding:utf8
"""
东方财富数据源
提供 分时数据 和 市场指数

API 端点:
- 实时行情: https://push2.eastmoney.com/api/qt/stock/get
- 分时数据: https://push2his.eastmoney.com/api/qt/stock/trends2/get
- 历史K线: https://push2his.eastmoney.com/api/qt/stock/kline/get
"""

import time
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
import requests
import pandas as pd

from .base import DataSource
from utils.logger import get_logger
from services.data_config import REQUEST_TIMEOUT, EASTMONEY_HEADERS

logger = get_logger(__name__)


class EastmoneyDataSource(DataSource):
    """
    东方财富数据源
    
    用途:
    - 分时数据 (首选)
    - 市场指数
    
    特点: 数据丰富，但有风控机制（频繁请求可能被封）
    """
    
    def __init__(self):
        self._session = requests.Session()
        self._available = True
    
    @property
    def name(self) -> str:
        return "Eastmoney"
    
    @property
    def max_days(self) -> int:
        return 3000  # 支持较长历史
    
    def is_available(self) -> bool:
        return self._available
    
    def _get_headers(self) -> dict:
        return EASTMONEY_HEADERS
    
    def _get_secid(self, code: str) -> str:
        """转换股票代码为东财格式"""
        if code.startswith(("sh", "SH")):
            return f"1.{code[2:]}"
        elif code.startswith(("sz", "SZ")):
            return f"0.{code[2:]}"
        elif code.startswith(("5", "6", "9")):
            return f"1.{code}"
        elif code.startswith(("4", "8")):
            return f"0.{code}"  # 北交所
        else:
            return f"0.{code}"  # 深交所
    
    # ==================== K线数据 ====================
    
    def fetch_kline(
        self, 
        code: str, 
        days: int = 365,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取历史K线数据 (自适应分页)
        
        Args:
            code: 股票代码
            days: 获取天数 (超过3000自动分页)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            DataFrame or None
        """
        try:
            secid = self._get_secid(code)
            all_dfs = []
            remaining_days = days
            current_end_date = end_date
            
            # 分页循环
            while remaining_days > 0:
                fetch_days = min(remaining_days, self.max_days)
                
                # 计算结束日期
                if current_end_date:
                    end_str = current_end_date.replace('-', '')
                else:
                    end_str = datetime.now().strftime('%Y%m%d')
                
                url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
                params = {
                    "secid": secid,
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                    "klt": "101",  # 日K
                    "fqt": "1",    # 前复权
                    "end": end_str,
                    "lmt": fetch_days,
                }
                
                # 发送请求 (带重试)
                data = None
                for attempt in range(3):
                    try:
                        resp = self._session.get(url, params=params, headers=self._get_headers(), timeout=REQUEST_TIMEOUT)
                        data = resp.json()
                        break
                    except (requests.RequestException, Exception):
                        if attempt == 2:
                            logger.warning(f" [东财] {code} 分页请求失败")
                        time.sleep(1)
                
                if not data or not data.get('data') or not data['data'].get('klines'):
                    break
                
                klines = data['data']['klines']
                
                # 解析本次数据
                records = []
                for kline in klines:
                    parts = kline.split(',')
                    if len(parts) >= 7:
                        records.append({
                            'date': parts[0],
                            'open': float(parts[1]),
                            'close': float(parts[2]),
                            'high': float(parts[3]),
                            'low': float(parts[4]),
                            'volume': float(parts[5]),
                        })
                
                if not records:
                    break
                
                df_chunk = pd.DataFrame(records)
                all_dfs.append(df_chunk)
                
                # 准备下一次循环
                if len(df_chunk) < fetch_days:
                    # 取到的比要的少，说明已经到头了
                    break
                
                earliest_date = df_chunk['date'].min()
                # 往前推一天作为新的结束日期
                earliest_dt = datetime.strptime(earliest_date, "%Y-%m-%d")
                current_end_date = (earliest_dt - timedelta(days=1)).strftime("%Y-%m-%d")
                remaining_days -= len(df_chunk)
                
                # 防止死循环保护 (与腾讯一致)
                if len(all_dfs) > 50:
                    break
            
            if not all_dfs:
                return None
            
            # 合并所有分片
            final_df = pd.concat(all_dfs, ignore_index=True)
            final_df = final_df.drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
            
            logger.info(f" [东财] {code} 总计获取 {len(final_df)} 条K线 (分 {len(all_dfs)} 页)")
            return final_df
            
        except Exception as e:
            logger.warning(f" [东财] {code} K线获取失败: {e}")
            self._available = False
            return None
    
    # ==================== 实时行情 ====================
    
    def get_realtime(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取单只股票实时行情
        
        Args:
            code: 股票代码
        
        Returns:
            {name, now, open, close, high, low, volume, ...}
        """
        try:
            secid = self._get_secid(code)
            url = f"https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": secid,
                "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f170,f171"
            }
            
            resp = self._session.get(url, params=params, headers=self._get_headers(), timeout=REQUEST_TIMEOUT)
            data = resp.json()
            
            if data.get('data'):
                d = data['data']
                return {
                    'code': d.get('f57', code),
                    'name': d.get('f58', ''),
                    'now': d.get('f43', 0) / 100,  # 价格需除100
                    'open': d.get('f46', 0) / 100,
                    'high': d.get('f44', 0) / 100,
                    'low': d.get('f45', 0) / 100,
                    'close': d.get('f60', 0) / 100,  # 昨收
                    'volume': d.get('f47', 0),
                    'amount': d.get('f48', 0),
                    'change_pct': d.get('f170', 0) / 100,
                    'change': d.get('f171', 0) / 100,
                }
            
            return None
            
        except requests.RequestException as e:
            logger.warning(f" [东财] {code} 实时行情失败: {e}")
            return None
    
    # ==================== 分时数据 ====================
    
    def get_intraday(self, code: str) -> Tuple[Optional[List], Optional[str], Optional[float]]:
        """
        获取分时数据
        
        Args:
            code: 股票代码
        
        Returns:
            (分时数据列表, 日期, 昨收价)
        """
        try:
            secid = self._get_secid(code)
            url = f"https://push2his.eastmoney.com/api/qt/stock/trends2/get"
            params = {
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                "iscr": "0",
                "iscca": "0",
                "ndays": "1"
            }
            
            resp = self._session.get(url, params=params, headers=self._get_headers(), timeout=REQUEST_TIMEOUT)
            data = resp.json()
            
            if data.get('data') and data['data'].get('trends'):
                trends = data['data']['trends']
                preClose = data['data'].get('preClose', 0) / 100
                
                # 解析分时数据
                formatted_data = []
                for trend in trends:
                    parts = trend.split(',')
                    if len(parts) >= 6:
                        formatted_data.append({
                            'time': parts[0],
                            'price': float(parts[2]) / 100,
                            'volume': float(parts[5]),
                            'avg_price': float(parts[7]) if len(parts) > 7 else 0,
                        })
                
                # 获取日期
                data_date = trends[0].split(',')[0].split()[0] if trends else None
                
                logger.info(f" [东财] {code} 分时数据 {len(formatted_data)} 条")
                return formatted_data, data_date, preClose
            
            return None, None, None
            
        except requests.RequestException as e:
            logger.warning(f" [东财] {code} 分时数据失败: {e}")
            return None, None, None
    
    # ==================== 港股K线 ====================
    
    def _get_hk_secid(self, code: str) -> str:
        """转换港股代码为东财格式"""
        if code.startswith(("hk", "HK")):
            code = code[2:]
        return f"116.{code.zfill(5)}"
    
    def fetch_hk_kline(self, code: str, days: int = 365) -> Optional[pd.DataFrame]:
        """
        获取港股日K线数据
        
        Args:
            code: 港股代码 (如 00700, 700, hk00700)
            days: 获取天数
        
        Returns:
            DataFrame or None
        """
        try:
            secid = self._get_hk_secid(code)
            
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101",  # 日K
                "fqt": "1",    # 前复权
                "end": datetime.now().strftime('%Y%m%d'),
                "lmt": min(days, 3000),
            }
            
            resp = self._session.get(url, params=params, headers=self._get_headers(), timeout=REQUEST_TIMEOUT)
            data = resp.json()
            
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                records = []
                for kline in klines:
                    parts = kline.split(',')
                    if len(parts) >= 7:
                        records.append({
                            'date': parts[0],
                            'open': float(parts[1]),
                            'close': float(parts[2]),
                            'high': float(parts[3]),
                            'low': float(parts[4]),
                            'volume': float(parts[5]),
                        })
                
                if records:
                    df = pd.DataFrame(records)
                    logger.info(f" [东财] 港股{code} 获取 {len(df)} 条K线")
                    return df
            
            return None
            
        except requests.RequestException as e:
            logger.warning(f" [东财] 港股{code} K线获取失败: {e}")
            return None
