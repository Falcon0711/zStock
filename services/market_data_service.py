"""
数据源服务模块
支持多个数据源：Tushare, AkShare, Alpha Vantage, Yahoo Finance
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import requests
import yfinance as yf
import tushare as ts


class MarketDataService:
    """市场数据服务 - 整合多个数据源"""
    
    # 类级别缓存，用于存储A股实时指数数据
    _cn_index_cache = {
        "data": None,
        "time": 0
    }
    _cn_index_cache_ttl = 10  # 10秒缓存
    
    def __init__(self, alpha_vantage_key: Optional[str] = None, tushare_token: Optional[str] = None):
        self.alpha_vantage_key = alpha_vantage_key
        self.base_url = "https://www.alphavantage.co/query"
        
        # 初始化Tushare
        self.tushare_token = tushare_token
        self.tushare_pro = None
        if tushare_token:
            try:
                ts.set_token(tushare_token)
                self.tushare_pro = ts.pro_api()
                print("✅ Tushare initialized successfully")
            except Exception as e:
                print(f"⚠️ Tushare initialization failed: {e}")
    
    def get_us_index_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取美股指数实时行情
        优先使用 Yahoo Finance (yfinance)，备用 Alpha Vantage
        symbol: 例如 '^GSPC' (标普500), '^NDX' (纳斯达克100), 'QQQ', 'SPY'
        """
        # 1. 尝试使用 Yahoo Finance (支持指数代码)
        try:
            print(f"Fetching US index {symbol} from Yahoo Finance...")
            ticker = yf.Ticker(symbol)
            
            # 获取历史数据
            hist = ticker.history(period="5d")
            
            if hist is not None and len(hist) >= 2:
                latest = hist.iloc[-1]
                previous = hist.iloc[-2]
                
                price = float(latest['Close'])
                change = float(latest['Close'] - previous['Close'])
                change_pct = (change / previous['Close'] * 100)
                
                print(f"✅ [Yahoo] Successfully got {symbol}: price={price}, change_pct={change_pct}%")
                
                return {
                    "price": price,
                    "change": change,
                    "change_pct": change_pct,
                    "time": datetime.now().strftime('%Y-%m-%d')
                }
            elif hist is not None and len(hist) == 1:
                # 只有一天数据
                latest = hist.iloc[-1]
                price = float(latest['Close'])
                
                # 尝试从info获取前收盘价
                info = ticker.info
                if info and 'regularMarketPreviousClose' in info:
                    prev_close = float(info.get('regularMarketPreviousClose', price))
                    if prev_close != price:
                        change = price - prev_close
                        change_pct = (change / prev_close * 100)
                        return {
                            "price": price,
                            "change": change,
                            "change_pct": change_pct,
                            "time": datetime.now().strftime('%Y-%m-%d')
                        }
                
                return {
                    "price": price,
                    "change": 0.0,
                    "change_pct": 0.0,
                    "time": datetime.now().strftime('%Y-%m-%d')
                }
        except Exception as e:
            print(f"⚠️ [Yahoo] Failed for {symbol}: {e}")

        # 2. 备用: Alpha Vantage (主要支持ETF)
        if not self.alpha_vantage_key or self.alpha_vantage_key == "YOUR_API_KEY_HERE":
            print(f"Alpha Vantage API key not configured, skipping fallback for {symbol}")
            return None
        
        try:
            print(f"Fetching US index {symbol} from Alpha Vantage (Fallback)...")
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.alpha_vantage_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()
            
            if "Global Quote" in data and data["Global Quote"]:
                quote = data["Global Quote"]
                if not quote.get("05. price"):
                    return None
                
                price = float(quote.get("05. price", 0))
                change = float(quote.get("09. change", 0))
                change_pct = float(quote.get("10. change percent", "0").rstrip('%'))
                
                print(f"✅ [Alpha Vantage] Successfully got {symbol}: price={price}")
                
                return {
                    "price": price,
                    "change": change,
                    "change_pct": change_pct,
                    "time": datetime.now().strftime('%Y-%m-%d')
                }
        except Exception as e:
            print(f"Alpha Vantage API error for {symbol}: {e}")
            return None
            
        return None
    
    
    def get_cn_index(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取A股指数数据
        优先级：Tushare实时 > AkShare实时 > AkShare历史
        """
        # 方法1: Tushare (优先 - 数据质量最高)
        if self.tushare_pro:
            try:
                print(f"📊 [Tushare] Fetching data for {code}...")
                
                # 转换代码格式: sh000001 -> 000001.SH
                ts_code = code.replace('sh', '').replace('sz', '') + '.SH'
                
                # 获取最近5天的数据（确保有数据）
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
                
                df = self.tushare_pro.index_daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df is not None and len(df) >= 2:
                    # Tushare数据是倒序的，所以第一行是最新的
                    df = df.sort_values('trade_date', ascending=False)
                    latest = df.iloc[0]
                    previous = df.iloc[1]
                    
                    price = float(latest['close'])
                    change = price - float(previous['close'])
                    change_pct = float(latest['pct_chg'])  # Tushare直接提供涨跌幅
                    
                    print(f"✅ [Tushare] {ts_code}: price={price}, change_pct={change_pct}%")
                    
                    return {
                        "price": price,
                        "change": change,
                        "change_pct": change_pct,
                        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " (Tushare)"
                    }
                elif df is not None and len(df) == 1:
                    # 只有一条数据，无法计算涨跌
                    latest = df.iloc[0]
                    price = float(latest['close'])
                    change_pct = float(latest['pct_chg'])
                    
                    print(f"✅ [Tushare] {ts_code}: price={price} (single day)")
                    
                    return {
                        "price": price,
                        "change": 0.0,
                        "change_pct": change_pct,
                        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " (Tushare)"
                    }
            except Exception as e:
                print(f"⚠️ [Tushare] Failed for {code}: {e}")
        

        
        
        # 方法2: AkShare实时接口 (备选1 - 增加缓存机制)
        try:
            current_time = datetime.now().timestamp()
            df = None
            
            # 检查缓存
            if (self._cn_index_cache["data"] is not None and 
                (current_time - self._cn_index_cache["time"]) < self._cn_index_cache_ttl):
                df = self._cn_index_cache["data"]
                # print(f"🚀 [Cache] Using cached AkShare data for {code}")
            else:
                print(f"📊 [AkShare RT] Fetching fresh real-time data...")
                df = ak.stock_zh_index_spot_em()
                self._cn_index_cache["data"] = df
                self._cn_index_cache["time"] = current_time
            
            if df is not None:
                code_number = code.replace('sh', '').replace('sz', '')
                result = df[df['代码'] == code_number]
                
                if len(result) > 0:
                    row = result.iloc[0]
                    price = float(row.get('最新价', 0))
                    change = float(row.get('涨跌额', 0))
                    change_pct = float(row.get('涨跌幅', 0))
                    
                    print(f"✅ [AkShare RT] {row['名称']}: price={price}, change_pct={change_pct}%")
                    
                    return {
                        "price": price,
                        "change": change,
                        "change_pct": change_pct,
                        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
        except Exception as e:
            print(f"⚠️ [AkShare RT] Failed for {code}: {str(e)[:100]}")

        # 方法3: AkShare历史数据 (最后备选)
        try:
            print(f"📅 [AkShare Hist] Fallback to historical data for {code}...")
            df = ak.stock_zh_index_daily(symbol=code)
            
            if df is None or len(df) < 2:
                return None
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            latest = df.iloc[-1]
            previous = df.iloc[-2]
            
            change = float(latest['close'] - previous['close'])
            change_pct = float((change / previous['close']) * 100)
            
            print(f"✅ [AkShare Hist] price={latest['close']}, change_pct={change_pct}%")
            
            return {
                "price": float(latest['close']),
                "change": change,
                "change_pct": change_pct,
                "time": latest['date'].strftime('%Y-%m-%d') + " (历史)"
            }
        except Exception as e:
            print(f"❌ [AkShare Hist] Error for {code}: {e}")
            return None
    
    def get_hk_index(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取港股指数数据 (Yahoo Finance)
        symbol: 例如 '^HSI', 'HSTECH.HK'
        """
        try:
            print(f"Fetching HK index {symbol} from Yahoo Finance...")
            
            # 使用 yfinance 获取数据
            ticker = yf.Ticker(symbol)
            
            # 优先使用历史数据（更准确）
            hist = ticker.history(period="5d")
            
            if hist is not None and len(hist) >= 2:
                # 获取最新两个交易日的数据
                latest = hist.iloc[-1]
                previous = hist.iloc[-2]
                
                price = float(latest['Close'])
                change = float(latest['Close'] - previous['Close'])
                change_pct = (change / previous['Close'] * 100)
                
                print(f"✅ Successfully got {symbol} from history: price={price}, change={change}, change_pct={change_pct}")
                
                return {
                    "price": price,
                    "change": change,
                    "change_pct": change_pct,
                    "time": datetime.now().strftime('%Y-%m-%d')
                }
            elif hist is not None and len(hist) == 1:
                # 只有一天数据，尝试从info获取
                latest = hist.iloc[-1]
                price = float(latest['Close'])
                
                info = ticker.info
                if info and 'regularMarketPreviousClose' in info:
                    prev_close = float(info.get('regularMarketPreviousClose', price))
                    if prev_close != price:
                        change = price - prev_close
                        change_pct = (change / prev_close * 100)
                        
                        print(f"✅ Got {symbol} from info fallback: price={price}, change={change}")
                        
                        return {
                            "price": price,
                            "change": change,
                            "change_pct": change_pct,
                            "time": datetime.now().strftime('%Y-%m-%d')
                        }
                
                print(f"⚠️ Got {symbol} but only one day of data, no change info")
                
                return {
                    "price": price,
                    "change": 0.0,
                    "change_pct": 0.0,
                    "time": datetime.now().strftime('%Y-%m-%d')
                }
            else:
                print(f"❌ No data available for {symbol}")
                return None
                
        except Exception as e:
            print(f"❌ Yahoo Finance error for {symbol}: {e}")
            return None
        
        return None

    def get_stock_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取个股实时行情
        code: 6位股票代码，如 '600519'
        """
        try:
            print(f"Fetching quote for {code}...")
            
            # 使用 AkShare 获取历史数据（最稳定的方式）
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
            end_date = datetime.now().strftime('%Y%m%d')
            
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                price = float(latest['收盘'])
                change_pct = float(latest['涨跌幅'])
                
                # 尝试获取股票名称
                try:
                    info_df = ak.stock_individual_info_em(symbol=code)
                    name = code
                    if not info_df.empty:
                        # info_df 的结构是 item/value 格式
                        for idx, row in info_df.iterrows():
                            if row['item'] == '股票简称':
                                name = row['value']
                                break
                except:
                    name = code
                
                return {
                    "code": code,
                    "name": name,
                    "price": price,
                    "change_pct": change_pct,
                    "time": latest['日期']
                }
                
        except Exception as e:
            print(f"Error fetching stock quote for {code}: {e}")
            
        return None
