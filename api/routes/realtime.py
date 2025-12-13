"""
实时行情和K线相关路由
包含: 实时行情、批量行情、K线融合、分时数据
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime

from api.validators import validate_stock_code
from utils.logger import get_logger
from services.realtime_quotation_service import get_realtime_service
from services.realtime_kline_service import get_realtime_kline_service

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["实时行情"])

# 初始化服务
realtime_service = get_realtime_service('sina')
realtime_kline_service = get_realtime_kline_service('sina')


@router.get("/realtime/{code}")
async def get_realtime_quote(code: str):
    """获取单只股票实时行情"""
    try:
        if not code or len(code) != 6 or not code.isdigit():
            raise HTTPException(
                status_code=400,
                detail=f"股票代码格式错误: {code}。请输入6位数字代码"
            )
        
        data = realtime_service.get_realtime(code)
        
        if not data or code not in data:
            for key in data:
                if key.endswith(code):
                    quote = data[key]
                    break
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"无法获取股票 {code} 的实时行情"
                )
        else:
            quote = data[code]
        
        now = quote.get('now', 0)
        close = quote.get('close', now)
        change_pct = round((now - close) / close * 100, 2) if close > 0 else 0
        
        return {
            "code": code,
            "name": quote.get('name', ''),
            "now": float(now),
            "open": float(quote.get('open', 0)),
            "close": float(close),
            "high": float(quote.get('high', 0)),
            "low": float(quote.get('low', 0)),
            "volume": int(quote.get('turnover', 0)),
            "turnover": float(quote.get('volume', 0)),
            "change_pct": change_pct,
            "bid1": float(quote.get('bid1', 0)),
            "ask1": float(quote.get('ask1', 0)),
            "time": quote.get('time', ''),
            "date": quote.get('date', datetime.now().strftime('%Y-%m-%d'))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 {code} 实时行情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取实时行情失败: {e}")


@router.post("/realtime/batch")
async def get_realtime_batch(codes: List[str]):
    """批量获取实时行情（最多50只）"""
    try:
        if len(codes) > 50:
            codes = codes[:50]
        
        valid_codes = [c for c in codes if c and len(c) == 6 and c.isdigit()]
        
        if not valid_codes:
            return []
        
        data = realtime_service.get_realtime(valid_codes)
        
        results = []
        for code in valid_codes:
            quote = data.get(code)
            if not quote:
                for key in data:
                    if key.endswith(code):
                        quote = data[key]
                        break
            
            if quote and quote.get('now', 0) > 0:
                now = quote.get('now', 0)
                close = quote.get('close', now)
                change_pct = round((now - close) / close * 100, 2) if close > 0 else 0
                
                results.append({
                    "code": code,
                    "name": quote.get('name', ''),
                    "now": float(now),
                    "change_pct": change_pct,
                    "high": float(quote.get('high', 0)),
                    "low": float(quote.get('low', 0)),
                    "volume": int(quote.get('turnover', 0)),
                })
        
        return results
    except Exception as e:
        logger.error(f"批量获取实时行情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量获取实时行情失败: {e}")


@router.get("/realtime/market")
async def get_market_snapshot(limit: int = 50):
    """获取全市场行情快照"""
    try:
        limit = min(max(1, limit), 500)
        
        data = realtime_service.get_market_snapshot(limit=limit)
        
        results = []
        for code, quote in data.items():
            if quote.get('now', 0) > 0:
                now = quote.get('now', 0)
                close = quote.get('close', now)
                change_pct = round((now - close) / close * 100, 2) if close > 0 else 0
                
                results.append({
                    "code": code,
                    "name": quote.get('name', ''),
                    "now": float(now),
                    "change_pct": change_pct,
                    "high": float(quote.get('high', 0)),
                    "low": float(quote.get('low', 0)),
                    "volume": int(quote.get('turnover', 0)),
                })
        
        results.sort(key=lambda x: x['change_pct'], reverse=True)
        
        return {
            "data": results,
            "total": len(results),
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        logger.error(f"获取市场快照失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取市场快照失败: {e}")


@router.get("/stock/{code}/kline-realtime")
async def get_kline_with_realtime(code: str, days: int = 90):
    """获取历史K线 + 实时更新"""
    try:
        if not code or len(code) != 6 or not code.isdigit():
            raise HTTPException(status_code=400, detail=f"股票代码格式错误: {code}")
        
        kline_data = realtime_kline_service.get_kline_with_realtime(code, days=days)
        
        if not kline_data or len(kline_data) == 0:
            raise HTTPException(status_code=404, detail=f"无法获取股票 {code} 的K线数据")
        
        return kline_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 {code} 实时K线失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取实时K线失败: {e}")


@router.get("/stock/{code}/intraday")
async def get_stock_intraday(code: str):
    """获取股票当日分时走势数据"""
    try:
        if not code or len(code) != 6 or not code.isdigit():
            raise HTTPException(status_code=400, detail=f"股票代码格式错误: {code}")
        
        data = realtime_service.get_intraday(code)
        
        if 'error' in data:
            raise HTTPException(status_code=404, detail=data['error'])
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 {code} 分时数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取分时数据失败: {e}")


@router.get("/stock/{code}/history")
def get_stock_history(code: str):
    """获取股票历史K线数据"""
    from analyzers.stock_analyzer import StockAnalyzer
    import pandas as pd
    
    try:
        if not code or len(code) != 6 or not code.isdigit():
            raise HTTPException(status_code=400, detail=f"股票代码格式错误: {code}")
        
        analyzer = StockAnalyzer()
        result = analyzer.analyze_stock(code)
        
        if not result or 'data' not in result:
            raise HTTPException(status_code=404, detail=f"无法获取股票 {code} 的历史数据")
        
        df = result['data']
        history = []
        for _, row in df.iterrows():
            history.append({
                "time": row['date'].strftime('%Y-%m-%d'),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": int(row['volume']) if 'volume' in row else 0,
                "bbi": float(row['bbi']) if pd.notna(row.get('bbi')) else None,
                "zhixing_trend": float(row['zhixing_trend']) if pd.notna(row.get('zhixing_trend')) else None,
                "zhixing_multi": float(row['zhixing_multi']) if pd.notna(row.get('zhixing_multi')) else None,
                "kdj_j": float(row['kdj_j']) if pd.notna(row.get('kdj_j')) else None,
            })
        
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票 {code} 历史数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取历史数据失败: {e}")
