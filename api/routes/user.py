"""
用户相关路由
包含: 用户股票分组、添加/删除股票、汇率信息
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.logger import get_logger
from services.user_stock_service import UserStockService
from services.stock_list_service import StockListService
from services.exchange_rate_service import get_exchange_rate_service
from analyzers.data_fetcher import get_stock_data

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["用户管理"])

# 初始化服务
user_stock_service = UserStockService()
stock_list_service = StockListService()
exchange_rate_service = get_exchange_rate_service()


class StockItem(BaseModel):
    group: str
    code: str


@router.get("/user/stocks")
async def get_user_stocks():
    """获取用户股票分组信息（包含实时行情）"""
    groups = user_stock_service.get_stocks()
    
    result = {
        "favorites": [],
        "holdings": [],
        "watching": []
    }
    
    for group_name, codes in groups.items():
        for code in codes:
            stock_info = {
                "code": code,
                "name": stock_list_service.get_stock_name(code) or code,
                "price": 0,
                "change_pct": 0
            }
            
            try:
                data = get_stock_data(code, days=90)
                if data is not None and len(data) >= 2:
                    latest = data.iloc[-1]
                    prev = data.iloc[-2]
                    close = float(latest['close'])
                    prev_close = float(prev['close'])
                    change_pct = (close - prev_close) / prev_close * 100 if prev_close else 0
                    stock_info['price'] = round(close, 2)
                    stock_info['change_pct'] = round(change_pct, 2)
            except Exception as e:
                logger.warning(f"获取 {code} 行情失败: {e}")
            
            result[group_name].append(stock_info)
    
    return result


@router.post("/user/stocks")
async def add_user_stock(item: StockItem):
    """添加股票到分组"""
    success = user_stock_service.add_stock(item.group, item.code)
    return {"success": success}


@router.delete("/user/stocks")
async def remove_user_stock(item: StockItem):
    """从分组删除股票"""
    success = user_stock_service.remove_stock(item.group, item.code)
    return {"success": success}


# ============================================
# 外汇牌价 API 端点
# ============================================

@router.get("/exchange/usd")
async def get_usd_exchange_rate():
    """获取美元汇率（中国银行）"""
    try:
        rate = exchange_rate_service.get_rate('USD')
        
        if not rate:
            raise HTTPException(
                status_code=404,
                detail="无法获取美元汇率"
            )
        
        return rate
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取美元汇率失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取美元汇率失败: {e}")


@router.get("/exchange/all")
async def get_all_exchange_rates():
    """获取所有支持的外汇牌价"""
    try:
        rates = exchange_rate_service.get_all_rates()
        return rates
    except Exception as e:
        logger.error(f"获取外汇牌价失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取外汇牌价失败: {e}")
