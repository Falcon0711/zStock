"""
A股分析模块 - 基于您的原始代码重构
Stock Analyzer for A-Shares (Refactored from original code)
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import functools
from core.base_analyzer import BaseAnalyzer
from utils.logger import get_logger
import time
from typing import Dict, Tuple

# ===== 性能优化：全局缓存机制 =====
_stock_data_cache: Dict[str, Tuple[pd.DataFrame, float]] = {}
CACHE_TTL = 300  # 缓存时间（秒）- 5分钟
MAX_CACHE_SIZE = 100  # 最大缓存数量


def clear_expired_cache():
    """清理过期的缓存条目"""
    current_time = time.time()
    expired_keys = [
        key for key, (_, cached_time) in _stock_data_cache.items()
        if current_time - cached_time > CACHE_TTL
    ]
    for key in expired_keys:
        del _stock_data_cache[key]
        print(f"🗑️ 清理过期缓存: {key}")


def get_stock_data_cached(stock_code, days=90, start_date=None):
    """
    获取股票数据（带缓存优化）
    性能优化：
    1. 使用全局字典缓存，TTL=5分钟
    2. 减少默认数据量从300天到90天
    3. 自动清理过期缓存
    """
    import requests
    
    # 生成缓存键
    cache_key = f"{stock_code}_{days}_{start_date}"
    current_time = time.time()
    
    # ===== 缓存检查 =====
    if cache_key in _stock_data_cache:
        data, cached_time = _stock_data_cache[cache_key]
        if current_time - cached_time < CACHE_TTL:
            print(f"✅ 缓存命中: {stock_code} (缓存时间: {int(current_time - cached_time)}秒前)")
            return data.copy()  # 返回副本避免修改原缓存
        else:
            print(f"⏰ 缓存过期: {stock_code}")
    
    # ===== 缓存未命中，从API获取 =====
    print(f"📡 从API获取数据: {stock_code} (需要{days}天)")
    
    max_retries = 3  # 减少重试次数（从5到3）
    base_retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            if start_date is None:
                # 只获取需要的天数，减少数据量
                start_date = (datetime.now() - timedelta(days=days + 10)).strftime('%Y%m%d')
            
            # 重试延迟
            if attempt > 0:
                delay = base_retry_delay * (2 ** (attempt - 1))
                print(f"⏳ 等待 {delay} 秒后重试...")
                time.sleep(delay)
            
            # 调用akshare获取数据 - 先尝试东方财富，失败后用腾讯
            data = None
            try:
                # 先等待一小段时间，避免请求过于频繁
                if attempt == 0:
                    time.sleep(0.5)
                
                # 方案1: 东方财富数据
                data = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start_date,
                    adjust="qfq"  # 前复权
                )
            except Exception as em_error:
                print(f"⚠️ 东方财富API失败，尝试腾讯数据源...")
                try:
                    # 方案2: 腾讯数据源
                    # 需要转换股票代码格式: 000001 -> sz000001, 600519 -> sh600519
                    if stock_code.startswith('6'):
                        tencent_code = f"sh{stock_code}"
                    else:
                        tencent_code = f"sz{stock_code}"
                    
                    end_date = datetime.now().strftime('%Y%m%d')
                    data = ak.stock_zh_a_daily(
                        symbol=tencent_code,
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq"
                    )
                    print(f"✅ 腾讯数据源获取成功: {len(data)} 条")
                except Exception as tx_error:
                    if attempt < max_retries - 1:
                        print(f"⚠️ 所有数据源失败，重试中...")
                        continue
                    else:
                        raise Exception(
                            f"网络连接失败，无法获取股票 {stock_code} 的数据。\n"
                            f"东方财富: {str(em_error)}\n"
                            f"腾讯: {str(tx_error)}\n"
                            f"建议：检查网络连接或稍后重试"
                        )
            
            if data is not None and not data.empty:
                # 数据处理和清洗
                column_mapping = {
                    '日期': 'date',
                    '开盘': 'open',
                    '最高': 'high',
                    '最低': 'low',
                    '收盘': 'close',
                    '成交量': 'volume'
                }
                
                for old_col, new_col in column_mapping.items():
                    if old_col in data.columns:
                        data = data.rename(columns={old_col: new_col})
                
                # 验证必要列
                required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
                if not all(col in data.columns for col in required_cols):
                    raise ValueError(f"数据列不完整")
                
                # 转换日期格式
                data['date'] = pd.to_datetime(data['date'])
                data = data.sort_values('date').reset_index(drop=True)
                
                # 限制数据量
                if days and len(data) > days:
                    data = data.tail(days).reset_index(drop=True)
                
                # 验证数据量
                if len(data) < 60:
                    raise ValueError(f"获取的数据不足60天，只有{len(data)}天")
                
                # 确保数据类型
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_cols:
                    data[col] = pd.to_numeric(data[col], errors='coerce')
                
                data = data.dropna(subset=numeric_cols)
                
                if len(data) < 60:
                    raise ValueError(f"清理后数据不足60天")
                
                # ===== 更新缓存 =====
                # 检查缓存大小，如果太大则清理
                if len(_stock_data_cache) >= MAX_CACHE_SIZE:
                    clear_expired_cache()
                    # 如果清理后还是太多，删除最旧的
                    if len(_stock_data_cache) >= MAX_CACHE_SIZE:
                        oldest_key = min(_stock_data_cache.keys(), 
                                       key=lambda k: _stock_data_cache[k][1])
                        del _stock_data_cache[oldest_key]
                        print(f"🗑️ 缓存已满，删除最旧: {oldest_key}")
                
                _stock_data_cache[cache_key] = (data.copy(), current_time)
                print(f"💾 已缓存: {stock_code} (共{len(data)}天数据)")
                
                return data
            else:
                raise ValueError(f"获取的数据为空: {stock_code}")

        except Exception as e:
            error_msg = f"获取股票 {stock_code} 数据失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
            
            if attempt < max_retries - 1:
                print(f"⚠️ {error_msg}")
                continue
            else:
                print(f"❌ {error_msg}")
                raise
    
    raise Exception(f"获取股票 {stock_code} 数据失败，已达到最大重试次数")


class StockAnalyzer(BaseAnalyzer):
    """A股分析器 - 集成知行指标"""

    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self.market_type = "A股"

    def get_data(self, symbol: str, period: str = "10y") -> pd.DataFrame:
        """获取A股数据"""
        if period.endswith('y'):
            days = int(period.replace('y', '')) * 365
        elif period.endswith('d'):
            days = int(period.replace('d', ''))
        else:
            days = 3650 # Default 10 years
            
        return get_stock_data_cached(symbol, days)

    def calculate_zhixing_trend_line(self, close):
        """计算知行短期趋势线: EMA(EMA(C,10),10)"""
        try:
            ema1 = close.ewm(span=10, adjust=False).mean()
            ema2 = ema1.ewm(span=10, adjust=False).mean()
            return ema2
        except:
            return pd.Series()

    def calculate_zhixing_multi_line(self, close, m1=3, m2=6, m3=12, m4=24):
        """计算知行多空线: (MA(CLOSE,M1)+MA(CLOSE,M2)+MA(CLOSE,M3)+MA(CLOSE,M4))/4"""
        try:
            ma1 = close.rolling(window=m1).mean()
            ma2 = close.rolling(window=m2).mean()
            ma3 = close.rolling(window=m3).mean()
            ma4 = close.rolling(window=m4).mean()
            multi_line = (ma1 + ma2 + ma3 + ma4) / 4
            return multi_line
        except:
            return pd.Series()

    def get_hot_stocks(self):
        """获取热门股票列表（硬编码Top20，作为API失败的备选）"""
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

    def get_market_indices(self):
        """获取主要指数数据 (上证、深证、创业板)"""
        indices = [
            {"code": "sh000001", "name": "上证指数"},
            {"code": "sz399001", "name": "深证成指"},
            {"code": "sz399006", "name": "创业板指"}
        ]
        
        results = []
        for index in indices:
            try:
                # Fetch index data
                df = ak.stock_zh_index_daily(symbol=index["code"])
                
                # Process data (last 3 months)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                recent_df = df.tail(60) # Approx 3 months of trading days
                
                chart_data = []
                for _, row in recent_df.iterrows():
                    chart_data.append({
                        "time": row['date'].strftime('%Y-%m-%d'),
                        "value": float(row['close'])
                    })
                
                # Calculate change
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
                # 不再使用模拟数据，记录错误并跳过该指数
                error_msg = f"获取指数 {index['name']} ({index['code']}) 数据失败: {e}"
                print(error_msg)
                self.logger.warning(error_msg)
                # 跳过该指数，继续处理其他指数
                continue
                
        return results

    def calculate_ma60_and_ema13(self, close):
        """计算MA60和EMA13"""
        try:
            ma60 = close.rolling(window=60).mean()
            ema13 = close.ewm(span=13, adjust=False).mean()
            return ma60, ema13
        except:
            return pd.Series(), pd.Series()

    def calculate_oscillator(self, close, high, low, volume, period=14):
        """计算振荡器指标（范围-50到150）"""
        try:
            # 基于价格动量的振荡器，类似RSI但调整范围
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            # 避免除零
            rs = gain / (loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            
            # 将RSI (0-100) 映射到振荡器范围 (-50到150)
            # 使用线性映射: oscillator = (rsi / 100) * 200 - 50
            oscillator = (rsi / 100) * 200 - 50
            
            # 使用成交量作为动量增强因子
            volume_ma = volume.rolling(window=period).mean()
            volume_ratio = volume / (volume_ma + 1e-10)
            # 成交量放大时增强振荡器幅度
            volume_factor = 0.8 + 0.2 * volume_ratio.clip(0.5, 2.0)
            oscillator = oscillator * volume_factor
            
            # 确保范围在-50到150之间
            return oscillator.clip(-50, 150)
        except:
            return pd.Series()

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        if data is None or len(data) < 60:
            return None

        # 计算所有技术指标
        k, d, j = self.calculate_kdj(data['high'], data['low'], data['close'])
        bbi = self.calculate_bbi(data['close'])
        macd, signal_line, hist = self.calculate_macd(data['close'])

        # 知行指标
        zhixing_trend = self.calculate_zhixing_trend_line(data['close'])
        zhixing_multi = self.calculate_zhixing_multi_line(data['close'])
        ma60, ema13 = self.calculate_ma60_and_ema13(data['close'])
        
        # 计算振荡器指标
        oscillator = self.calculate_oscillator(
            data['close'], 
            data['high'], 
            data['low'], 
            data['volume']
        )
        
        # 计算基础均线
        ma5 = data['close'].rolling(window=5).mean()
        ma10 = data['close'].rolling(window=10).mean()
        ma20 = data['close'].rolling(window=20).mean()
        ma30 = data['close'].rolling(window=30).mean()

        # 添加指标到数据
        data = data.copy()
        data['kdj_k'] = k
        data['kdj_d'] = d
        data['kdj_j'] = j
        data['bbi'] = bbi
        data['macd'] = macd
        data['macd_signal'] = signal_line
        data['macd_hist'] = hist
        data['zhixing_trend'] = zhixing_trend
        data['zhixing_multi'] = zhixing_multi
        data['ma60'] = ma60
        data['ema13'] = ema13
        data['ma5'] = ma5
        data['ma10'] = ma10
        data['ma20'] = ma20
        data['ma30'] = ma30
        data['oscillator'] = oscillator

        return data

    def generate_signals(self, data: pd.DataFrame) -> dict:
        """生成交易信号"""
        if data is None or len(data) == 0:
            return {}

        latest = data.iloc[-1]
        signals = {}

        # KDJ信号
        if not pd.isna(latest['kdj_k']) and not pd.isna(latest['kdj_d']):
            signals['kdj_buy'] = latest['kdj_k'] < 20 and latest['kdj_d'] < 20 and latest['kdj_k'] > latest['kdj_d']
            signals['kdj_sell'] = latest['kdj_k'] > 80 and latest['kdj_d'] > 80 and latest['kdj_k'] < latest['kdj_d']

        # BBI/知行多空线信号
        if not pd.isna(latest['bbi']):
            signals['bbi_buy'] = latest['close'] > latest['bbi'] * 1.02
            signals['bbi_sell'] = latest['close'] < latest['bbi'] * 0.98

        # MACD信号
        if not pd.isna(latest['macd']) and not pd.isna(latest['macd_signal']):
            signals['macd_buy'] = latest['macd'] > latest['macd_signal'] and latest['macd_hist'] > 0
            signals['macd_sell'] = latest['macd'] < latest['macd_signal'] and latest['macd_hist'] < 0

        # 知行趋势线信号
        if not pd.isna(latest['zhixing_trend']):
            signals['zhixing_buy'] = latest['close'] > latest['zhixing_trend']
            signals['zhixing_sell'] = latest['close'] < latest['zhixing_trend']

        return signals

    def analyze_stock(self, stock_code: str):
        """完整的股票分析"""
        try:
            # 获取数据
            data = self.get_data(stock_code)
            if data is None or len(data) == 0:
                error_msg = f"无法获取股票 {stock_code} 的数据。数据为空。"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            # 计算指标
            data_with_indicators = self.calculate_indicators(data)
            if data_with_indicators is None:
                error_msg = f"无法计算股票 {stock_code} 的技术指标。数据可能不足60天。"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            # 生成信号
            signals = self.generate_signals(data_with_indicators)

            # 计算综合评分
            score = self.calculate_score(signals)

            # 获取最新数据
            latest = data_with_indicators.iloc[-1]

            return {
                'data': data_with_indicators,
                'signals': signals,
                'score': score,
                'latest_price': latest['close'],
                'kdj_k': latest.get('kdj_k', 0),
                'kdj_d': latest.get('kdj_d', 0),
                'bbi_value': latest.get('bbi', 0),
                'macd_value': latest.get('macd', 0),
                'zhixing_trend_value': latest.get('zhixing_trend', 0),
                'zhixing_multi_value': latest.get('zhixing_multi', 0)
            }
        except ValueError as e:
            # 重新抛出ValueError，让API层处理
            raise
        except Exception as e:
            error_msg = f"分析股票 {stock_code} 时发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise Exception(error_msg) from e

    def get_csi300_stocks(self):
        """获取沪深300成分股"""
        try:
            stocks = ak.index_stock_cons_csindex(symbol="000300")
            # 统一列名
            stocks = stocks.rename(columns={
                '成分券代码': 'code',
                '成分券名称': 'name',
                '交易所': 'exchange'
            })
            return stocks[['code', 'name']].to_dict('records')
        except Exception as e:
            self.logger.error(f"获取沪深300成分股失败: {e}")
            return []

    def filter_stocks_by_kdj(self, stock_list, criteria):
        """根据KDJ指标筛选股票"""
        import time
        results = []
        total = len(stock_list)
        
        for i, stock in enumerate(stock_list):
            try:

                code = stock.get('code')
                
                # 添加延时以避免请求过快
                time.sleep(0.1)
                
                # 获取数据（使用较短周期以加快速度，例如150天）
                # 增加重试机制
                retry_count = 3
                data = None
                for attempt in range(retry_count):
                    try:
                        data = self.get_data(code, period="150d")
                        if data is not None:
                            break
                        time.sleep(0.5) # 重试前等待
                    except Exception:
                        if attempt < retry_count - 1:
                            time.sleep(1)
                            continue
                
                if data is None or len(data) < 9: # KDJ至少需要9天数据
                    continue

                # 计算KDJ
                k, d, j = self.calculate_kdj(data['high'], data['low'], data['close'])
                
                if len(k) == 0:
                    continue
                    
                curr_k = k.iloc[-1]
                curr_d = d.iloc[-1]
                curr_j = j.iloc[-1]
                curr_close = data['close'].iloc[-1]
                
                # 检查是否满足筛选条件
                match = True
                
                # K值范围
                if 'k_min' in criteria and curr_k < criteria['k_min']: match = False
                if 'k_max' in criteria and curr_k > criteria['k_max']: match = False
                
                # D值范围
                if 'd_min' in criteria and curr_d < criteria['d_min']: match = False
                if 'd_max' in criteria and curr_d > criteria['d_max']: match = False
                
                # J值范围
                if 'j_min' in criteria and curr_j < criteria['j_min']: match = False
                if 'j_max' in criteria and curr_j > criteria['j_max']: match = False
                
                # 金叉/死叉
                if criteria.get('signal'):
                    prev_k = k.iloc[-2]
                    prev_d = d.iloc[-2]
                    
                    if criteria['signal'] == 'buy': # 金叉: K上穿D
                        if not (prev_k < prev_d and curr_k > curr_d): match = False
                    elif criteria['signal'] == 'sell': # 死叉: K下穿D
                        if not (prev_k > prev_d and curr_k < curr_d): match = False

                if match:
                    results.append({
                        'code': code,
                        'name': stock.get('name'),
                        'close': curr_close,
                        'k': curr_k,
                        'd': curr_d,
                        'j': curr_j
                    })
                    
            except Exception as e:
                self.logger.error(f"分析股票 {stock.get('code')} 失败: {e}")
                continue
                
            
        return results

    def batch_analyze(self, stock_list):
        """批量分析股票列表"""
        results = []

        for stock in stock_list:
            analysis = self.analyze_stock(stock.get('code', stock.get('symbol', '')))
            if analysis:
                results.append({
                    '股票代码': stock.get('code', stock.get('symbol', '')),
                    '股票名称': stock.get('name', ''),
                    '最新价格': f"{analysis['latest_price']:.2f}",
                    '综合评分': analysis['score'],
                    'KDJ信号': "买入" if analysis['signals'].get('kdj_buy') else "卖出" if analysis['signals'].get(
                        'kdj_sell') else "观望",
                    'BBI信号': "买入" if analysis['signals'].get('bbi_buy') else "卖出" if analysis['signals'].get(
                        'bbi_sell') else "观望",
                    'MACD信号': "买入" if analysis['signals'].get('macd_buy') else "卖出" if analysis['signals'].get(
                        'macd_sell') else "观望",
                    '知行趋势': "买入" if analysis['signals'].get('zhixing_buy') else "卖出" if analysis['signals'].get(
                        'zhixing_sell') else "观望"
                })

        return results
