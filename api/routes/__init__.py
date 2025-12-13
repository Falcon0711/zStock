"""
API 路由模块
按功能拆分的模块化路由注册
"""

from api.routes.stock import router as stock_router
from api.routes.market import router as market_router
from api.routes.realtime import router as realtime_router
from api.routes.hk import router as hk_router
from api.routes.user import router as user_router
from api.routes.system import router as system_router

__all__ = [
    'stock_router',
    'market_router', 
    'realtime_router',
    'hk_router',
    'user_router',
    'system_router',
]
