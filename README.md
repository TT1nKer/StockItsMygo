# 📈 StockItsMygo - AI 股票推荐系统

> 智能股票分析与推荐系统，支持多用户、仓位管理、实时监控

![Status](https://img.shields.io/badge/status-active-success)
![Python](https://img.shields.io/badge/python-3.x-blue)
![Database](https://img.shields.io/badge/database-PostgreSQL%2013-316192)

---

## ✨ 核心功能

### 📊 AI 每日推荐
- 基于技术分析的智能推荐算法
- RSI、动量、成交量、突破等多维度分析
- 可调节评分阈值，灵活过滤
- **今日推荐**: 查看最新的股票推荐

### 👁️ 智能 Watchlist
- **4 种仓位类型**：
  - 📈 **Long** - 看涨仓位
  - 📉 **Short** - 看跌仓位
  - 👁️ **Watch** - 观察模式
  - ⭐ **Wishlist** - 愿望清单
- 自动计算收益
- 14 天监控期
- 按仓位类型过滤

### 🔐 多用户系统
- 邀请码注册机制
- 独立的用户 watchlist
- 安全的密码哈希
- Session 管理

### 📈 实时数据
- 2156 只股票
- 940 万条历史价格数据
- 一键更新最新数据
- TimescaleDB 优化存储

---

## 🚀 快速开始

### 1. 启动服务器

```bash
cd /Users/hostsjim/StockItsMygo
source venv/bin/activate
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

## 📚 完整文档

### 🎯 新手指南
- [完整部署指南](docs/deployment/DEPLOYMENT.md) - 从零开始部署
- [网络配置](docs/setup/NETWORK.md) - 让朋友可以访问
- [常见问题 FAQ](docs/setup/FAQ.md) - 疑难解答

### ⚙️ 功能文档
- [Watchlist 使用指南](docs/features/WATCHLIST.md) - 仓位管理详解
- [用户认证](docs/setup/AUTHENTICATION.md) - 用户管理
- [数据更新](docs/features/DATA_UPDATE.md) - 如何更新数据

### 📖 完整文档导航
👉 **[文档总目录](docs/MASTER_README.md)** 👈

---

## 💡 使用场景

### 场景 1：日内交易者
```
1. 查看"每日推荐"，找到高分股票
2. 添加看涨的股票为 📈 Long
3. 添加看跌的股票为 📉 Short
4. 用过滤器分别查看做多/做空仓位
```

### 场景 2：长期投资者
```
1. 发现有潜力的股票
2. 添加到 ⭐ Wishlist 愿望清单
3. 研究 1-2 周
4. 决定后改为 📈 Long 并买入
```

### 场景 3：分享给朋友
```
1. 使用 Ngrok 获取公网地址
2. 分享地址和邀请码给朋友
3. 每个人有独立的 watchlist
4. 一起研究和讨论股票
```

---

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| **数据库** | PostgreSQL 13 + TimescaleDB |
| **后端** | Python 3.x + Flask |
| **前端** | HTML/CSS/JavaScript (原生) |
| **图表** | Plotly.js |
| **认证** | Flask Session + Werkzeug Security |
| **数据** | yfinance + pandas |

---

## 📊 数据统计

```
📈 2,156 只股票
💾 9.4M 条价格记录
⏱️ 每日推荐生成：~5-10 分钟
👥 支持多用户（10-20 人）
```

---

## 🔧 常用命令

### 启动服务器
```bash
source venv/bin/activate
python web_dashboard.py
```

### 更新数据
在 Web 界面点击 "Update Data" 按钮，或：
```bash
python tools/update_recent_data.py --days 5 --yes
python strategy_recommender_fast.py
```

### 查看用户
```bash
python -c "
import psycopg2
conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
cursor = conn.cursor()
cursor.execute('SELECT username, is_active FROM users')
for row in cursor.fetchall():
    print(f'{row[0]:15s} - {\"Active\" if row[1] else \"Inactive\"}')"
```

### 使用 Ngrok（无路由器控制权）
```bash
# 终端 1: 启动 Flask
python web_dashboard.py

# 终端 2: 启动 Ngrok
ngrok http 8080
# 会显示: https://abc123.ngrok.io
```

---

## 🌟 最新更新

### v2.1.0 (2026-01-06)
- ✨ 新增仓位类型功能（Long/Short/Watch/Wishlist）
- ✨ Watchlist 过滤功能
- 📚 重新整理文档结构
- 🐛 Bug 修复

### v2.0.0 (2026-01-05)
- ✨ 多用户认证系统
- ✨ Ngrok 内网穿透支持
- 📚 完整部署文档

---

## 📁 项目结构

```
StockItsMygo/
├── web_dashboard.py          # Flask 主应用
├── auth.py                   # 认证模块
├── strategy_recommender_fast.py  # 推荐算法
├── templates/
│   ├── dashboard.html        # 主界面
│   └── login.html            # 登录页面
├── tools/
│   └── update_recent_data.py # 数据更新
├── migrations/               # 数据库迁移
│   ├── 001_add_user_auth.sql
│   └── 002_add_position_type.sql
└── docs/                     # 📚 完整文档
    ├── MASTER_README.md      # 文档导航
    ├── setup/                # 设置指南
    ├── features/             # 功能文档
    ├── deployment/           # 部署指南
    └── archive/              # 历史文档
```

---

## 🆘 需要帮助？

1. **查看文档**: [docs/MASTER_README.md](docs/MASTER_README.md)
2. **常见问题**: [docs/setup/FAQ.md](docs/setup/FAQ.md)
3. **网络问题**: [docs/setup/NETWORK.md](docs/setup/NETWORK.md)
4. **功能使用**: [docs/features/](docs/features/)

---

## 🔐 安全提示

- ⚠️ 修改默认 admin 密码
- ⚠️ 不要把邀请码发到公开论坛
- ⚠️ 定期检查用户列表
- ⚠️ 备份数据库

---

## 📝 License

MIT License - 自由使用和修改

---

<div align="center">

**Happy Trading! 📈**

[文档](docs/MASTER_README.md) • [部署指南](docs/deployment/DEPLOYMENT.md) • [FAQ](docs/setup/FAQ.md)

</div>
