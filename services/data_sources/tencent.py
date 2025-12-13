# coding:utf8
"""
腾讯财经数据源
提供 A股历史K线、实时行情、分时数据、港股K线

API 端点:
- A股K线: http://web.ifzq.gtimg.cn/appstock/app/fqkline/get
- A股实时: http://qt.gtimg.cn/q={codes}
- 港股K线: http://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get
"""

import re
import time
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import requests

from .base import DataSource
from utils.logger import get_logger
from services.data_config import REQUEST_TIMEOUT, TENCENT_HEADERS

logger = get_logger(__name__)


class TencentDataSource(DataSource):
    """
    腾讯财经数据源
    
    用途:
    - A股历史K线 (首选)
    - A股实时行情 (备用)
    - A股分时数据
    - 港股K线
    
    特点: 速度快、稳定、支持前复权，最多获取640天
    """
    
    # 实时数据解析正则
    STOCK_CODE_REGEX = re.compile(r"(?<=_)\w+")
    
    def __init__(self):
        self._session = requests.Session()
        self._available = True
    
    @property
    def name(self) -> str:
        return "Tencent"
    
    @property
    def max_days(self) -> int:
        return 640
    
    def is_available(self) -> bool:
        return self._available
    
    def _get_headers(self) -> dict:
        return TENCENT_HEADERS
    
    def _get_symbol(self, code: str) -> str:
        """转换A股代码为腾讯格式"""
        if code.startswith(("sh", "sz", "bj")):
            return code
        if code.startswith(("5", "6", "9")):
            return "sh" + code
        elif code.startswith(("4", "8")):
            return "bj" + code
        else:
            return "sz" + code
    
    def _format_hk_code(self, code: str) -> str:
        """格式化港股代码"""
        if code.startswith(("hk", "HK")):
            code = code[2:]
        return f"hk{code.zfill(5)}"
    
    # ==================== A股历史K线 ====================
    
    def fetch_kline(
        self, 
        code: str, 
        days: int = 365,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取A股日K线前复权数据 (自适应分页)
        
        Args:
            code: 股票代码
            days: 获取天数 (超过640自动分页)
            end_date: 结束日期 (YYYY-MM-DD)
        """
        try:
            symbol = self._get_symbol(code)
            all_dfs = []
            remaining_days = days
            current_end_date = end_date
            
            # 分页循环
            while remaining_days > 0:
                fetch_days = min(remaining_days, self.max_days)
                
                # 构建本次请求 URL
                if current_end_date:
                    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,{current_end_date},{fetch_days},qfq"
                else:
                    # 第一次请求如果不传 end_date，腾讯默认返回最近的数据
                    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{fetch_days},qfq"
                
                # 发送请求 (带重试)
                data = None
                for attempt in range(3):
                    try:
                        resp = self._session.get(url, headers=self._get_headers(), timeout=REQUEST_TIMEOUT)
                        data = resp.json()
                        break
                    except (requests.RequestException, Exception):
                        if attempt == 2:
                             logger.warning(f" [腾讯] {code} 分页请求失败")
                        time.sleep(1)
                
                if not data or not data.get('data') or symbol not in data['data']:
                    break
                
                stock_data = data['data'][symbol]
                klines = stock_data.get('qfqday', stock_data.get('day'))
                
                if not klines:
                    break
                
                # 解析本次数据
                records = []
                for row in klines:
                    if len(row) < 6: continue
                    records.append({
                        "date": row[0],
                        "open": float(row[1]),
                        "close": float(row[2]),
                        "high": float(row[3]),
                        "low": float(row[4]),
                        "volume": float(row[5])
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
                
                # 防止死循环保护
                if len(all_dfs) > 50: 
                    break
            
            if not all_dfs:
                return None
                
            # 合并所有分片
            final_df = pd.concat(all_dfs, ignore_index=True)
            final_df = final_df.drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
            
            logger.info(f" [腾讯] {code} 总计获取 {len(final_df)} 条K线 (分 {len(all_dfs)} 页)")
            return final_df
            
        except Exception as e:
            logger.warning(f" [腾讯] {code} K线获取失败: {e}")
            return None
    
    # ==================== A股实时行情 ====================
    
    def get_realtime(self, codes: List[str]) -> Dict[str, Dict]:
        """
        获取A股实时行情
        
        Args:
            codes: 股票代码列表
        
        Returns:
            {code: {name, now, open, close, high, low, volume, ...}}
        """
        try:
            tencent_codes = [self._get_symbol(c) for c in codes]
            codes_str = ",".join(tencent_codes)
            
            url = f"http://qt.gtimg.cn/q={codes_str}"
            resp = self._session.get(url, headers=self._get_headers(), timeout=REQUEST_TIMEOUT)
            resp.encoding = 'gbk'
            
            return self._parse_realtime(resp.text, codes)
            
        except Exception as e:
            logger.warning(f" [腾讯] 实时行情获取失败: {e}")
            return {}
    
    def _parse_realtime(self, text: str, original_codes: List[str]) -> Dict[str, Dict]:
        """解析腾讯实时行情"""
        result = {}
        lines = text.strip().split('\n')
        
        for line in lines:
            if '~' not in line:
                continue
            
            try:
                # 提取代码
                code_match = self.STOCK_CODE_REGEX.search(line)
                if not code_match:
                    continue
                
                full_code = code_match.group()
                pure_code = full_code[2:] if full_code[:2] in ('sh', 'sz', 'bj') else full_code
                
                # 解析数据 (腾讯用~分隔)
                data_part = line.split('="')[1].rstrip('";') if '="' in line else ""
                parts = data_part.split('~')
                
                if len(parts) < 45:
                    continue
                
                def safe_float(s):
                    try:
                        return float(s) if s else 0.0
                    except (ValueError, TypeError):
                        return 0.0
                
                result[pure_code] = {
                    'name': parts[1],
                    'code': parts[2],
                    'now': safe_float(parts[3]),
                    'close': safe_float(parts[4]),  # 昨收
                    'open': safe_float(parts[5]),
                    'volume': safe_float(parts[6]),
                    'buy_volume': safe_float(parts[7]),
                    'sell_volume': safe_float(parts[8]),
                    'buy1': safe_float(parts[9]),
                    'sell1': safe_float(parts[19]),
                    'high': safe_float(parts[33]),
                    'low': safe_float(parts[34]),
                    'amount': safe_float(parts[37]),
                    'change_pct': safe_float(parts[32]),
                    'change': safe_float(parts[31]),
                }
            except (ValueError, IndexError, KeyError):
                continue
        
        return result
    
    # ==================== A股分时数据 ====================
    
    def get_intraday(self, code: str) -> Tuple[Optional[List], Optional[str], Optional[float]]:
        """
        获取A股分时数据
        
        Args:
            code: 股票代码
        
        Returns:
            (分时数据列表, 日期, 昨收价)
        """
        try:
            symbol = self._get_symbol(code)
            url = f"http://data.gtimg.cn/flashdata/hushen/minute/{symbol}.js"
            
            resp = self._session.get(url, headers=self._get_headers(), timeout=REQUEST_TIMEOUT)
            resp.encoding = 'gbk'
            
            # 解析数据
            lines = resp.text.split('\n')
            data_date = None
            preClose = None
            formatted_data = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('date:'):
                    data_date = line.split(':')[1].strip().strip('"')
                elif '\\n\\' in line or ':' in line:
                    continue
                elif line and len(line.split(' ')) >= 3:
                    parts = line.split(' ')
                    formatted_data.append({
                        'time': parts[0],
                        'price': float(parts[1]),
                        'volume': float(parts[2]) if len(parts) > 2 else 0,
                    })
            
            if formatted_data:
                logger.info(f" [腾讯] {code} 分时数据 {len(formatted_data)} 条")
                return formatted_data, data_date, preClose
            
            return None, None, None
            
        except Exception as e:
            logger.warning(f" [腾讯] {code} 分时数据失败: {e}")
            return None, None, None
    
    # ==================== 港股K线 ====================
    
    def fetch_hk_kline(self, code: str, days: int = 660) -> Optional[pd.DataFrame]:
        """
        获取港股日K线前复权数据
        
        Args:
            code: 港股代码 (如 00700, 700, hk00700)
            days: 获取天数 (最大660)
        
        Returns:
            DataFrame or None
        """
        try:
            hk_code = self._format_hk_code(code)
            url = f"http://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get?_var=kline_dayqfq&param={hk_code},day,,,{days},qfq"
            
            resp = self._session.get(url, headers=self._get_headers(), timeout=REQUEST_TIMEOUT)
            resp.encoding = 'utf-8'
            
            # 解析JS变量格式
            raw_data = re.search(r"=(.+)", resp.text)
            if not raw_data:
                return None
            
            import json
            data = json.loads(raw_data.group(1))
            
            if "data" not in data or hk_code not in data["data"]:
                return None
            
            stock_data = data["data"][hk_code]
            klines = stock_data.get("qfqday") or stock_data.get("day")
            
            if not klines:
                return None
            
            records = []
            for row in klines:
                if len(row) < 6:
                    continue
                records.append({
                    "date": row[0],
                    "open": float(row[1]),
                    "close": float(row[2]),
                    "high": float(row[3]),
                    "low": float(row[4]),
                    "volume": float(row[5]) if row[5] else 0,
                })
            
            if records:
                df = pd.DataFrame(records)
                logger.info(f" [腾讯] 港股{code} 获取 {len(df)} 条K线")
                return df
            
            return None
            
        except Exception as e:
            logger.warning(f" [腾讯] 港股{code} K线获取失败: {e}")
            return None
    # ==================== 腾讯全球指数 ====================

    # 港股指数映射
    HK_INDEX_MAP = {
        '^HSI': 'r_hkHSI',         # 恒生指数
        'HSI': 'r_hkHSI',
        'HSTECH.HK': 'r_hkHSTECH', # 恒生科技
        'HSTECH': 'r_hkHSTECH',
    }

    # 美股指数映射
    US_INDEX_MAP = {
        '^DJI': 'usDJI',       # 道琼斯
        'DJI': 'usDJI',
        '^IXIC': 'usIXIC',     # 纳斯达克综合
        'IXIC': 'usIXIC',
        '^GSPC': 'usINX',      # 标普500 (腾讯通常用 usINX 或 usSPX)
        'GSPC': 'usINX',
        '^NDX': 'usNDX',       # 纳斯达克100
        'NDX': 'usNDX',
        'QQQ': 'usQQQ',        # 纳指100ETF
    }

    def get_hk_index(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取港股指数"""
        code = self.HK_INDEX_MAP.get(symbol.upper())
        if not code:
            return None
        return self._fetch_global_index(code, symbol)

    def get_us_index(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取美股指数"""
        code = self.US_INDEX_MAP.get(symbol.upper())
        if not code:
            return None
        return self._fetch_global_index(code, symbol)

    def _fetch_global_index(self, code: str, display_symbol: str) -> Optional[Dict[str, Any]]:
        """通用全球指数解析 (腾讯格式)"""
        try:
            url = f"http://qt.gtimg.cn/q={code}"
            resp = self._session.get(url, headers=self._get_headers(), timeout=REQUEST_TIMEOUT)
            resp.encoding = 'gbk'  # 腾讯通常是GBK
            
            text = resp.text.strip()
            if not text or '="' not in text:
                return None
            
            data_part = text.split('="')[1].rstrip('";')
            parts = data_part.split('~')
            
            # 腾讯指数格式通常: 
            # 1:Name, 3:Price, 31:Change, 32:Pct, 30:Time
            if len(parts) > 32:
                name = parts[1]
                
                def safe_float(s):
                    try:
                        return float(s) if s else 0.0
                    except (ValueError, TypeError):
                        return 0.0
                
                price = safe_float(parts[3])
                change = safe_float(parts[31])
                change_pct = safe_float(parts[32])
                time_str = parts[30]
                
                # 腾讯时间格式可能是 "2025/12/09 17:25:29"(HK) 或 "2025-12-08 17:15:59"(US)
                # 简单处理
                
                if price > 0:
                    # logger.info(f" [腾讯] {display_symbol}: {price}, {change_pct}%")
                    return {
                        "name": name,
                        "price": price,
                        "change": change,
                        "change_pct": change_pct,
                        "time": time_str
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f" [腾讯] {display_symbol} 获取失败: {e}")
            return None
