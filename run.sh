#!/bin/bash
# 启动股票分析系统

echo "🚀 启动股票分析系统..."
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source .venv/bin/activate

# 安装依赖
echo "📥 安装依赖包..."
pip install -r requirements.txt -q

# 启动服务
echo ""
echo "✅ 启动FastAPI服务器..."
echo "📍 API地址: http://127.0.0.1:8000"
echo "🌐 前端启动说明:"
echo "   cd frontend"
echo "   npm install"
echo "   npm run dev"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

cd "$(dirname "$0")"
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

