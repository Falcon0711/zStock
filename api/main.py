"""
Stock Analysis API - 主入口
模块化路由架构，所有业务逻辑拆分到 api/routes/ 目录
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger

logger = get_logger(__name__)

# ============================================
# 创建 FastAPI 应用
# ============================================

app = FastAPI(
    title="Stock Analysis API",
    description="A股/港股 行情分析 API",
    version="2.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# 注册模块化路由
# ============================================

from api.routes import (
    stock_router,
    market_router,
    realtime_router,
    hk_router,
    user_router,
    system_router,
)

# 股票分析路由 - /api/stock/*
app.include_router(stock_router)

# 市场数据路由 - /api/market/*
app.include_router(market_router)

# 实时行情路由 - /api/realtime/*
app.include_router(realtime_router)

# 港股路由 - /api/hk/*
app.include_router(hk_router)

# 用户管理路由 - /api/user/*
app.include_router(user_router)

# 系统路由 - /api/system/*
app.include_router(system_router)


# ============================================
# 根路由
# ============================================

@app.get("/")
def read_root():
    return {
        "message": "Stock Analysis API is running",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


# ============================================
# 启动入口
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
