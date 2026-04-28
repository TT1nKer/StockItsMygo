# 📈 StockItsMygo - AI 股票推荐系统

> 智能股票分析与推荐系统，基于 PostgreSQL + TimescaleDB，支持多用户、仓位管理、实时监控

![Status](https://img.shields.io/badge/status-active-success)
![Python](https://img.shields.io/badge/python-3.x-blue)
![Database](https://img.shields.io/badge/database-PostgreSQL%2013-316192)

---

## ✨ 核心功能

| 功能 | 描述 |
|------|------|
| 📊 **AI 每日推荐** | 基于 RSI、动量、成交量等多维度技术分析 |
| 👁️ **智能 Watchlist** | 4种仓位类型（Long/Short/Watch/Wishlist），自动收益计算 |
| 🔐 **多用户系统** | 邀请码注册，独立 watchlist，安全认证 |
| 📈 **海量数据** | 2,156只股票，9.4M条历史价格数据 |
| ⚡ **高性能** | TimescaleDB 时序优化，支持并发查询 |

---

## 🚀 快速开始

### Docker (推荐 · 一键启动)

```bash
git clone https://github.com/TT1nKer/StockItsMygo.git
cd StockItsMygo
docker compose up -d
```

服务起来后访问 http://localhost:8080。

### 本地 Python 环境

```bash
git clone https://github.com/TT1nKer/StockItsMygo.git
cd StockItsMygo
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python web_dashboard.py
```

### 2. 访问系统

**本地访问**:
```
http://localhost:8080
```

**朋友访问** (选择一种方式):
- **局域网**: `http://192.168.x.x:8080` (同一 WiFi)
- **端口转发**: `http://公网IP:8080` (有路由器控制权)
- **Ngrok**: `https://xxx.ngrok.io` (无路由器控制权) ⭐ 推荐

### 3. 登录

**默认账号**:
- 用户名: `admin`
- 密码: `admin123`
- ⚠️ 首次登录后请立即修改密码！

**注册新用户**:
- 点击 "New User? Register here"
- 邀请码: `stocktest2026`

---

## 📚 文档导航

> 👉 **完整文档请查看：[docs/MASTER_README.md](docs/MASTER_README.md)**

**快速链接**:
- 🚀 [部署指南](docs/deployment/DEPLOYMENT.md) - 完整安装步骤
- 🌐 [网络配置](docs/setup/NETWORK.md) - 局域网/公网访问设置
- 👥 [用户认证](docs/setup/AUTHENTICATION.md) - 多用户管理
- 📊 [数据库指南](docs/DATABASE_GUIDE.md) - 数据查询与分析
- 👁️ [Watchlist 指南](docs/features/WATCHLIST.md) - 仓位管理详解
- ❓ [常见问题 FAQ](docs/setup/FAQ.md) - 故障排除

---

## 🔧 常用命令

```bash
# 启动服务器
source venv/bin/activate
python web_dashboard.py

# 更新数据（在 Web 界面点击 "Update Data" 或运行）
python tools/update_recent_data.py --days 5 --yes
python strategy_recommender_fast.py

# 启动 Ngrok（公网访问）
ngrok http 8080
```

**更多命令**: 查看 [部署指南](docs/deployment/DEPLOYMENT.md)

---

## 🎯 技术栈

PostgreSQL 13 + TimescaleDB • Python 3.x + Flask • Plotly.js • yfinance

---

## 🆘 需要帮助？

📖 [完整文档](docs/MASTER_README.md) • ❓ [FAQ](docs/setup/FAQ.md) • 🌐 [网络问题](docs/setup/NETWORK.md)

---

## 🔐 安全提示

⚠️ 修改默认密码 • ⚠️ 保护邀请码 • ⚠️ 定期备份数据库

---

## 📌 当前状态 / Limitations

- **状态**：active · 个人使用中，非生产级
- **数据源**：yfinance（免费、有延迟、偶尔限流）
- **推荐策略**：基于技术指标（RSI、动量、量能），不构成投资建议
- **覆盖范围**：美股 2,156 只主流标的，不含期权/加密
- **回测**：策略推荐器尚未对接完整回测框架（roadmap）
- **多用户**：邀请码注册可用，但未做严格的速率限制 / 审计日志

---

**Happy Trading! 📈** | MIT License

<div align="center">

[📚 文档总目录](docs/MASTER_README.md) • [🚀 部署指南](docs/deployment/DEPLOYMENT.md) • [❓ FAQ](docs/setup/FAQ.md)

</div>
