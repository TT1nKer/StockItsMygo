# macOS全新部署 + PostgreSQL迁移指南

## 背景

**目标**: 在macOS上重新搭建股票分析系统，释放Windows资源用于游戏

**优势**:
- ✅ Windows专心打游戏，不受Docker/数据库内存占用影响
- ✅ macOS开发体验更好（Docker原生支持，终端友好）
- ✅ 资源隔离，互不干扰
- ✅ 代码和数据已在GitHub，迁移简单

**数据迁移**: 1.5GB SQLite数据库 + 完整代码库

---

## Phase 0: macOS环境准备（30分钟）

### 0.1 安装开发工具

**1. 安装Homebrew（包管理器）**
```bash
# 打开Terminal（终端）应用
# 运行以下命令
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装完成后，根据提示将Homebrew添加到PATH
# 通常需要运行（M芯片Mac）：
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# 验证安装
brew --version
```

**2. 安装Git**
```bash
brew install git

# 配置Git（如果还没配置）
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

**3. 安装Python 3.11+**
```bash
brew install python@3.11

# 验证安装
python3 --version  # 应该显示 Python 3.11.x

# 创建软链接（可选，方便使用）
brew link python@3.11
```

**4. 安装Docker Desktop for Mac**
```bash
# 方法1: 直接下载安装包
# 访问：https://www.docker.com/products/docker-desktop
# 下载macOS版本（Intel或Apple Silicon根据你的Mac选择）
# 双击.dmg文件安装

# 方法2: 通过Homebrew安装
brew install --cask docker

# 启动Docker Desktop
open /Applications/Docker.app

# 等待Docker Desktop完全启动（状态栏显示绿色鲸鱼图标）
```

**验收标准**:
- [ ] `brew --version` 正常输出
- [ ] `python3 --version` 显示3.11+
- [ ] `git --version` 正常输出
- [ ] Docker Desktop启动成功（状态栏有图标）

---

### 0.2 克隆代码仓库

**1. 选择工作目录**
```bash
# 推荐使用 ~/Projects 或 ~/Code
mkdir -p ~/Projects
cd ~/Projects

# 克隆仓库
git clone https://github.com/TT1nKer/StockItsMygo.git strategy-z
cd strategy-z

# 查看结构
ls -la
```

**2. 检查代码完整性**
```bash
# 确认关键文件存在
ls db/init_db.py
ls db/api.py
ls script/momentum_strategy.py
ls plans/postgresql-migration-plan.md

# 查看当前分支
git branch
git log --oneline -5
```

**验收标准**:
- [ ] 代码仓库克隆成功
- [ ] 关键文件存在
- [ ] Git历史正常

---

### 0.3 迁移SQLite数据库

**方法1: 通过网盘迁移（推荐，最简单）**
```bash
# 在Windows上：
# 1. 将 d:/strategy=Z/db/stock.db 上传到百度网盘/OneDrive/Google Drive
# 2. 记下文件大小（应该约1.5GB）

# 在macOS上：
# 1. 下载stock.db到 ~/Downloads/
# 2. 移动到项目目录
cd ~/Projects/strategy-z
mkdir -p db
mv ~/Downloads/stock.db db/stock.db

# 验证文件完整性
ls -lh db/stock.db  # 检查大小是否正确（约1.5GB）
file db/stock.db    # 应显示 SQLite 3.x database
```

**方法2: 通过局域网传输（如果两台机器在同一WiFi）**
```bash
# 在Windows上（假设IP是192.168.1.100）：
# 方法2a: 使用Python启动简易HTTP服务器
cd d:\strategy=Z\db
python -m http.server 8000

# 在macOS上：
cd ~/Projects/strategy-z/db
curl -O http://192.168.1.100:8000/stock.db

# 或者使用scp（需要Windows安装OpenSSH Server）
scp username@192.168.1.100:d:/strategy=Z/db/stock.db ~/Projects/strategy-z/db/
```

**方法3: 通过U盘传输**
```bash
# 在Windows上：
# 1. 插入U盘（假设盘符为E:）
# 2. 复制文件
copy d:\strategy=Z\db\stock.db E:\stock.db

# 在macOS上：
# 1. 插入U盘，会自动挂载到 /Volumes/USBDRIVE（名称可能不同）
# 2. 复制文件
cp /Volumes/USBDRIVE/stock.db ~/Projects/strategy-z/db/stock.db
```

**验证数据库完整性**
```bash
cd ~/Projects/strategy-z

# 使用SQLite命令行工具检查
sqlite3 db/stock.db "SELECT COUNT(*) FROM stocks;"
# 应该输出 2156（或你的实际股票数量）

sqlite3 db/stock.db "SELECT COUNT(*) FROM price_history;"
# 应该输出约200万行

sqlite3 db/stock.db ".tables"
# 应该显示16张表
```

**验收标准**:
- [ ] stock.db文件大小约1.5GB
- [ ] SQLite能正常打开数据库
- [ ] stocks表有2156行
- [ ] price_history表有约200万行

---

### 0.4 安装Python依赖

**1. 创建虚拟环境（推荐）**
```bash
cd ~/Projects/strategy-z

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 验证虚拟环境
which python  # 应该显示 ~/Projects/strategy-z/venv/bin/python
```

**2. 安装依赖**
```bash
# 如果有requirements.txt
pip install -r requirements.txt

# 如果没有，手动安装核心依赖
pip install yfinance pandas numpy scipy scikit-learn psycopg2-binary

# 验证安装
python -c "import yfinance; import pandas; import psycopg2; print('All dependencies OK')"
```

**3. 修改文件路径为macOS风格**

由于Windows使用 `d:/strategy=Z`，macOS需要改为 `~/Projects/strategy-z`

**需要修改的文件**（暂时不改，先验证SQLite版本能跑）:
- `db/api.py` - SQLite路径
- `check_data_summary.py` - SQLite路径
- 其他硬编码路径的文件

**验收标准**:
- [ ] 虚拟环境创建成功
- [ ] 所有依赖安装成功
- [ ] import测试通过

---

### 0.5 测试SQLite版本能否运行

**1. 快速测试数据库连接**
```bash
cd ~/Projects/strategy-z
source venv/bin/activate  # 激活虚拟环境

# 测试数据库API
python -c "
import sys
sys.path.insert(0, '.')
from db.api import StockDB

db = StockDB()
stocks = db.get_stock_list()
print(f'Loaded {len(stocks)} stocks')
print(f'Sample: {stocks[:5]}')
"
```

**2. 运行完整的daily_observation**
```bash
# 如果路径有问题，先临时修改
# 编辑 db/api.py 第10行左右
# 将 self.db_path = 'd:/strategy=Z/db/stock.db'
# 改为 self.db_path = os.path.join(os.path.dirname(__file__), 'stock.db')

# 运行daily_observation
python daily_observation.py
```

**3. 常见问题修复**

**问题1: 路径错误**
```bash
# 错误: FileNotFoundError: d:/strategy=Z/db/stock.db
# 解决: 修改 db/api.py
# 找到 self.db_path = 'd:/strategy=Z/db/stock.db'
# 改为相对路径或绝对路径
```

**问题2: 模块导入错误**
```bash
# 错误: ModuleNotFoundError: No module named 'yfinance'
# 解决: pip install yfinance
```

**问题3: 编码错误**
```bash
# 错误: UnicodeDecodeError
# 解决: 文件编码问题，确保都是UTF-8
```

**验收标准**:
- [ ] 数据库API测试通过
- [ ] daily_observation.py能运行
- [ ] 生成今日候选列表

**如果测试失败**: 先解决SQLite版本的问题，再考虑迁移PostgreSQL

---

## Phase 1: Docker环境搭建（10分钟）

### 1.1 创建Docker配置

**1. 创建必要目录**
```bash
cd ~/Projects/strategy-z

mkdir -p db/pg-config
mkdir -p pg-data
```

**2. 创建 `docker-compose.yml`**
```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    container_name: strategy-z-pg
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: stock_password
      POSTGRES_DB: stock_db
      POSTGRES_USER: stock_user
      TZ: UTC
    ports:
      - "5432:5432"
    volumes:
      - ./pg-data:/var/lib/postgresql/data
      - ./db/pg-config/init.sql:/docker-entrypoint-initdb.d/01-init.sql
    command:
      - postgres
      - -c shared_preload_libraries=timescaledb
      - -c max_connections=200
      - -c shared_buffers=512MB
      - -c effective_cache_size=1GB
      - -c maintenance_work_mem=128MB
      - -c work_mem=16MB
      - -c wal_buffers=16MB
      - -c checkpoint_completion_target=0.9
      - -c random_page_cost=1.1
      - -c effective_io_concurrency=200
EOF
```

**3. 创建 `db/pg-config/init.sql`**
```bash
cat > db/pg-config/init.sql << 'EOF'
-- 启用TimescaleDB扩展
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 设置时区
SET timezone = 'UTC';

-- 启用自动统计收集
ALTER DATABASE stock_db SET default_statistics_target = 100;
EOF
```

**4. 将pg-data目录添加到.gitignore**
```bash
echo "pg-data/" >> .gitignore
```

**验收标准**:
- [ ] docker-compose.yml创建成功
- [ ] db/pg-config/init.sql创建成功
- [ ] pg-data目录存在

---

### 1.2 启动PostgreSQL容器

**1. 启动容器**
```bash
cd ~/Projects/strategy-z

# 启动PostgreSQL + TimescaleDB
docker-compose up -d

# 预期输出:
# Creating network "strategy-z_default" with the default driver
# Creating strategy-z-pg ... done
```

**2. 检查容器状态**
```bash
# 查看容器状态
docker-compose ps

# 预期输出:
# Name                  Command               State           Ports
# -------------------------------------------------------------------------
# strategy-z-pg   docker-entrypoint.sh postgres   Up      0.0.0.0:5432->5432/tcp

# 查看日志
docker-compose logs timescaledb

# 预期看到:
# PostgreSQL init process complete; ready for start up.
# database system is ready to accept connections
```

**3. 验证TimescaleDB扩展**
```bash
# 连接到数据库
docker exec -it strategy-z-pg psql -U stock_user -d stock_db

# 在psql提示符下执行:
SELECT * FROM pg_extension WHERE extname = 'timescaledb';
# 应该显示timescaledb已安装

# 查看PostgreSQL版本
SELECT version();
# 应该显示 PostgreSQL 16.x

# 退出psql
\q
```

**4. 测试Python连接**
```bash
# 测试psycopg2连接
python -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    user='stock_user',
    password='stock_password',
    database='stock_db'
)
print('PostgreSQL connection OK')
conn.close()
"
```

**验收标准**:
- [ ] 容器启动成功（docker-compose ps显示Up）
- [ ] TimescaleDB扩展已启用
- [ ] Python能连接到PostgreSQL

---

## Phase 2: 配置管理系统（30分钟）

### 2.1 创建数据库配置文件

**创建 `config/database.py`**
```bash
mkdir -p config

cat > config/database.py << 'EOF'
"""
Database Configuration
支持SQLite和PostgreSQL双后端
"""
import os

class DatabaseConfig:
    DB_TYPE = 'sqlite'  # 'sqlite' or 'postgresql'

    # SQLite配置（使用相对路径，跨平台兼容）
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    SQLITE_PATH = os.path.join(BASE_DIR, 'db', 'stock.db')

    # PostgreSQL配置
    PG_HOST = 'localhost'
    PG_PORT = 5432
    PG_USER = 'stock_user'
    PG_PASSWORD = 'stock_password'
    PG_DATABASE = 'stock_db'
    PG_CONNECT_TIMEOUT = 30

    @classmethod
    def switch_to_postgresql(cls):
        cls.DB_TYPE = 'postgresql'

    @classmethod
    def switch_to_sqlite(cls):
        cls.DB_TYPE = 'sqlite'

    @classmethod
    def get_connection_string(cls):
        """返回连接字符串（用于psycopg2）"""
        if cls.DB_TYPE == 'postgresql':
            return f"host={cls.PG_HOST} port={cls.PG_PORT} dbname={cls.PG_DATABASE} " \
                   f"user={cls.PG_USER} password={cls.PG_PASSWORD} connect_timeout={cls.PG_CONNECT_TIMEOUT}"
        else:
            return cls.SQLITE_PATH


config = DatabaseConfig()
EOF

# 创建__init__.py
touch config/__init__.py
```

**验证配置文件**
```bash
python -c "
from config.database import config
print(f'DB Type: {config.DB_TYPE}')
print(f'SQLite Path: {config.SQLITE_PATH}')
print(f'PostgreSQL Connection String: {config.get_connection_string()}')
"
```

**验收标准**:
- [ ] config/database.py创建成功
- [ ] import测试通过
- [ ] 路径自动适配（不再有Windows路径）

---

### 2.2 创建数据库抽象层

**创建 `db/connection.py`**
```bash
cat > db/connection.py << 'EOF'
"""
Database Connection Manager
统一SQLite和PostgreSQL的连接和语法差异
"""

import sqlite3
import psycopg2
import psycopg2.extras
from config.database import config


class DatabaseConnection:
    """数据库连接管理器"""

    def __init__(self):
        self.db_type = config.DB_TYPE

    def connect(self):
        """创建数据库连接"""
        if self.db_type == 'sqlite':
            conn = sqlite3.connect(config.SQLITE_PATH)
            conn.execute('PRAGMA foreign_keys = ON')
            return conn
        else:  # PostgreSQL
            conn = psycopg2.connect(config.get_connection_string())
            conn.set_session(autocommit=False)
            return conn

    def get_placeholder(self, n=1):
        """
        返回占位符字符串

        Args:
            n: 占位符数量

        Returns:
            SQLite: '?, ?, ?'
            PostgreSQL: '%s, %s, %s'
        """
        if self.db_type == 'sqlite':
            return ', '.join(['?'] * n)
        else:
            return ', '.join(['%s'] * n)

    def insert_or_replace(self, table, columns, conflict_columns=None):
        """
        生成INSERT OR REPLACE语句

        Args:
            table: 表名
            columns: 列名列表 ['col1', 'col2', 'col3']
            conflict_columns: 冲突列（主键/唯一索引）['id'] 或 ['symbol', 'date']
                            如果为None，自动使用第一列作为冲突列

        Returns:
            SQL语句模板
        """
        if conflict_columns is None:
            conflict_columns = [columns[0]]

        placeholders = self.get_placeholder(len(columns))
        cols_str = ', '.join(columns)

        if self.db_type == 'sqlite':
            return f"INSERT OR REPLACE INTO {table} ({cols_str}) VALUES ({placeholders})"

        else:  # PostgreSQL
            conflict_str = ', '.join(conflict_columns)

            # 生成UPDATE子句（排除冲突列）
            update_cols = [col for col in columns if col not in conflict_columns]
            if update_cols:
                updates = ', '.join([f"{col} = EXCLUDED.{col}" for col in update_cols])
                return f"""
                    INSERT INTO {table} ({cols_str})
                    VALUES ({placeholders})
                    ON CONFLICT ({conflict_str}) DO UPDATE SET {updates}
                """
            else:
                # 所有列都是主键，只插入不更新
                return f"""
                    INSERT INTO {table} ({cols_str})
                    VALUES ({placeholders})
                    ON CONFLICT ({conflict_str}) DO NOTHING
                """

    def create_index(self, index_name, table, columns, unique=False):
        """创建索引（处理IF NOT EXISTS语法差异）"""
        unique_str = 'UNIQUE ' if unique else ''
        cols_str = ', '.join(columns)

        if self.db_type == 'sqlite':
            return f"CREATE {unique_str}INDEX IF NOT EXISTS {index_name} ON {table} ({cols_str})"
        else:
            return f"CREATE {unique_str}INDEX IF NOT EXISTS {index_name} ON {table} ({cols_str})"

    def get_autoincrement_type(self):
        """返回自增字段类型"""
        if self.db_type == 'sqlite':
            return 'INTEGER PRIMARY KEY AUTOINCREMENT'
        else:
            return 'SERIAL PRIMARY KEY'


# 全局连接管理器
db_connection = DatabaseConnection()
EOF
```

**验证抽象层**
```bash
python -c "
from db.connection import db_connection
from config.database import config

print(f'Database Type: {config.DB_TYPE}')
print(f'Placeholder (3 args): {db_connection.get_placeholder(3)}')

# 测试SQLite连接
conn = db_connection.connect()
print('SQLite connection OK')
conn.close()

# 测试PostgreSQL配置切换
config.switch_to_postgresql()
print(f'Switched to: {config.DB_TYPE}')
sql = db_connection.insert_or_replace('stocks', ['symbol', 'name'], ['symbol'])
print(f'PostgreSQL SQL: {sql[:100]}...')
"
```

**验收标准**:
- [ ] db/connection.py创建成功
- [ ] SQLite连接测试通过
- [ ] insert_or_replace()生成正确SQL

---

## Phase 3: 代码改造（参考主plan文件）

**关键改造点**:
1. `db/init_db.py` - 16张表DDL转换
2. `db/api.py` - 11处INSERT OR REPLACE改造
3. `tools/daily_update.py` - 修复直接连接
4. `check_data_summary.py` - 修复直接连接

**详细步骤参考**: `plans/postgresql-migration-plan.md` Phase 3

**macOS特殊注意事项**:
- ✅ 所有文件路径已改为相对路径（跨平台兼容）
- ✅ Docker配置无需WSL2（macOS原生支持）
- ✅ 终端命令100%兼容

---

## Phase 4: 数据迁移（30分钟）

**创建迁移脚本**: `tools/migrate_to_postgresql.py`

**详细步骤参考**: `plans/postgresql-migration-plan.md` Phase 4

**macOS运行命令**:
```bash
cd ~/Projects/strategy-z
source venv/bin/activate

# 1. 初始化PostgreSQL表结构
python -c "from config.database import config; config.switch_to_postgresql()"
python db/init_db.py

# 2. 运行迁移
python tools/migrate_to_postgresql.py

# 预期输出:
# [1/16] Migrating stocks... 2156 rows
# [2/16] Migrating price_history... 1,234,567 rows
# ...
# Migration Completed!
# Total rows: 1,450,000
# Time: 18.5 minutes
```

---

## Phase 5: 测试与切换（参考主plan文件）

**详细步骤参考**: `plans/postgresql-migration-plan.md` Phase 5

**macOS特定测试**:
```bash
# 性能对比
DB_TYPE=sqlite python tests/benchmark_sqlite_vs_postgresql.py
DB_TYPE=postgresql python tests/benchmark_sqlite_vs_postgresql.py

# 正式切换
# 编辑 config/database.py，将 DB_TYPE 改为 'postgresql'
python daily_observation.py

# 验证
python -c "from script.watchlist import WatchlistManager; wl = WatchlistManager(); print(wl.get_statistics())"
```

---

## macOS vs Windows 差异总结

| 方面 | Windows | macOS |
|------|---------|-------|
| **文件路径** | `d:/strategy=Z/db/stock.db` | `~/Projects/strategy-z/db/stock.db` |
| **路径分隔符** | `\` 或 `/` | `/` |
| **Python命令** | `python` 或 `python3` | `python3`（默认） |
| **虚拟环境激活** | `venv\Scripts\activate` | `source venv/bin/activate` |
| **Docker底层** | WSL2（轻量级虚拟机） | 原生支持（更轻量） |
| **内存占用** | Docker Desktop ~2GB | Docker Desktop ~1.5GB |
| **终端** | PowerShell/CMD | Terminal (zsh/bash) |
| **包管理器** | 无（手动安装） | Homebrew |

---

## 常见问题

### Q1: macOS上Docker占用内存会比Windows少吗？
**A**: 是的！macOS的Docker Desktop比Windows轻量：
- macOS: ~1.5GB（原生支持，无需WSL2）
- Windows: ~2GB（需要WSL2虚拟机）

### Q2: M芯片Mac有什么特别注意的？
**A**: TimescaleDB镜像支持M芯片，但首次拉取镜像会慢一些（转译）：
```bash
# 如果是M芯片Mac，确保Docker Desktop启用了Rosetta 2
# Docker Desktop → Settings → General → "Use Rosetta for x86/amd64 emulation"
```

### Q3: 如何在macOS和Windows之间同步代码？
**A**: 使用Git双向同步：
```bash
# macOS上修改代码后
git add .
git commit -m "macOS development updates"
git push

# Windows上拉取
git pull
```

### Q4: SQLite数据库需要定期同步吗？
**A**: 迁移到PostgreSQL后不需要：
- macOS专门用于分析，PostgreSQL是主数据库
- Windows只用于打游戏，不再运行股票系统
- 如果Windows偶尔需要运行，直接连接macOS的PostgreSQL：
  ```python
  # Windows上修改config/database.py
  PG_HOST = 'macos的IP地址'  # 如192.168.1.50
  ```

### Q5: 如何释放macOS硬盘空间？
**A**: PostgreSQL数据库占用约2GB（包含索引），比SQLite的1.5GB略大：
```bash
# 查看pg-data目录大小
du -sh ~/Projects/strategy-z/pg-data

# 如果需要清理旧数据（小心！）
docker-compose down -v  # 删除所有数据
```

---

## 回滚方案

### 如果PostgreSQL迁移失败

**场景1: 迁移中断**
```bash
# 停止PostgreSQL
docker-compose down

# 切换回SQLite
python -c "from config.database import config; config.switch_to_sqlite()"

# 验证
python daily_observation.py
```

**场景2: 性能不达标**
```bash
# 调优PostgreSQL配置
vim docker-compose.yml  # 修改shared_buffers, work_mem等

# 重启容器
docker-compose restart timescaledb

# 如果仍不行，回退SQLite
config.switch_to_sqlite()
```

**场景3: macOS硬盘空间不足**
```bash
# 删除PostgreSQL数据
docker-compose down -v

# 继续用SQLite（1.5GB vs 2GB，省500MB）
```

---

## 成功标准

### 定量指标

- [ ] macOS环境搭建完成（Python + Docker + Git）
- [ ] SQLite数据库迁移成功（2156只股票）
- [ ] PostgreSQL迁移完成（16张表，200万行）
- [ ] 查询性能不低于SQLite
- [ ] Windows内存释放至少2.5GB

### 定性指标

- [ ] daily_observation.py正常运行
- [ ] 无"database locked"错误
- [ ] workers可以设置为10
- [ ] macOS和Windows代码通过Git同步
- [ ] Windows可以专心打游戏

---

## 下一步行动

### 立即可做（macOS上）

**1. 准备环境**
```bash
# 安装Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装工具
brew install git python@3.11 docker
```

**2. 克隆代码**
```bash
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/TT1nKer/StockItsMygo.git strategy-z
```

**3. 迁移数据库**
```bash
# 通过网盘下载stock.db到macOS
# 放到 ~/Projects/strategy-z/db/stock.db
```

**4. 测试SQLite版本**
```bash
cd ~/Projects/strategy-z
python3 -m venv venv
source venv/bin/activate
pip install yfinance pandas numpy scipy scikit-learn psycopg2-binary
python daily_observation.py
```

**如果SQLite版本能跑**: 继续执行PostgreSQL迁移（Phase 1-5）

**如果SQLite版本不能跑**: 先解决依赖问题，再考虑迁移

---

## 总结

**macOS部署优势**:
- ✅ Docker原生支持，更轻量稳定
- ✅ 终端体验更好（Unix命令）
- ✅ Python生态更友好
- ✅ 释放Windows资源用于游戏
- ✅ 代码通过Git同步，随时可在两台机器切换

**迁移路径**:
```
Windows SQLite (1.5GB)
    ↓
macOS SQLite (验证环境)
    ↓
macOS PostgreSQL + TimescaleDB (生产环境)
```

**预计时间**:
- 环境准备: 30分钟
- SQLite验证: 1小时
- PostgreSQL迁移: 3天（和Windows版本相同）

准备好开始了吗？我可以帮你：
1. 生成自动化安装脚本（一键安装Homebrew + Python + Docker）
2. 检查你的SQLite数据库完整性
3. 直接开始Phase 1实施

你想从哪一步开始？
