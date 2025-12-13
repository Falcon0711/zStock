#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 正在启动 A股智能交易分析系统...${NC}"

# 获取脚本所在目录
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

# 1. 启动后端 (后台运行)
echo -e "${GREEN}📦 正在启动后端服务 (FastAPI)...${NC}"
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt -q
nohup uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "后端运行在 PID: $BACKEND_PID"

# 2. 启动前端 (后台运行)
echo -e "${GREEN}🌐 正在启动前端服务 (React)...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "前端运行在 PID: $FRONTEND_PID"

# 3. 等待服务启动
echo -e "${BLUE}⏳ 等待服务就绪...${NC}"
sleep 5

# 检查后端端口
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${GREEN}✅ 后端已启动: http://127.0.0.1:8000${NC}"
else
    echo "⚠️ 后端启动可能失败，请检查 logs/backend.log"
fi

# 检查前端端口 (默认5173, Vite)
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${GREEN}✅ 前端已启动: http://localhost:5173${NC}"
    echo -e "${BLUE}🎉 系统启动成功！请访问 http://localhost:5173${NC}"
else
    echo "⚠️ 前端启动可能失败，请检查 logs/frontend.log"
fi

echo "日志文件位置:"
echo "- 后端: logs/backend.log"
echo "- 前端: logs/frontend.log"
echo ""
echo "按任意键停止所有服务..."
read -n 1 -s -r -p ""

# 停止服务
echo ""
echo "🛑 正在停止服务..."
kill $BACKEND_PID 2>/dev/null
kill $FRONTEND_PID 2>/dev/null
echo "👋 已退出"
