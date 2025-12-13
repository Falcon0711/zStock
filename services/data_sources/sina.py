# coding:utf8
"""
新浪财经数据源
提供 A股实时行情 和 美股指数

API 端点:
- A股实时: http://hq.sinajs.cn/list={codes}
- 美股指数: http://hq.sinajs.cn/list=int_dji,int_nasdaq,int_sp500
"""

import re
import time
from typing import Optional, Dict, List, Any
from datetime import datetime
import requests
import pandas as pd

from .base import DataSource
from utils.logger import get_logger
from services.data_config import REQUEST_TIMEOUT, SINA_HEADERS

logger = get_logger(__name__)


class SinaDataSource(DataSource):
    """
    新浪财经数据源
    
    用途:
    - A股实时行情 (首选)
    - 美股指数 (首选)
    
    特点: 官方授权接口，稳定快速，无封禁风险
    """
    
    # A股实时数据解析正则
    STOCK_REGEX = re.compile(
        r"(\d+)=[^\s]([^\s,]+?)%s%s"
        % (r",([\.\d]+)" * 29, r",([-\.\d:]+)" * 2)
    )
    
    # 美股指数代码映射
    US_INDEX_MAP = {
        '^DJI': 'gb_dji',      # 道琼斯
        'DJI': 'gb_dji',
        '^IXIC': 'gb_ixic',    # 纳斯达克综合
        'IXIC': 'gb_ixic',
        '^GSPC': 'gb_inx',     # 标普500
        'GSPC': 'gb_inx',
        '^NDX': 'gb_ndx',      # 纳斯达克100
        'NDX': 'gb_ndx',
        'QQQ': 'gb_qqq',       # 纳指100ETF
    }

    # 港股指数代码映射 (新浪 rt_hk 接口)
    HK_INDEX_MAP = {
        '^HSI': 'rt_hkHSI',        # 恒生指数
        'HSI': 'rt_hkHSI',
        'HSTECH.HK': 'rt_hkHSTECH', # 恒生科技
        'HSTECH': 'rt_hkHSTECH',
    }
    
    def __init__(self):
        self._session = requests.Session()
        self._available = True
    
    @property
    def name(self) -> str:
        return "Sina"
    
    @property
    def max_days(self) -> int:
        return 0  # 实时数据源，不支持历史
    
    def is_available(self) -> bool:
        return self._available
    
    def _get_headers(self) -> dict:
        return SINA_HEADERS
    
    def _get_stock_prefix(self, code: str) -> str:
        """转换股票代码为新浪格式"""
        if code.startswith(("sh", "sz", "bj")):
            return code
        if code.startswith(("5", "6", "9")):
            return "sh" + code
        elif code.startswith(("4", "8")):
            return "bj" + code
        else:
            return "sz" + code
    
    # ==================== K线数据 (不支持) ====================
    
    def fetch_kline(
        self, 
        code: str, 
        days: int = 365,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """新浪不支持历史K线，返回None"""
        return None
    
    # ==================== 实时行情 ====================
    
    def get_realtime(self, codes: List[str]) -> Dict[str, Dict]:
        """
        获取A股实时行情
        
        Args:
            codes: 股票代码列表，如 ['600519', '000001']
        
        Returns:
            {code: {name, now, open, close, high, low, volume, ...}}
        """
        try:
            # 转换代码格式
            sina_codes = [self._get_stock_prefix(c) for c in codes]
            codes_str = ",".join(sina_codes)
            
            url = f"http://hq.sinajs.cn/list={codes_str}"
            resp = self._session.get(url, headers=self._get_headers(), timeout=REQUEST_TIMEOUT)
            resp.encoding = 'gbk'
            
            return self._parse_realtime(resp.text, codes)
            
        except requests.RequestException as e:
            logger.warning(f" [新浪] 实时行情获取失败: {e}")
            return {}
    
    def _parse_realtime(self, text: str, original_codes: List[str]) -> Dict[str, Dict]:
        """解析新浪实时行情数据"""
        result = {}
        lines = text.strip().split('\n')
        
        for i, line in enumerate(lines):
            if '="' not in line:
                continue
            
            try:
                code_match = re.search(r'hq_str_(\w+)=', line)
                if not code_match:
                    continue
                
                full_code = code_match.group(1)
                # 确定 Key: 优先匹配原始代码列表中的完整代码，否则尝试去前缀
                key_code = full_code
                pure_code = full_code[2:] if full_code[:2] in ('sh', 'sz', 'bj') else full_code
                
                if full_code in original_codes:
                    key_code = full_code
                elif pure_code in original_codes:
                    key_code = pure_code
                
                # 解析数据
                data_str = line.split('="')[1].rstrip('";')
                if not data_str:
                    continue
                
                parts = data_str.split(',')
                if len(parts) < 30: # 稍微放宽长度限制
                    continue
                
                # 区分指数和股票的数据映射
                # 指数代码通常以 sh000 或 sz399 开头
                is_index = full_code.startswith(('sh000', 'sz399'))
                
                # 定义安全转换函数
                def safe_float(v):
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        return 0.0

                
                if is_index:
                    # 指数: 1=当前点数, 2=当前价格(与1相同?), 3=涨跌率? 
                    # 实际上新浪指数接口: 1=当前, 2=昨收, 3=开盘, 4=高, 5=低
                    name = parts[0]
                    now = safe_float(parts[1])
                    pre_close = safe_float(parts[2])
                    open_price = safe_float(parts[3])
                    high = safe_float(parts[4])
                    low = safe_float(parts[5])
                    volume = safe_float(parts[8])
                    amount = safe_float(parts[9])
                else:
                    # 股票: 0=name, 1=open, 2=pre_close, 3=current
                    name = parts[0]
                    open_price = safe_float(parts[1])
                    pre_close = safe_float(parts[2])
                    now = safe_float(parts[3])
                    high = safe_float(parts[4])
                    low = safe_float(parts[5])
                    volume = safe_float(parts[8])
                    amount = safe_float(parts[9])

                result[key_code] = {
                    'name': name,
                    'open': open_price,
                    'close': pre_close,
                    'now': now,
                    'high': high,
                    'low': low,
                    'buy': 0.0,
                    'sell': 0.0,
                    'volume': volume,
                    'amount': amount,
                    'date': parts[30] if len(parts) > 30 else datetime.now().strftime('%Y-%m-%d'),
                    'time': parts[31] if len(parts) > 31 else '',
                }
            except (ValueError, KeyError, IndexError) as e:
                logger.error(f"解析行失败: code={key_code}, error={e}")
                continue
        
        return result
    
    # ==================== 美股指数 ====================
    
    def get_us_index(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取美股指数
        """
        sina_code = self.US_INDEX_MAP.get(symbol.upper())
        if not sina_code:
            return None
        
        return self._fetch_global_index(sina_code, symbol)

    # ==================== 港股指数 ====================

    def get_hk_index(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取港股指数 (rt_hkHSI)
        """
        sina_code = self.HK_INDEX_MAP.get(symbol.upper())
        if not sina_code:
            return None
            
        return self._fetch_global_index(sina_code, symbol)
        
    def _fetch_global_index(self, sina_code: str, display_symbol: str) -> Optional[Dict[str, Any]]:
        """通用全球指数获取与解析 (美股/港股)"""
        try:
            url = f"http://hq.sinajs.cn/list={sina_code}"
            # 港股接口必须要 Referer
            headers = self._get_headers()
            resp = self._session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.encoding = 'gbk'
            
            text = resp.text.strip()
            if '="' not in text or text.endswith('="";'):
                return None
            
            # 提取数据
            data_str = text.split('="')[1]
            data_str = data_str.rstrip(';\n\r"')
            parts = data_str.split(',')
            
            price = 0.0
            change = 0.0
            change_pct = 0.0
            name = ""
            
            # 定义安全转换函数
            def safe_float(v):
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return 0.0
            
            if sina_code.startswith('rt_hk'):
                # 港股 (rt_hk) 格式:
                # 0=EnName, 1=CnName, 2=Open, 3=PrevClose, 6=Price, 7=Change, 8=Pct
                if len(parts) > 8:
                    name = parts[1]
                    price = safe_float(parts[6])
                    change = safe_float(parts[7])
                    change_pct = safe_float(parts[8])
            elif sina_code.startswith('gb_'):
                # 美股 (gb_) 格式:
                # 0=Name, 1=Price, 2=Pct, 3=Time, 4=Change
                if len(parts) > 4:
                    name = parts[0]
                    price = safe_float(parts[1])
                    change = safe_float(parts[4])
                    change_pct = safe_float(parts[2])
            else:
                # 旧版美股 (int_) 格式 (兼容):
                # 0=Name, 1=Price, 2=Change, 3=Pct
                if len(parts) >= 4:
                    name = parts[0]
                    price = safe_float(parts[1])
                    change = safe_float(parts[2])
                    change_pct = safe_float(parts[3])
            
            if price > 0:
                # logger.info(f" [新浪] {display_symbol}: {price}, {change_pct}%")
                return {
                    "name": name,
                    "price": price,
                    "change": change,
                    "change_pct": change_pct,
                    "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
        except requests.RequestException as e:
            logger.warning(f" [新浪] {display_symbol} 获取失败: {e}")
        
        return None
    
    # ==================== 分时数据 ====================
    
    def get_intraday(self, code: str) -> Optional[List[Dict]]:
        """
        获取A股分时数据
        
        API: http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData
        
        Args:
            code: 股票代码
        
        Returns:
            [{time, price, volume, avg_price}, ...]
        """
        try:
            sina_code = self._get_stock_prefix(code)
            url = f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
            params = {
                "symbol": sina_code,
                "scale": "5",  # 5分钟级别
                "ma": "no",
                "datalen": "48"  # 一天约48个5分钟
            }
            
            resp = self._session.get(url, params=params, headers=self._get_headers(), timeout=REQUEST_TIMEOUT)
            data = resp.json()
            
            if not data:
                return None
            
            formatted_data = []
            for item in data:
                formatted_data.append({
                    'time': item.get('day', ''),
                    'price': float(item.get('close', 0)),
                    'open': float(item.get('open', 0)),
                    'high': float(item.get('high', 0)),
                    'low': float(item.get('low', 0)),
                    'volume': float(item.get('volume', 0)),
                })
            
            if formatted_data:
                logger.info(f" [新浪] {code} 分时数据 {len(formatted_data)} 条")
                return formatted_data
            
            return None
            
        except requests.RequestException as e:
            logger.warning(f" [新浪] {code} 分时数据失败: {e}")
            return None
