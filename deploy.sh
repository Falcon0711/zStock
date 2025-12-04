#!/bin/bash

# 1. 检查并安装 Docker
if ! command -v docker &> /dev/null; then
    echo "Docker 未安装，正在尝试自动安装..."
    if command -v curl &> /dev/null; then
        curl -fsSL https://get.docker.com | bash
    else
        echo "错误: 未找到 curl，请手动安装 Docker"
        exit 1
    fi
fi

# 2. 构建前端
echo "正在构建前端..."
cd frontend
if ! command -v npm &> /dev/null; then
    echo "错误: npm 未安装。请先安装 Node.js 和 npm (例如: apt install nodejs npm)"
    exit 1
fi

# 安装依赖并构建
npm install
npm run build

if [ ! -d "dist" ]; then
    echo "错误: 前端构建失败，dist 目录不存在"
    exit 1
fi
cd ..

# 3. 启动 Docker 服务
echo "正在启动 Docker 服务..."
docker compose up -d --build

echo "========================================"
echo "✅ 部署完成！"
echo "后端日志: docker logs -f stock_backend"
echo "访问地址: http://localhost (或服务器公网IP)"
echo "========================================"

# 4. 询问是否同步数据
read -p "是否立即在后台同步全市场历史数据？(建议首次部署执行，耗时约40分钟) [y/N] " sync_choice
if [[ "$sync_choice" =~ ^[Yy]$ ]]; then
    echo "🚀 正在后台启动全量同步..."
    docker exec -d stock_backend python /app/scripts/sync_data.py --all
    echo "✅ 同步任务已在后台运行！"
    echo "查看同步进度: docker logs -f stock_backend"
else
    echo "已跳过同步。后续可手动运行: docker exec stock_backend python /app/scripts/sync_data.py --watchlist"
fi
