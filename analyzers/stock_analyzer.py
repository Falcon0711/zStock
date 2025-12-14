"""
A股分析器 - 重构版
Stock Analyzer for A-Shares (Refactored)

职责：
- 组合数据获取和指标计算
- 生成交易信号
- 计算综合评分
"""

import akshare as ak
from datetime import datetime
import pandas as pd
import numpy as np
import time
from datetime import datetime
from typing import Dict, Tuple, Optional

from core.base_analyzer import BaseAnalyzer
from utils.logger import get_logger
from analyzers.data_fetcher import get_stock_data
from analyzers.indicators import (
    calculate_kdj, calculate_macd, calculate_bbi,
    calculate_all_indicators
)

# ==================== 分析结果缓存 ====================
from collections import OrderedDict
from threading import Lock


class AnalysisCache:
    """线程安全的 LRU 缓存（配置化）"""
    
    def __init__(self, maxsize: int = None, ttl: int = None):
        # 从配置读取默认值
        try:
            from services.data_config import ANALYSIS_CACHE_SIZE, ANALYSIS_CACHE_TTL
            maxsize = maxsize or ANALYSIS_CACHE_SIZE
            ttl = ttl or ANALYSIS_CACHE_TTL
        except (ImportError, AttributeError):
            maxsize = maxsize or 50
            ttl = ttl or 300
        
        self._cache: OrderedDict = OrderedDict()
        self._lock = Lock()
        self._maxsize = maxsize
        self._ttl = ttl
    
    def get(self, key: str) -> Optional[dict]:
        """获取缓存，返回 None 表示未命中或已过期"""
        with self._lock:
            if key in self._cache:
                result, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    self._cache.move_to_end(key)  # LRU: 移到末尾
                    return result
                del self._cache[key]  # 过期删除
        return None
    
    def set(self, key: str, value: dict):
        """设置缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            self._cache[key] = (value, time.time())
            while len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)  # 删除最旧的


_analysis_cache = AnalysisCache()


class StockAnalyzer(BaseAnalyzer):
    """A股分析器 - 集成知行指标"""

    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self.market_type = "A股"

    def get_data(self, symbol: str, period: str = "10y") -> pd.DataFrame:
        """获取A股数据"""
        if period == 'all':
            # A股始于1990年12月19日 (上交所开业)
            # 动态计算天数，确保覆盖全部历史
            start = datetime(1990, 12, 19)
            days = (datetime.now() - start).days + 365  # 加一年buffer
        elif period.endswith('y'):
            days = int(period.replace('y', '')) * 365
        elif period.endswith('d'):
            days = int(period.replace('d', ''))
        else:
            days = 3650
            
        return get_stock_data(symbol, days)

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        return calculate_all_indicators(data)

    def generate_signals(self, data: pd.DataFrame) -> dict:
        """生成交易信号"""
        if data is None or len(data) == 0:
            return {}

        latest = data.iloc[-1]
        signals = {}

        # KDJ信号
        if not pd.isna(latest.get('kdj_k')) and not pd.isna(latest.get('kdj_d')):
            signals['kdj_buy'] = (latest['kdj_k'] < 20 and latest['kdj_d'] < 20 
                                  and latest['kdj_k'] > latest['kdj_d'])
            signals['kdj_sell'] = (latest['kdj_k'] > 80 and latest['kdj_d'] > 80 
                                   and latest['kdj_k'] < latest['kdj_d'])

        # BBI信号
        if not pd.isna(latest.get('bbi')):
            signals['bbi_buy'] = latest['close'] > latest['bbi'] * 1.02
            signals['bbi_sell'] = latest['close'] < latest['bbi'] * 0.98

        # MACD信号
        if not pd.isna(latest.get('macd')) and not pd.isna(latest.get('macd_signal')):
            signals['macd_buy'] = (latest['macd'] > latest['macd_signal'] 
                                   and latest['macd_hist'] > 0)
            signals['macd_sell'] = (latest['macd'] < latest['macd_signal'] 
                                    and latest['macd_hist'] < 0)

        # 知行趋势线信号
        if not pd.isna(latest.get('zhixing_trend')):
            signals['zhixing_buy'] = latest['close'] > latest['zhixing_trend']
            signals['zhixing_sell'] = latest['close'] < latest['zhixing_trend']

        return signals

    def calculate_score(self, signals: dict) -> int:
        """计算综合评分"""
        score = 50  # 基础分数
        
        # 信号权重配置
        weights = {
            'zhixing': 25,  # 趋势最重要
            'bbi': 22,      # 多空分界次之
            'macd': 20,     # 动量指标
            'kdj': 18       # 超买超卖辅助
        }
        
        for key, value in signals.items():
            if not value:  # 跳过False信号
                continue
                
            if 'buy' in key:
                if 'zhixing' in key: score += weights['zhixing']
                elif 'bbi' in key: score += weights['bbi']
                elif 'macd' in key: score += weights['macd']
                elif 'kdj' in key: score += weights['kdj']
            elif 'sell' in key:
                if 'zhixing' in key: score -= weights['zhixing']
                elif 'bbi' in key: score -= weights['bbi']
                elif 'macd' in key: score -= weights['macd']
                elif 'kdj' in key: score -= weights['kdj']
                
        return max(0, min(100, score))

    def analyze_stock(self, stock_code: str, use_cache: bool = True) -> dict:
        """
        完整的股票分析
        
        Args:
            stock_code: 股票代码
            use_cache: 是否使用缓存（默认True）
        """
        # 检查缓存
        if use_cache:
            cached = _analysis_cache.get(stock_code)
            if cached:
                self.logger.info(f"✅ 使用缓存的分析结果: {stock_code}")
                return cached
        
        try:
            # 获取数据 (默认获取全量)
            data = self.get_data(stock_code, period="all")
            if data is None or len(data) == 0:
                raise ValueError(f"无法获取股票 {stock_code} 的数据")

            # 计算指标
            data_with_indicators = self.calculate_indicators(data)
            if data_with_indicators is None:
                raise ValueError(f"无法计算股票 {stock_code} 的技术指标")

            # 生成信号和评分
            signals = self.generate_signals(data_with_indicators)
            score = self.calculate_score(signals)
            latest = data_with_indicators.iloc[-1]

            result = {
                'data': data_with_indicators,
                'signals': signals,
                'score': score,
                'latest_price': latest['close'],
                'kdj_k': latest.get('kdj_k', 0),
                'kdj_d': latest.get('kdj_d', 0),
                'kdj_j': latest.get('kdj_j', 0),
                'bbi_value': latest.get('bbi', 0),
                'macd_value': latest.get('macd', 0),
                'zhixing_trend_value': latest.get('zhixing_trend', 0),
                'zhixing_multi_value': latest.get('zhixing_multi', 0)
            }
            
            # 缓存结果
            _analysis_cache.set(stock_code, result)
            self.logger.info(f"✅ 分析完成并缓存: {stock_code}")
            
            return result
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"分析股票 {stock_code} 失败: {e}", exc_info=True)
            raise

    def get_hot_stocks(self) -> list:
        """获取热门股票列表"""
        return [
            {"code": "600519", "name": "贵州茅台", "market_cap": "21000亿"},
            {"code": "601398", "name": "工商银行", "market_cap": "19000亿"},
            {"code": "601288", "name": "农业银行", "market_cap": "16000亿"},
            {"code": "601857", "name": "中国石油", "market_cap": "15000亿"},
            {"code": "600941", "name": "中国移动", "market_cap": "14500亿"},
            {"code": "601939", "name": "建设银行", "market_cap": "14000亿"},
            {"code": "601988", "name": "中国银行", "market_cap": "13000亿"},
            {"code": "300750", "name": "宁德时代", "market_cap": "9000亿"},
            {"code": "600036", "name": "招商银行", "market_cap": "8500亿"},
            {"code": "601088", "name": "中国神华", "market_cap": "8000亿"},
            {"code": "600900", "name": "长江电力", "market_cap": "7500亿"},
            {"code": "300059", "name": "东方财富", "market_cap": "4000亿"},
            {"code": "002594", "name": "比亚迪", "market_cap": "7000亿"},
            {"code": "000858", "name": "五粮液", "market_cap": "6000亿"},
            {"code": "601318", "name": "中国平安", "market_cap": "8000亿"},
            {"code": "000333", "name": "美的集团", "market_cap": "4500亿"},
            {"code": "603288", "name": "海天味业", "market_cap": "3500亿"},
            {"code": "600276", "name": "恒瑞医药", "market_cap": "3000亿"},
            {"code": "600030", "name": "中信证券", "market_cap": "3500亿"},
            {"code": "000001", "name": "平安银行", "market_cap": "2000亿"}
        ]

    def get_market_indices(self) -> list:
        """获取主要指数数据"""
        indices = [
            {"code": "sh000001", "name": "上证指数"},
            {"code": "sz399001", "name": "深证成指"},
            {"code": "sz399006", "name": "创业板指"},
            {"code": "sh000688", "name": "科创50"}
        ]
        
        results = []
        for index in indices:
            try:
                df = ak.stock_zh_index_daily(symbol=index["code"])
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                recent_df = df.tail(60)
                
                chart_data = [
                    {"time": row['date'].strftime('%Y-%m-%d'), "value": float(row['close'])}
                    for _, row in recent_df.iterrows()
                ]
                
                latest = recent_df.iloc[-1]
                prev = recent_df.iloc[-2]
                change_pct = (latest['close'] - prev['close']) / prev['close'] * 100
                
                results.append({
                    "code": index["code"],
                    "name": index["name"],
                    "latest_price": float(latest['close']),
                    "change_pct": float(change_pct),
                    "data": chart_data
                })
            except Exception as e:
                self.logger.warning(f"获取指数 {index['name']} 失败: {e}")
                continue
                
        return results

    def get_csi300_stocks(self) -> list:
        """获取沪深300成分股"""
        try:
            stocks = ak.index_stock_cons_csindex(symbol="000300")
            stocks = stocks.rename(columns={
                '成分券代码': 'code',
                '成分券名称': 'name'
            })
            return stocks[['code', 'name']].to_dict('records')
        except Exception as e:
            self.logger.error(f"获取沪深300成分股失败: {e}")
            return []

    def filter_stocks_by_kdj(self, stock_list: list, criteria: dict) -> list:
        """根据KDJ指标筛选股票"""
        import time
        results = []
        
        for stock in stock_list:
            try:
                code = stock.get('code')
                time.sleep(0.1)
                
                data = self.get_data(code, period="150d")
                if data is None or len(data) < 9:
                    continue

                k, d, j = calculate_kdj(data['high'], data['low'], data['close'])
                if len(k) == 0:
                    continue
                    
                curr_k, curr_d, curr_j = k.iloc[-1], d.iloc[-1], j.iloc[-1]
                
                # 检查条件
                match = True
                if 'k_min' in criteria and curr_k < criteria['k_min']: match = False
                if 'k_max' in criteria and curr_k > criteria['k_max']: match = False
                if 'd_min' in criteria and curr_d < criteria['d_min']: match = False
                if 'd_max' in criteria and curr_d > criteria['d_max']: match = False
                
                if criteria.get('signal'):
                    prev_k, prev_d = k.iloc[-2], d.iloc[-2]
                    if criteria['signal'] == 'buy' and not (prev_k < prev_d and curr_k > curr_d):
                        match = False
                    elif criteria['signal'] == 'sell' and not (prev_k > prev_d and curr_k < curr_d):
                        match = False

                if match:
                    results.append({
                        'code': code,
                        'name': stock.get('name'),
                        'close': data['close'].iloc[-1],
                        'k': curr_k, 'd': curr_d, 'j': curr_j
                    })
                    
            except Exception as e:
                self.logger.error(f"筛选 {stock.get('code')} 失败: {e}")
                continue
            
        return results

    def batch_analyze(self, stock_list: list) -> list:
        """批量分析股票列表"""
        results = []
        for stock in stock_list:
            try:
                analysis = self.analyze_stock(stock.get('code', stock.get('symbol', '')))
                if analysis:
                    results.append({
                        '股票代码': stock.get('code', ''),
                        '股票名称': stock.get('name', ''),
                        '最新价格': f"{analysis['latest_price']:.2f}",
                        '综合评分': analysis['score'],
                        'KDJ信号': "买入" if analysis['signals'].get('kdj_buy') else 
                                  "卖出" if analysis['signals'].get('kdj_sell') else "观望",
                        'MACD信号': "买入" if analysis['signals'].get('macd_buy') else 
                                   "卖出" if analysis['signals'].get('macd_sell') else "观望",
                    })
            except Exception as e:
                self.logger.warning(f"批量分析 {stock.get('code', 'unknown')} 失败: {e}")
                continue
        return results
