"""
数据源服务模块
使用 data_sources 模块获取数据，减少冗余实现
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import yfinance as yf
import akshare as ak


from utils.logger import get_logger

# 使用统一的数据源模块
from services.data_sources import SinaDataSource, YahooDataSource, TencentDataSource

logger = get_logger(__name__)


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
        
        # 使用 data_sources 模块
        self._sina = SinaDataSource()
        self._yahoo = YahooDataSource()
        self._tencent = TencentDataSource()
        
        # Tushare 配置 (可选)
        self.tushare_token = tushare_token
        self.tushare_pro = None
        if tushare_token:
            try:
                import tushare as ts
                ts.set_token(tushare_token)
                self.tushare_pro = ts.pro_api()
                logger.info("Tushare initialized successfully")
            except Exception as e:
                logger.warning(f"Tushare initialization failed: {e}")
    
    def get_us_index_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取美股指数实时行情
        优先级: Sina (首选) -> Tencent (备选) -> Yahoo (兜底)
        
        symbol: 例如 '^DJI' (道琼斯), '^IXIC' (纳斯达克), '^GSPC' (标普500)
        """
        # 1. Sina (快速)
        data = self._sina.get_us_index(symbol)
        if data: return data
        
        # 2. Tencent (备选)
        data = self._tencent.get_us_index(symbol)
        if data: return data
        
        # 3. Yahoo (兜底)
        data = self._yahoo.get_us_index(symbol)
        if data: return data
        
        return None
    
    def get_hk_index(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取港股指数实时行情
        优先级: Sina (首选) -> Tencent (备选) -> Yahoo (兜底)
        
        symbol: 例如 '^HSI', 'HSTECH.HK'
        """
        # 1. Sina (快速)
        data = self._sina.get_hk_index(symbol)
        if data: return data
        
        # 2. Tencent (备选)
        data = self._tencent.get_hk_index(symbol)
        if data: return data
        
        # 3. Yahoo (兜底)
        # Yahoo code adjustment for HSTECH if needed, but Yahoo usually handles standard tickers well for HK
        data = self._yahoo.get_us_index(symbol) # Yahoo handles HK under same method
        if data: return data
        
        return None
    
    # 指数获取失败缓存 {code: timestamp}
    _failure_cache = {}
    _failure_cache_ttl = 60  # 60秒不再重试

    def get_cn_index(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取A股指数数据
        优先级：实时接口(新浪/腾讯/东财) > Tushare > AkShare历史
        """
        # 0. 检查失败缓存
        current_time = datetime.now().timestamp()
        if code in self._failure_cache:
            last_fail_time = self._failure_cache[code]
            if current_time - last_fail_time < self._failure_cache_ttl:
                # print(f"⚠️ [Skip] Skipping {code} due to recent failure")
                return None
            else:
                del self._failure_cache[code]

        try:
            # 方法1: 使用 RealtimeQuotationService (新浪/腾讯/东方财富)
            from services.realtime_quotation_service import get_realtime_service
            
            # 尝试新浪 (通常最快)
            service = get_realtime_service(source='sina')
            data_dict = service.get_realtime(code)
            
            # 如果新浪失败，尝试东方财富 (备选)
            if not data_dict or code not in data_dict:
                # 尝试通过东方财富获取
                # 注: 东方财富接口在 RealtimeQuotationService 中有封装，但可能需要适配指数代码
                # 这里暂时通过 fallback 机制，或者直接调用 get_realtime_with_fallback
                data_dict = service.get_realtime_with_fallback(code)

            if data_dict and code in data_dict:
                row = data_dict[code]
                price = float(row.get('now', 0))
                
                # 如果价格为0，可能是接口返回异常，视为失败
                if price <= 0:
                    raise ValueError(f"Price is 0 for {code}")
                    
                change = float(row.get('change', 0))
                # 计算涨跌幅: 优先用 change_pct, 否则通过 (now-close)/close 计算
                if 'change_pct' in row and row['change_pct'] != 0:
                     change_pct = float(row['change_pct'])
                else:
                    prev_close = float(row.get('close', price))
                    if prev_close > 0:
                        change = price - prev_close
                        change_pct = (change / prev_close) * 100
                    else:
                        change_pct = 0.0

                # print(f"✅ [Realtime] {row['name']}: price={price}, change_pct={change_pct:.2f}%")
                return {
                    "price": price,
                    "change": change,
                    "change_pct": change_pct,
                    "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

        except Exception as e:
            # 记录这次尝试的一个小错误，但不阻断后续fallback
            # print(f"⚠️ [Realtime] Failed for {code}: {e}")
            # 记录这次尝试的错误
            logger.error(f"⚠️ [Realtime] Failed for {code}: {e}")

        # ... 如果实时接口都失败了，回退到 Tushare/AkShare ...

        # 方法2: Tushare (备选 - 数据质量高但有额度限制)
        if self.tushare_pro:
            try:
                # print(f"📊 [Tushare] Fetching data for {code}...")
                
                # 转换代码格式: sh000001 -> 000001.SH
                ts_code = code.replace('sh', '').replace('sz', '') + '.SH'
                
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
                
                df = self.tushare_pro.index_daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df is not None and len(df) >= 1:
                    df = df.sort_values('trade_date', ascending=False)
                    latest = df.iloc[0]
                    price = float(latest['close'])
                    change_pct = float(latest['pct_chg'])
                    
                    logger.debug(f"[Tushare] {ts_code}: price={price}, change_pct={change_pct}%")
                    return {
                        "price": price,
                        "change": float(latest.get('change', 0)),
                        "change_pct": change_pct,
                        "time": datetime.now().strftime('%Y-%m-%d') + " (Tushare)"
                    }
            except Exception as e:
                pass # print(f"⚠️ [Tushare] Failed for {code}: {e}")
        
        # 方法3: AkShare历史数据 (最后防线)
        try:
            # print(f"📅 [AkShare] Fallback for {code}...")
            df = ak.stock_zh_index_daily(symbol=code)
            
            if df is not None and len(df) >= 2:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                latest = df.iloc[-1]
                prev = df.iloc[-2]
                
                price = latest['close']
                change = price - prev['close']
                change_pct = (change / prev['close']) * 100
                
                return {
                    "price": float(price),
                    "change": float(change),
                    "change_pct": float(change_pct),
                    "time": latest['date'].strftime('%Y-%m-%d') + " (Hist)"
                }
        except Exception:
            pass

        # 如果所有方法都失败了，记录到失败缓存
        self._failure_cache[code] = datetime.now().timestamp()
        logger.error(f"All methods failed for {code}, caching failure for 60s")
        return None
    

    def get_stock_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取个股实时行情
        code: 6位股票代码，如 '600519'
        """
        try:
            logger.debug(f"Fetching quote for {code}...")
            
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
                except Exception as e:
                    logger.warning(f"获取股票名称失败 {code}: {e}")
                    name = code
                
                return {
                    "code": code,
                    "name": name,
                    "price": price,
                    "change_pct": change_pct,
                    "time": latest['日期']
                }
                
        except Exception as e:
            logger.error(f"Error fetching stock quote for {code}: {e}")
            
        return None
