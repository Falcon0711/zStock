# 📈 A股智能交易分析系统 (Smart Stock Analysis System)

基于 FastAPI + React 的现代化A股分析系统，提供专业的K线图表、技术指标分析和交易信号。

## 🌟 主要功能

- **专业图表**: 集成 TradingView 风格的 K 线图，支持缩放、平移。
- **技术指标**: 
  - 均线系统 (MA5/10/20/30/60)
  - KDJ 指标
  - MACD 指标
  - BBI 多空指标
  - 知行趋势指标
- **智能分析**: 自动生成交易信号（金叉/死叉、突破/跌破）。
- **实时数据**: 支持 A 股实时行情和历史数据查询。
- **市场概览**: 热门股票排行和主要指数监控。

## 🛠 技术栈

- **后端**: Python, FastAPI, Pandas, AKShare
- **前端**: React, TypeScript, Ant Design, Lightweight Charts
- **数据源**: AKShare (开源财经数据接口)

## 🚀 快速开始

### 1. 后端启动

```bash
# 1. 进入项目目录
cd /Users/ffmeng/Desktop/Stock

# 2. 运行启动脚本 (自动创建虚拟环境并安装依赖)
./run.sh
```

后端服务将在 `http://127.0.0.1:8000` 启动。

### 2. 前端启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

前端页面将在 `http://localhost:5173` (或终端显示的地址) 启动。

## 📁 项目结构

```
Stock/
├── api/                  # FastAPI 后端代码
├── analyzers/            # 股票分析核心逻辑
├── charts/               # 图表数据处理
├── frontend/             # React 前端项目
│   ├── src/
│   │   ├── components/   # UI 组件
│   │   ├── services/     # API 请求
│   │   └── ...
├── run.sh                # 后端启动脚本
└── requirements.txt      # Python 依赖
```

## 📝 注意事项

- **数据源**: 系统依赖 AKShare 获取数据，请保持网络连接畅通。
- **股票代码**: A股代码为 6 位数字 (如 `000001`, `600519`)。

## 📄 许可证

MIT License
