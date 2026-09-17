<p align="center">
  <img src="docs/readme-cover.svg" alt="StockItsMygo — personal market watcher" width="100%">
</p>

# StockItsMygo

StockItsMygo 是一个可自托管的股票数据、技术信号和多用户 watchlist 系统。后端使用 Flask 与 PostgreSQL / TimescaleDB，支持批量 OHLCV ingestion、技术指标实验和交互式行情 Dashboard。

[![CI](https://github.com/TT1nKer/StockItsMygo/actions/workflows/ci.yml/badge.svg)](https://github.com/TT1nKer/StockItsMygo/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1)
![License](https://img.shields.io/badge/license-MIT-green)

> 这是数据工程与量化研究项目，不是自动交易系统，所有技术信号仅用于实验，不构成投资建议。

## 功能

- PostgreSQL 16 + TimescaleDB hypertable 存储历史和日内行情。
- yfinance 美股数据管线；`cn-a-shares` 分支提供 AKShare + Baostock A 股管线。
- 基于 RSI、动量、成交量和突破形态的规则化信号评分。
- 多用户登录以及相互隔离的 Long / Short / Watch / Wishlist。
- Plotly 个股走势图、市场统计、涨跌榜、搜索和每日信号页面。
- 可重复执行的离线 demo seed，无需 API key 或外部行情服务。
- Docker health checks、pytest 测试与 GitHub Actions CI。

## 五分钟启动

需要 Docker 和 Docker Compose v2。

```bash
git clone https://github.com/TT1nKer/StockItsMygo.git
cd StockItsMygo
cp .env.example .env

# 构建并启动 Web + TimescaleDB，启动时自动创建完整 schema
docker compose up --build -d

# 写入 8 只股票、260 个交易日和今日推荐，用于立即体验 UI
docker compose exec app python tools/seed_demo_data.py
```

访问 <http://localhost:8090>，使用演示账号：

- Username: `admin`
- Password: `admin123`

健康检查：

```bash
curl http://localhost:8090/api/health
docker compose ps
```

停止服务：

```bash
docker compose down
```

数据库数据保存在 `./pg-data/`。`docker compose down` 不会删除行情；只有明确执行 `docker compose down -v` 或删除该目录才会清空数据。

## 本地 Python 启动

```bash
python -m venv venv
source venv/bin/activate                 # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt

docker compose up -d timescaledb
export STOCK_DB_TYPE=postgresql
python db/init_db_postgres.py
python tools/seed_demo_data.py            # 可选的离线演示数据
python web_dashboard.py
```

默认端口统一为 `8090`。

## 使用真实数据

Demo seed 只用于快速验收。美股真实数据由 yfinance 下载：

```bash
source venv/bin/activate
export STOCK_DB_TYPE=postgresql
python tools/update_recent_data.py --days 30 --yes
python strategy_recommender_fast.py
```

全量数据下载可能持续数小时，并受到免费数据源限流影响：

```bash
python tools/download_all_stocks.py
```

### A 股分支

```bash
git switch cn-a-shares
docker compose --profile cn up -d timescaledb-cn

export STOCK_DB_TYPE=postgresql
export STOCK_PG_PORT=5433
export STOCK_PG_DATABASE=stock_db_cn
python db/init_db_postgres.py
python tools/cn_backfill.py --workers 8
python web_dashboard.py
```

| Branch | 市场 | 数据源 | 默认数据库 |
| --- | --- | --- | --- |
| `main` | 美股 | yfinance | `localhost:5432/stock_db` |
| `cn-a-shares` | 沪深 A 股 | AKShare、Baostock | `localhost:5433/stock_db_cn` |

## 架构

```text
Market providers              Flask / Plotly dashboard
 yfinance ─────┐                 │
 AKShare ──────┼─> ingestion ─> PostgreSQL + TimescaleDB
 Baostock ─────┘                 │
                         signal scanners / reports
```

主要模块：

- `db/api.py`：行情写入、查询与批处理接口。
- `db/init_db_postgres.py`：幂等 schema 初始化。
- `script/signals/`：动量与异常信号扫描。
- `strategy_recommender_fast.py`：批量技术评分。
- `web_dashboard.py`：认证、Dashboard 和 JSON API。
- `tools/daily_workflow.py`：每日数据与报告编排。

更详细的设计见 [架构文档](docs/ARCHITECTURE.md) 和 [文档索引](docs/MASTER_README.md)。

## 配置

复制 `.env.example` 后修改以下值：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `STOCK_PG_PASSWORD` | `stock_password` | PostgreSQL 密码 |
| `FLASK_SECRET_KEY` | local demo value | Flask session 签名密钥 |
| `STOCK_INVITATION_CODE` | `stocktest2026` | 新用户注册邀请码 |
| `STOCK_ADMIN_PASSWORD` | `admin123` | 首次初始化时的 admin 密码 |
| `DASHBOARD_PORT` | `8090` | 宿主机 Web 端口 |
| `STOCK_PG_HOST` | `localhost` | 非 Docker 模式数据库地址 |
| `STOCK_PG_PORT` | `5432` | 非 Docker 模式数据库端口 |
| `STOCK_PG_DATABASE` | `stock_db` | 数据库名 |

默认凭据只适合本机演示。公开部署前必须替换 `.env` 中的密码、session secret 和邀请码，并放在 HTTPS 反向代理之后。数据更新接口要求登录，Flask debug 默认关闭。

## 测试

```bash
pip install -r requirements-dev.txt
pytest
python -m compileall -q -x '(^|/)(venv|pg-data|pg-data-cn)/' .
docker compose config --quiet
```

`tests/test_phase*.py` 和根目录下较早的 `test_*.py` 是需要真实行情源的历史集成脚本，不属于快速 CI；CI 使用 `tests/test_unit_*.py`。

## 项目边界

- 免费行情源可能延迟、限流或调整字段。
- 技术评分不是机器学习模型，也不预测未来收益。
- 完整历史库不会提交到 Git；使用 ingestion 脚本自行构建。
- 当前没有完整交易成本模型、订单执行、审计日志或生产级回测框架。

## License

[MIT](LICENSE)
