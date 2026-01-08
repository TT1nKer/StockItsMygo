# 📚 StockItsMygo 文档导航

欢迎来到股票推荐系统的完整文档！所有文档已经整理分类，方便查找。

---

## 🚀 快速开始

**新用户？从这里开始：**
1. [快速启动指南](../README.md) - 系统概览和快速上手
2. [部署指南](deployment/DEPLOYMENT.md) - 完整的部署步骤
3. [常见问题](setup/FAQ.md) - 疑难解答

---

## 📁 文档分类

### 1️⃣ 设置与配置 (`setup/`)
系统安装、配置、初始化相关文档

- **[用户认证设置](setup/AUTHENTICATION.md)**
  - 多用户登录系统
  - 邀请码注册
  - 默认账号信息
  - 用户管理命令

- **[网络配置指南](setup/NETWORK.md)**
  - 本地访问配置
  - 路由器端口转发（有路由器控制权）
  - Ngrok 内网穿透（无路由器控制权）
  - 防火墙设置

- **[常见问题 FAQ](setup/FAQ.md)**
  - 安装问题
  - 网络问题
  - 数据库问题
  - 性能优化

### 2️⃣ 功能特性 (`features/`)
系统核心功能和特性说明

- **[Watchlist 功能](features/WATCHLIST.md)**
  - 添加股票到监控列表
  - 4 种仓位类型（Long/Short/Watch/Wishlist）
  - 过滤和管理
  - 自动收益计算

- **[数据库使用指南](DATABASE_GUIDE.md)**
  - 双语文档（中英文）
  - 数据查询示例
  - 技术指标计算
  - 投资组合分析

### 3️⃣ 部署与运维 (`deployment/`)
部署、升级、备份相关文档

- **[完整部署指南](deployment/DEPLOYMENT.md)**
  - 系统要求（硬件/软件）
  - 详细安装步骤
  - Docker 配置
  - 数据库初始化
  - 验证清单
  - 常见问题解决

### 4️⃣ 归档文档 (`archive/`)
历史文档，仅供参考

- **实现总结** - 原始实现文档
- **迁移记录** - PostgreSQL 迁移技术文档
- **策略系统** - 早期交易策略文档（已停用）

---

## 🎯 常用场景快速导航

### 场景 1：我是新用户，第一次部署
1. 阅读 [README.md](../README.md) 了解系统
2. 按照 [部署指南](deployment/DEPLOYMENT.md) 安装
3. 配置 [用户认证](setup/AUTHENTICATION.md)
4. 设置 [网络访问](setup/NETWORK.md)

### 场景 2：朋友无法访问我的系统
1. 检查 Flask 服务器是否运行
2. 查看 [网络配置指南](setup/NETWORK.md)
3. 如果没有路由器控制权，使用 [Ngrok](setup/NETWORK.md#ngrok-内网穿透)

### 场景 3：想要添加新功能/理解现有功能
1. 查看 [功能特性文档](features/)
2. 了解 [数据库结构](deployment/MIGRATIONS.md)
3. 阅读代码注释

### 场景 4：系统出现问题
1. 查看 [常见问题 FAQ](setup/FAQ.md)
2. 检查 Flask 日志
3. 验证数据库连接

### 场景 5：需要升级系统
1. 备份数据库
2. 按照 [升级指南](deployment/UPGRADE.md) 操作
3. 运行最新迁移

---

## 📊 系统架构概览

```
StockItsMygo/
├── 数据层
│   ├── PostgreSQL + TimescaleDB (价格数据)
│   └── 用户数据 (认证、watchlist)
│
├── 后端
│   ├── Flask Web 服务器
│   ├── 股票推荐算法
│   └── 数据更新脚本
│
└── 前端
    ├── 每日推荐页面
    ├── Watchlist 管理
    └── 股票详情图表
```

---

## 🔧 技术栈

- **数据库**: PostgreSQL 13 + TimescaleDB
- **后端**: Python 3.x + Flask
- **前端**: HTML/CSS/JavaScript (原生)
- **图表**: Plotly.js
- **认证**: Flask Session + bcrypt

---

## 📝 更新日志

### 2026-01-07
- ✅ **重大文档整理**：合并重复文档，精简结构
- ✅ 新增 [DATABASE_GUIDE.md](DATABASE_GUIDE.md) - 双语数据库使用指南
- ✅ 重写 [DEPLOYMENT.md](deployment/DEPLOYMENT.md) - 用户友好的部署指南
- ✅ 归档旧技术文档和策略文档

### 2026-01-06
- ✅ 添加仓位类型功能（Long/Short/Watch/Wishlist）
- ✅ Watchlist 过滤和管理

### 2026-01-05
- ✅ 多用户认证系统
- ✅ Ngrok 内网穿透支持

### 2025-12-XX
- ✅ 每日推荐功能
- ✅ Watchlist 功能
- ✅ Web Dashboard

---

## 🆘 获取帮助

1. **查看文档**: 先查看对应分类的文档
2. **查看日志**: Flask 终端输出 + 浏览器控制台
3. **数据库检查**: 使用提供的 SQL 命令
4. **社区支持**: GitHub Issues

---

## 📂 文档维护

**原则**：
- ✅ 保持文档更新
- ✅ 删除过时文档（移到 archive/）
- ✅ 合并重复内容
- ✅ 清晰的分类结构

**上次整理**: 2026-01-07

**已删除/归档的重复文档**:
- ❌ `HOW_TO_USE.md` → 合并到 `DATABASE_GUIDE.md`
- ❌ `使用指南.md` → 合并到 `DATABASE_GUIDE.md`
- ❌ `QUICK_START.md` → 合并到 `deployment/DEPLOYMENT.md`
- ❌ `策略系统使用指南.md` → 归档到 `archive/`
- ❌ `小资金动量交易指南.md` → 归档到 `archive/`

---

*Happy Trading! 📈*
