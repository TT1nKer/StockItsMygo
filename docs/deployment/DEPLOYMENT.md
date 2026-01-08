# 🚀 StockItsMygo 部署指南

> 完整的系统安装、配置和启动指南

**预计时间**: 30-60 分钟 | **难度**: 简单-中等

---

## 📋 目录

1. [系统要求](#系统要求)
2. [安装步骤](#安装步骤)
3. [启动系统](#启动系统)
4. [验证安装](#验证安装)
5. [常见问题](#常见问题)
6. [下一步](#下一步)

---

## 📊 系统要求

### 硬件要求

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| **CPU** | 双核 2.0GHz | 四核 2.5GHz+ |
| **内存** | 4GB RAM | 8GB+ RAM |
| **硬盘** | 5GB 可用空间 | 10GB+ SSD |
| **网络** | 宽带连接 | 高速宽带 |

### 软件要求

- **操作系统**: macOS 10.15+, Windows 10+, Ubuntu 18.04+
- **Python**: 3.8 或更高版本
- **Docker**: Docker Desktop (用于 PostgreSQL)
- **浏览器**: Chrome, Firefox, Safari, Edge (最新版本)

---

## 🛠️ 安装步骤

### 步骤 1: 安装 Python

#### macOS
```bash
# 检查是否已安装
python3 --version

# 如果未安装，使用 Homebrew 安装
brew install python@3.11
```

#### Windows
```bash
# 下载并安装 Python 3.11
# https://www.python.org/downloads/
# 安装时勾选 "Add Python to PATH"

# 验证安装
python --version
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.11 python3-pip python3-venv
```

### 步骤 2: 安装 Docker

#### macOS
```bash
# 下载 Docker Desktop for Mac
# https://www.docker.com/products/docker-desktop

# 安装完成后启动 Docker Desktop
# 验证安装
docker --version
docker-compose --version
```

#### Windows
```bash
# 下载 Docker Desktop for Windows
# https://www.docker.com/products/docker-desktop

# 安装完成后启动 Docker Desktop
# 验证安装
docker --version
docker-compose --version
```

#### Linux
```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo apt install docker-compose

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker
```

### 步骤 3: 克隆项目（如果需要）

```bash
# 如果项目已存在，跳过此步骤
cd ~
git clone https://github.com/your-username/StockItsMygo.git
cd StockItsMygo
```

### 步骤 4: 创建虚拟环境

```bash
# 进入项目目录
cd /Users/hostsjim/StockItsMygo  # macOS/Linux
# 或
cd C:\Users\YourName\StockItsMygo  # Windows

# 创建虚拟环境
python3 -m venv venv  # macOS/Linux
# 或
python -m venv venv   # Windows

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 验证
which python  # 应该显示 venv/bin/python
```

### 步骤 5: 安装 Python 依赖

```bash
# 确保虚拟环境已激活
pip install --upgrade pip

# 安装所有依赖
pip install -r requirements.txt

# 验证关键包
pip list | grep -E "flask|psycopg2|yfinance|pandas|plotly"
```

### 步骤 6: 启动 PostgreSQL 数据库

```bash
# 启动 Docker 容器
docker-compose up -d

# 验证容器运行
docker-compose ps

# 查看日志（可选）
docker-compose logs -f timescaledb

# 按 Ctrl+C 退出日志查看
```

**预期输出**:
```
NAME                   IMAGE                       STATUS
strategy-z-pg          timescale/timescaledb:...   Up
```

### 步骤 7: 初始化数据库

```bash
# 进入 Python 环境
python

# 在 Python 中运行
>>> from db.init_db_postgres import init_database
>>> init_database()
>>> exit()
```

**预期输出**:
```
✓ Database initialized
✓ Tables created
✓ Indexes created
✓ TimescaleDB hypertable configured
```

### 步骤 8: 下载股票列表

```bash
# 下载 NASDAQ 股票列表（快速）
python -c "
from db.api import StockDB
db = StockDB()
# 股票列表会自动从 NASDAQ 下载
print('✓ Stock list downloaded')
"
```

### 步骤 9: 下载初始数据（可选但推荐）

```bash
# 下载前100只股票的数据（测试用，约5-10分钟）
python tools/update_recent_data.py --limit 100 --days 365

# 或下载所有股票（生产用，约2-4小时）
# python tools/download_all_stocks.py
```

---

## 🎯 启动系统

### 方法 1: 直接启动 Flask

```bash
# 1. 确保 PostgreSQL 运行
docker-compose ps

# 2. 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 3. 启动 Flask 服务器
python web_dashboard.py
```

**预期输出**:
```
* Running on http://localhost:8080
* Running on http://192.168.x.x:8080
```

### 方法 2: 后台运行（推荐）

```bash
# macOS/Linux
nohup python web_dashboard.py > logs/flask.log 2>&1 &

# Windows
start /B python web_dashboard.py > logs\flask.log 2>&1
```

### 访问系统

打开浏览器，访问:
```
http://localhost:8080
```

**默认登录账号**:
- 用户名: `admin`
- 密码: `admin123`

⚠️ **重要**: 首次登录后请立即修改密码！

---

## ✅ 验证安装

### 1. 检查 Docker 容器

```bash
docker-compose ps
```

**预期**: `strategy-z-pg` 状态为 `Up`

### 2. 检查数据库连接

```bash
python -c "
from config.database import config
from db.api import StockDB

config.switch_to_postgresql()
db = StockDB()
stocks = db.get_stock_list()
print(f'✓ Database connected: {len(stocks)} stocks')
"
```

**预期输出**: `✓ Database connected: 2156 stocks`

### 3. 检查 Web 服务器

```bash
curl http://localhost:8080
```

**预期**: 返回 HTML 内容（登录页面）

### 4. 检查数据完整性

```bash
python -c "
from db.api import StockDB
db = StockDB()

# 检查价格数据
import subprocess
result = subprocess.run([
    'docker', 'exec', 'strategy-z-pg',
    'psql', '-U', 'stock_user', '-d', 'stock_db',
    '-c', 'SELECT COUNT(*) FROM price_history;'
], capture_output=True, text=True)

print(result.stdout)
"
```

**预期**: 显示价格记录数量

---

## 🔧 配置选项

### 1. 更改 Flask 端口

编辑 `web_dashboard.py`:
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888, debug=False)  # 改为 8888
```

### 2. 切换数据库后端

```python
# 在代码中切换
from config.database import config

# 使用 PostgreSQL（推荐）
config.switch_to_postgresql()

# 使用 SQLite（备份）
config.switch_to_sqlite()
```

### 3. 配置数据更新频率

编辑 `tools/update_recent_data.py` 或在 cron 中设置:

```bash
# macOS/Linux - 每天早上 8 点更新
crontab -e

# 添加以下行
0 8 * * * cd /path/to/StockItsMygo && source venv/bin/activate && python tools/update_recent_data.py --days 5 --yes
```

### 4. 设置邀请码

编辑 `auth.py`:
```python
VALID_INVITE_CODES = [
    'stocktest2026',
    'your_custom_code',  # 添加你的邀请码
]
```

---

## 🆘 常见问题

### Q1: Docker 容器启动失败

**问题**: `docker-compose up -d` 失败

**解决**:
```bash
# 检查 Docker 是否运行
docker ps

# 查看错误日志
docker-compose logs

# 重启 Docker Desktop
# macOS: 重启 Docker Desktop 应用
# Linux: sudo systemctl restart docker

# 删除旧容器重新创建
docker-compose down
docker-compose up -d
```

### Q2: 数据库连接失败

**问题**: `psycopg2.OperationalError: could not connect`

**解决**:
```bash
# 1. 检查容器是否运行
docker-compose ps

# 2. 检查端口是否被占用
lsof -i :5432  # macOS/Linux
netstat -ano | findstr :5432  # Windows

# 3. 测试数据库连接
docker exec -it strategy-z-pg psql -U stock_user -d stock_db -c "SELECT 1;"
```

### Q3: 依赖安装失败

**问题**: `pip install` 报错

**解决**:
```bash
# 升级 pip
pip install --upgrade pip setuptools wheel

# 单独安装问题包
pip install psycopg2-binary
pip install pandas
pip install yfinance

# 如果是 macOS M1/M2 芯片
arch -arm64 pip install psycopg2-binary
```

### Q4: 端口 8080 已被占用

**问题**: `Address already in use: 8080`

**解决**:
```bash
# 查找占用端口的进程
lsof -i :8080  # macOS/Linux
netstat -ano | findstr :8080  # Windows

# 杀死进程
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# 或更改 Flask 端口（见配置选项）
```

### Q5: 虚拟环境激活失败

**问题**: `activate: No such file or directory`

**解决**:
```bash
# 重新创建虚拟环境
rm -rf venv
python3 -m venv venv

# Windows PowerShell 可能需要
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

更多问题？查看 [FAQ](../setup/FAQ.md)

---

## 📊 数据库管理

### Docker 命令速查

```bash
# 启动数据库
docker-compose up -d

# 停止数据库
docker-compose down

# 重启数据库
docker-compose restart

# 查看日志
docker-compose logs -f timescaledb

# 进入数据库 shell
docker exec -it strategy-z-pg psql -U stock_user -d stock_db

# 查看数据库大小
docker exec strategy-z-pg psql -U stock_user -d stock_db -c \
  "SELECT pg_size_pretty(pg_database_size('stock_db'));"

# 备份数据库
docker exec strategy-z-pg pg_dump -U stock_user stock_db > backup_$(date +%Y%m%d).sql

# 恢复数据库
cat backup_20260107.sql | docker exec -i strategy-z-pg psql -U stock_user -d stock_db
```

### 常用 SQL 查询

```sql
-- 连接数据库
docker exec -it strategy-z-pg psql -U stock_user -d stock_db

-- 查看所有表
\dt

-- 统计股票数量
SELECT COUNT(*) FROM stocks;

-- 统计价格记录
SELECT COUNT(*) FROM price_history;

-- 查看最新价格
SELECT symbol, date, close
FROM price_history
WHERE symbol = 'AAPL'
ORDER BY date DESC
LIMIT 5;

-- 查看数据覆盖率
SELECT
    COUNT(DISTINCT symbol) as stocks_with_data,
    MIN(date) as earliest_date,
    MAX(date) as latest_date
FROM price_history;

-- 退出
\q
```

---

## 🎯 下一步

安装完成后，你可以：

### 1. 配置远程访问

让朋友也能访问你的系统：
- 📖 [网络配置指南](../setup/NETWORK.md)

### 2. 添加用户

创建新用户账号：
- 📖 [用户认证指南](../setup/AUTHENTICATION.md)

### 3. 学习使用数据库

编写自己的股票分析代码：
- 📖 [数据库使用指南](../DATABASE_GUIDE.md)

### 4. 自定义推荐算法

调整股票推荐参数：
- 📖 查看 `strategy_recommender_fast.py`

### 5. 设置自动更新

每日自动更新股票数据：
- 📖 [数据更新指南](../features/DATA_UPDATE.md)

---

## 📚 相关文档

| 文档 | 用途 |
|------|------|
| [MASTER_README.md](../MASTER_README.md) | 文档总导航 |
| [NETWORK.md](../setup/NETWORK.md) | 网络配置（局域网/公网） |
| [AUTHENTICATION.md](../setup/AUTHENTICATION.md) | 用户管理 |
| [DATABASE_GUIDE.md](../DATABASE_GUIDE.md) | 数据库使用 |
| [WATCHLIST.md](../features/WATCHLIST.md) | Watchlist 功能 |
| [FAQ.md](../setup/FAQ.md) | 常见问题 |

---

## 🔧 系统架构

```
┌─────────────────────────────────────────────┐
│           用户浏览器 (Browser)               │
│         http://localhost:8080                │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│        Flask Web Server (web_dashboard.py)  │
│  - 用户认证 (auth.py)                       │
│  - 推荐算法 (strategy_recommender_fast.py) │
│  - API 端点                                  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│         Database API (db/api.py)            │
│  - StockDB 类                               │
│  - 数据查询方法                             │
└──────────────────┬──────────────────────────┘
                   │
           ┌───────┴───────┐
           ▼               ▼
┌──────────────────┐ ┌──────────────────┐
│   PostgreSQL     │ │     SQLite       │
│  + TimescaleDB   │ │   (备份后端)     │
│   (Docker)       │ │   db/stock.db    │
└──────────────────┘ └──────────────────┘
```

---

## ⚡ 性能优化建议

### 1. PostgreSQL 配置（高级）

编辑 `docker-compose.yml`:
```yaml
environment:
  - POSTGRES_PASSWORD=stock_password
  - shared_buffers=256MB        # 增加共享内存
  - effective_cache_size=1GB    # 缓存大小
  - work_mem=16MB               # 工作内存
```

### 2. 启用数据压缩

```sql
-- 连接数据库
docker exec -it strategy-z-pg psql -U stock_user -d stock_db

-- 启用压缩（节省空间）
SELECT add_compression_policy('price_history', INTERVAL '7 days');
```

### 3. 定期维护

```bash
# 每周运行一次
docker exec strategy-z-pg psql -U stock_user -d stock_db -c "VACUUM ANALYZE;"
```

---

## 🔒 安全建议

1. **修改默认密码**: 首次登录后立即更改 admin 密码
2. **保护邀请码**: 不要在公开论坛分享邀请码
3. **使用 HTTPS**: 生产环境建议使用 Nginx + SSL
4. **定期备份**: 每周备份一次数据库
5. **限制访问**: 配置防火墙规则

---

## 📞 获取帮助

遇到问题？这里有一些资源：

1. **查看日志**:
   ```bash
   # Flask 日志
   tail -f logs/flask.log

   # Docker 日志
   docker-compose logs -f
   ```

2. **检查文档**:
   - [FAQ](../setup/FAQ.md) - 常见问题
   - [MASTER_README.md](../MASTER_README.md) - 完整文档

3. **社区支持**:
   - GitHub Issues
   - 项目 Wiki

---

**部署完成！开始探索 StockItsMygo 吧！** 📈

*最后更新: 2026-01-07*
