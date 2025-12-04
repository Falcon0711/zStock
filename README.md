# 📈 A股智能交易分析系统

基于 FastAPI + React 的现代化A股分析系统，提供 K 线图表、技术指标分析和交易信号。

## 🌟 功能特性

- **实时行情**: A股/港股/美股指数行情，点击查看K线
- **自选股管理**: 分组管理股票，实时显示涨跌
- **技术指标**: MA均线、KDJ、MACD、BBI、知行趋势
- **智能信号**: 自动生成金叉/死叉交易信号
- **K线图表**: TradingView 风格专业图表

## 🛠 技术栈

| 后端 | 前端 | 数据源 |
|------|------|--------|
| Python, FastAPI | React, TypeScript | AKShare |
| Pandas, NumPy | Lightweight Charts | Yahoo Finance |

## 🚀 快速开始

### 本地开发

```bash
# 后端
cd Stock
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 编辑配置
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install && npm run dev
```

### Docker 部署

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f
```

### 服务器部署

```bash
# 1. 克隆代码
git clone https://github.com/your-username/Stock.git
cd Stock

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 CORS_ORIGINS 为你的域名

# 3. Docker 部署
docker-compose up -d
```

## 📁 项目结构

```
Stock/
├── api/              # FastAPI 后端 API
├── analyzers/        # 数据获取和分析器
├── services/         # 业务服务层
├── frontend/         # React 前端
├── docker-compose.yml
└── requirements.txt
```

## ⚙️ 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CORS_ORIGINS` | 允许的前端域名 | `http://localhost:5173` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `MEMORY_CACHE_TTL` | 缓存时间(秒) | `300` |

## 📝 注意事项

- 股票代码为 6 位数字 (如 `000001`, `600519`)
- 数据依赖 AKShare，请保持网络连接
- 生产环境请使用 HTTPS

## 📄 License

MIT
