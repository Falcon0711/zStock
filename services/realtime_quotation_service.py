# coding:utf8
"""
实时行情服务模块
支持新浪和腾讯数据源获取 A股实时行情

数据源:
- 新浪: http://hq.sinajs.cn/rn={timestamp}&list=股票代码
- 腾讯: http://qt.gtimg.cn/q=股票代码

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


# 股票代码路径
STOCK_CODE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "stock_codes.json")


def get_stock_type(stock_code: str) -> str:
    """
    判断股票代码对应的证券市场
    
    匹配规则:
    - ['43', '83', '87', '92'] 开头为 bj (北交所)
    - ['5', '6', '7', '9', '110', '113', '118', '132', '204'] 开头为 sh (上交所)
    - 其余为 sz (深交所)
    
    Args:
        stock_code: 股票代码，如 '600519' 或 'sh600519'
    
    Returns:
        'sh', 'sz', 或 'bj'
    """
    assert isinstance(stock_code, str), "stock code need str type"
    
    # 如果已有前缀直接返回
    if stock_code.startswith(("sh", "sz", "zz", "bj")):
        return stock_code[:2]
    
    bj_head = ("43", "83", "87", "92")
    sh_head = ("5", "6", "7", "9", "110", "113", "118", "132", "204")
    
    if stock_code.startswith(bj_head):
        return "bj"
    elif stock_code.startswith(sh_head):
        return "sh"
    return "sz"


class SinaQuotation:
    """新浪实时行情获取"""
    
    max_num = 800  # 每次请求最大股票数
    
    # 解析正则
    grep_detail = re.compile(
        r"(\d+)=[^\s]([^\s,]+?)%s%s"
        % (r",([\.\d]+)" * 29, r",([-\.\d:]+)" * 2)
    )
    grep_detail_with_prefix = re.compile(
        r"(\w{2}\d+)=[^\s]([^\s,]+?)%s%s"
        % (r",([\.\d]+)" * 29, r",([-\.\d:]+)" * 2)
    )
    del_null_data_stock = re.compile(r"(\w{2}\d+)=\"\";")
    
    def __init__(self):
        self._session = requests.Session()
    
    @property
    def stock_api(self) -> str:
        return f"http://hq.sinajs.cn/rn={int(time.time() * 1000)}&list="
    
    def _get_headers(self) -> dict:
        return {
            "Accept-Encoding": "gzip, deflate, sdch",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/54.0.2840.100 Safari/537.36"
            ),
            "Referer": "http://finance.sina.com.cn/"
        }
    
    def _gen_stock_prefix(self, stock_codes: List[str]) -> List[str]:
        """为股票代码添加市场前缀"""
        return [get_stock_type(code) + code[-6:] for code in stock_codes]
    
    def _fetch_stocks(self, stock_list: str) -> Optional[str]:
        """获取一批股票数据"""
        try:
            headers = self._get_headers()
            r = self._session.get(self.stock_api + stock_list, headers=headers, timeout=10)
            return r.text
        except Exception as e:
            print(f"⚠️ 新浪行情请求失败: {e}")
            return None
    
    def get_realtime(self, stock_codes: Union[str, List[str]], prefix: bool = False) -> Dict:
        """
        获取实时行情
        
        Args:
            stock_codes: 单个股票代码或代码列表
            prefix: 返回结果是否带市场前缀
        
        Returns:
            行情字典 {代码: {name, now, open, close, high, low, ...}}
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
    
    def get_market_snapshot(self, stock_codes: List[str], prefix: bool = False) -> Dict:
        """获取多只股票快照"""
        return self.get_realtime(stock_codes, prefix=prefix)
    
    def _parse_response(self, rep_data: List[str], prefix: bool = False) -> Dict:
        """解析响应数据"""
        stocks_detail = "".join(rep_data)
        stocks_detail = self.del_null_data_stock.sub('', stocks_detail)
        stocks_detail = stocks_detail.replace(' ', '')
        
        grep_str = self.grep_detail_with_prefix if prefix else self.grep_detail
        result = grep_str.finditer(stocks_detail)
        
        stock_dict = {}
        for stock_match_object in result:
            stock = stock_match_object.groups()
            try:
                stock_dict[stock[0]] = {
                    "name": stock[1],
                    "open": float(stock[2]) if stock[2] else 0,
                    "close": float(stock[3]) if stock[3] else 0,  # 昨收
                    "now": float(stock[4]) if stock[4] else 0,
                    "high": float(stock[5]) if stock[5] else 0,
                    "low": float(stock[6]) if stock[6] else 0,
                    "buy": float(stock[7]) if stock[7] else 0,
                    "sell": float(stock[8]) if stock[8] else 0,
                    "turnover": int(float(stock[9])) if stock[9] else 0,  # 成交量（股）
                    "volume": float(stock[10]) if stock[10] else 0,  # 成交额
                    "bid1_volume": int(float(stock[11])) if stock[11] else 0,
                    "bid1": float(stock[12]) if stock[12] else 0,
                    "bid2_volume": int(float(stock[13])) if stock[13] else 0,
                    "bid2": float(stock[14]) if stock[14] else 0,
                    "bid3_volume": int(float(stock[15])) if stock[15] else 0,
                    "bid3": float(stock[16]) if stock[16] else 0,
                    "bid4_volume": int(float(stock[17])) if stock[17] else 0,
                    "bid4": float(stock[18]) if stock[18] else 0,
                    "bid5_volume": int(float(stock[19])) if stock[19] else 0,
                    "bid5": float(stock[20]) if stock[20] else 0,
                    "ask1_volume": int(float(stock[21])) if stock[21] else 0,
                    "ask1": float(stock[22]) if stock[22] else 0,
                    "ask2_volume": int(float(stock[23])) if stock[23] else 0,
                    "ask2": float(stock[24]) if stock[24] else 0,
                    "ask3_volume": int(float(stock[25])) if stock[25] else 0,
                    "ask3": float(stock[26]) if stock[26] else 0,
                    "ask4_volume": int(float(stock[27])) if stock[27] else 0,
                    "ask4": float(stock[28]) if stock[28] else 0,
                    "ask5_volume": int(float(stock[29])) if stock[29] else 0,
                    "ask5": float(stock[30]) if stock[30] else 0,
                    "date": stock[31],
                    "time": stock[32],
                }
            except (ValueError, IndexError) as e:
                print(f"⚠️ 解析股票 {stock[0]} 数据失败: {e}")
                continue
        
        return stock_dict


class TencentQuotation:
    """腾讯实时行情获取"""
    
    max_num = 60  # 腾讯API每次最多60只
    grep_stock_code = re.compile(r"(?<=_)\w+")
    
    def __init__(self):
        self._session = requests.Session()
    
    @property
    def stock_api(self) -> str:
        return "http://qt.gtimg.cn/q="
    
    def _get_headers(self) -> dict:
        return {
            "Accept-Encoding": "gzip, deflate, sdch",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/54.0.2840.100 Safari/537.36"
            ),
        }
    
    def _gen_stock_prefix(self, stock_codes: List[str]) -> List[str]:
        """为股票代码添加市场前缀"""
        return [get_stock_type(code) + code[-6:] for code in stock_codes]
    
    def _fetch_stocks(self, stock_list: str) -> Optional[str]:
        """获取一批股票数据"""
        try:
            headers = self._get_headers()
            r = self._session.get(self.stock_api + stock_list, headers=headers, timeout=10)
            return r.text
        except Exception as e:
            print(f"⚠️ 腾讯行情请求失败: {e}")
            return None
    
    def get_realtime(self, stock_codes: Union[str, List[str]], prefix: bool = False) -> Dict:
        """获取实时行情"""
        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]
        
        stock_with_prefix = self._gen_stock_prefix(stock_codes)
        
        # 分批请求（使用线程池并发）
        results = []
        batches = []
        for i in range(0, len(stock_with_prefix), self.max_num):
            batch = stock_with_prefix[i:i + self.max_num]
            batches.append(",".join(batch))
        
        if len(batches) > 1:
            with ThreadPoolExecutor(max_workers=min(len(batches), 10)) as executor:
                results = list(executor.map(self._fetch_stocks, batches))
        else:
            for batch in batches:
                data = self._fetch_stocks(batch)
                if data:
                    results.append(data)
        
        results = [r for r in results if r is not None]
        return self._parse_response(results, prefix=prefix)
    
    def get_market_snapshot(self, stock_codes: List[str], prefix: bool = False) -> Dict:
        """获取多只股票快照"""
        return self.get_realtime(stock_codes, prefix=prefix)
    
    def _safe_float(self, s: str) -> Optional[float]:
        try:
            return float(s)
        except (ValueError, TypeError):
            return None
    
    def _parse_response(self, rep_data: List[str], prefix: bool = False) -> Dict:
        """解析响应数据"""
        stocks_detail = "".join(rep_data)
        stock_details = stocks_detail.split(";")
        stock_dict = {}
        
        for stock_detail in stock_details:
            stock = stock_detail.split("~")
            if len(stock) <= 49:
                continue
            
            try:
                stock_code = (
                    self.grep_stock_code.search(stock[0]).group()
                    if prefix
                    else stock[2]
                )
                
                stock_dict[stock_code] = {
                    "name": stock[1],
                    "code": stock_code,
                    "now": float(stock[3]) if stock[3] else 0,
                    "close": float(stock[4]) if stock[4] else 0,  # 昨收
                    "open": float(stock[5]) if stock[5] else 0,
                    "volume": float(stock[6]) * 100 if stock[6] else 0,  # 成交量
                    "bid_volume": int(float(stock[7]) * 100) if stock[7] else 0,
                    "ask_volume": float(stock[8]) * 100 if stock[8] else 0,
                    "bid1": float(stock[9]) if stock[9] else 0,
                    "bid1_volume": int(float(stock[10]) * 100) if stock[10] else 0,
                    "bid2": float(stock[11]) if stock[11] else 0,
                    "bid2_volume": int(float(stock[12]) * 100) if stock[12] else 0,
                    "bid3": float(stock[13]) if stock[13] else 0,
                    "bid3_volume": int(float(stock[14]) * 100) if stock[14] else 0,
                    "bid4": float(stock[15]) if stock[15] else 0,
                    "bid4_volume": int(float(stock[16]) * 100) if stock[16] else 0,
                    "bid5": float(stock[17]) if stock[17] else 0,
                    "bid5_volume": int(float(stock[18]) * 100) if stock[18] else 0,
                    "ask1": float(stock[19]) if stock[19] else 0,
                    "ask1_volume": int(float(stock[20]) * 100) if stock[20] else 0,
                    "ask2": float(stock[21]) if stock[21] else 0,
                    "ask2_volume": int(float(stock[22]) * 100) if stock[22] else 0,
                    "ask3": float(stock[23]) if stock[23] else 0,
                    "ask3_volume": int(float(stock[24]) * 100) if stock[24] else 0,
                    "ask4": float(stock[25]) if stock[25] else 0,
                    "ask4_volume": int(float(stock[26]) * 100) if stock[26] else 0,
                    "ask5": float(stock[27]) if stock[27] else 0,
                    "ask5_volume": int(float(stock[28]) * 100) if stock[28] else 0,
                    "high": float(stock[33]) if stock[33] else 0,
                    "low": float(stock[34]) if stock[34] else 0,
                    "turnover": self._safe_float(stock[38]),  # 换手率
                    "pe": self._safe_float(stock[39]),
                    "pb": float(stock[46]) if len(stock) > 46 and stock[46] else None,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "time": datetime.now().strftime("%H:%M:%S"),
                }
            except (ValueError, IndexError, AttributeError) as e:
                print(f"⚠️ 腾讯数据解析失败: {e}")
                continue
        
        return stock_dict


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
        if self.source == 'sina':
            self._quotation = SinaQuotation()
        elif self.source == 'tencent':
            self._quotation = TencentQuotation()
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
                    print(f"✅ 加载股票代码列表: {len(self._stock_codes)} 只")
            else:
                print(f"⚠️ 股票代码文件不存在: {STOCK_CODE_PATH}")
        except Exception as e:
            print(f"⚠️ 加载股票代码列表失败: {e}")
    
    def get_realtime(self, codes: Union[str, List[str]], prefix: bool = False) -> Dict:
        """
        获取实时行情
        
        Args:
            codes: 股票代码或代码列表 (如 '600519' 或 ['600519', '000001'])
            prefix: 是否在返回结果中带有市场前缀 (sh/sz/bj)
        
        Returns:
            {代码: {name, now, open, close, high, low, volume, ...}}
        """
        return self._quotation.get_realtime(codes, prefix=prefix)
    
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
            print("⚠️ 股票代码列表为空")
            return {}
        
        codes = self._stock_codes[:limit] if limit > 0 else self._stock_codes
        
        # 获取行情
        result = self._quotation.get_market_snapshot(codes, prefix=prefix)
        
        # 更新缓存
        self._cache[cache_key] = result
        self._cache_time = current_time
        
        return result
    
    def get_stock_codes(self) -> List[str]:
        """获取全市场股票代码列表"""
        return self._stock_codes.copy()
    
    def get_intraday(self, stock_code: str) -> Dict:
        """
        获取股票当日分时走势数据
        
        使用新浪分时数据接口获取当日分钟级行情
        非交易时段会返回最近交易日的分时数据
        
        Args:
            stock_code: 6位股票代码，如 '600519'
        
        Returns:
            {
                'code': '600519',
                'name': '贵州茅台',
                'now': 1825.00,
                'change_pct': 0.85,
                'high': 1830.00,
                'low': 1815.00, 
                'open': 1820.00,
                'close': 1815.00,
                'volume': 12345678,
                'date': '2025-12-08',  # 数据日期
                'data': [
                    {'time': '09:30', 'price': 1820.00, 'avg': 1820.00, 'volume': 1234},
                    ...
                ]
            }
        """
        # 获取当日基础行情
        quote_data = self.get_realtime(stock_code)
        quote = quote_data.get(stock_code, {})
        
        if not quote:
            return {'error': f'无法获取股票 {stock_code} 的行情数据'}
        
        # 新浪分时数据接口
        prefix = get_stock_type(stock_code)
        sina_code = f"{prefix}{stock_code}"
        
        try:
            # 获取分时数据 - 增加datalen到480以获取更多历史数据
            url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sina_code}&scale=1&ma=no&datalen=480"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "http://finance.sina.com.cn/"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"⚠️ 分时数据请求失败: HTTP {response.status_code}")
                return self._build_intraday_response(stock_code, quote, [], None)
            
            # 解析JSON数据
            try:
                intraday_data = response.json()
            except:
                # 如果不是JSON，尝试解析为eval格式
                import ast
                text = response.text.strip()
                if text.startswith('['):
                    intraday_data = ast.literal_eval(text)
                else:
                    intraday_data = []
            
            if not isinstance(intraday_data, list) or len(intraday_data) == 0:
                return self._build_intraday_response(stock_code, quote, [], None)
            
            # 按日期分组数据，只取最近一个交易日的数据
            date_groups = {}
            for item in intraday_data:
                try:
                    day_str = item.get('day', '')
                    if ' ' in day_str:
                        date_part = day_str.split(' ')[0]
                        if date_part not in date_groups:
                            date_groups[date_part] = []
                        date_groups[date_part].append(item)
                except:
                    continue
            
            # 获取最近交易日的数据
            if not date_groups:
                return self._build_intraday_response(stock_code, quote, [], None)
            
            latest_date = max(date_groups.keys())
            latest_data = date_groups[latest_date]
            
            # 格式化分时数据
            formatted_data = []
            total_volume = 0
            total_amount = 0
            
            for item in latest_data:
                try:
                    # 提取时间（只取 HH:MM）
                    time_str = item.get('day', '')
                    if ' ' in time_str:
                        time_str = time_str.split(' ')[1][:5]
                    
                    price = float(item.get('close', 0))
                    volume = int(float(item.get('volume', 0)))
                    
                    total_volume += volume
                    total_amount += price * volume
                    
                    # 计算均价
                    avg_price = total_amount / total_volume if total_volume > 0 else price
                    
                    formatted_data.append({
                        'time': time_str,
                        'price': price,
                        'avg': round(avg_price, 2),
                        'volume': volume,
                        'open': float(item.get('open', price)),
                        'high': float(item.get('high', price)),
                        'low': float(item.get('low', price))
                    })
                except (ValueError, KeyError) as e:
                    continue
            
            return self._build_intraday_response(stock_code, quote, formatted_data, latest_date)
            
        except Exception as e:
            print(f"⚠️ 获取分时数据失败: {e}")
            return self._build_intraday_response(stock_code, quote, [], None)
    
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


def get_realtime_service(source: str = 'sina') -> RealtimeQuotationService:
    """获取实时行情服务单例"""
    global _realtime_service
    if _realtime_service is None or _realtime_service.source != source:
        _realtime_service = RealtimeQuotationService(source=source)
    return _realtime_service
