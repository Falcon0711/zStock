# coding:utf8
"""
港股历史K线服务模块
基于腾讯港股K线接口，提供港股历史日K线数据（前复权）

数据源: http://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get

使用示例:
    service = HKDayKlineService()
    
    # 获取港股日K线
    klines = service.get_day_kline('00700', days=90)
"""

import json
import re
from typing import Dict, List, Optional
import requests


class HKDayKline:
    """港股日K线获取"""
    
    max_num = 1  # 每次只能查询一只股票
    
    def __init__(self):
        self._session = requests.Session()
    
    @property
    def stock_api(self) -> str:
        return "http://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get?_var=kline_dayqfq&param="
    
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
        return f"hk{code}"
    
    def get_day_kline(self, stock_code: str, days: int = 660) -> Optional[List[List]]:
        """
        获取港股日K线数据（前复权）
        
        Args:
            stock_code: 港股代码，如 '00700', '700', 'hk00700'
            days: 获取的天数，默认660天
        
        Returns:
            K线数据列表，格式: [[日期, 开盘, 收盘, 最高, 最低, 成交量], ...]
        """
        try:
            stock_with_prefix = self._format_stock_code(stock_code)
            
            # 构建请求参数
            params = f"{stock_with_prefix},day,,,{days},qfq"
            
            headers = self._get_headers()
            url = self.stock_api + params
            
            r = self._session.get(url, headers=headers, timeout=15)
            r.encoding = 'utf-8'
            
            # 解析JavaScript变量格式的响应
            raw_data = re.search(r"=(.+)", r.text)
            if not raw_data:
                print(f"⚠️ 无法解析港股K线数据")
                return None
            
            data = json.loads(raw_data.group(1))
            
            # 提取K线数据
            if "data" not in data:
                print(f"⚠️ 响应中没有data字段")
                return None
            
            stock_data = data["data"].get(stock_with_prefix)
            if not stock_data:
                print(f"⚠️ 未找到股票 {stock_code} 的数据")
                return None
            
            # 优先使用前复权数据
            kline_data = stock_data.get("qfqday") or stock_data.get("day")
            
            if not kline_data:
                print(f"⚠️ 股票 {stock_code} 没有K线数据")
                return None
            
            return kline_data
        
        except Exception as e:
            print(f"⚠️ 获取港股K线失败: {e}")
            return None


class HKDayKlineService:
    """
    港股日K线服务
    提供格式化的港股历史K线数据
    """
    
    def __init__(self):
        self._kline = HKDayKline()
    
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
                print(f"⚠️ 解析K线数据失败: {e}")
                continue
        
        return result
    
    def get_kline_dataframe(self, code: str, days: int = 90):
        """
        获取港股日K线数据（DataFrame格式）
        
        Args:
            code: 港股代码
            days: 获取天数
        
        Returns:
            pandas.DataFrame or None
        """
        try:
            import pandas as pd
            
            klines = self.get_day_kline(code, days=days)
            if not klines:
                return None
            
            df = pd.DataFrame(klines)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            return df
        except ImportError:
            print("⚠️ 需要安装pandas: pip install pandas")
            return None
        except Exception as e:
            print(f"⚠️ 转换为DataFrame失败: {e}")
            return None


# 全局单例
_hk_kline_service: Optional[HKDayKlineService] = None


def get_hk_kline_service() -> HKDayKlineService:
    """获取港股K线服务单例"""
    global _hk_kline_service
    if _hk_kline_service is None:
        _hk_kline_service = HKDayKlineService()
    return _hk_kline_service
