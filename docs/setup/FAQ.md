# 常见问题解答 (FAQ)

## 🚀 安装和启动

### Q: 如何第一次启动系统？
```bash
cd /Users/hostsjim/StockItsMygo
source venv/bin/activate
python web_dashboard.py
```
访问 `http://localhost:8080`

### Q: 报错 "Port 8080 is already in use"
**原因**: 端口被占用
**解决方案**:
```bash
# 方法 1: 找到并停止占用进程
lsof -i :8080
kill <PID>

# 方法 2: 换个端口
# 编辑 web_dashboard.py 最后一行，改成 port=9090
```

### Q: 报错 "ModuleNotFoundError"
**原因**: 依赖未安装或虚拟环境未激活
**解决方案**:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🔐 用户和认证

### Q: 忘记 admin 密码怎么办？
```bash
source venv/bin/activate
python -c "
from werkzeug.security import generate_password_hash
import psycopg2

new_password = 'newpassword123'
password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
cursor = conn.cursor()
cursor.execute('UPDATE users SET password_hash = %s WHERE username = %s', (password_hash, 'admin'))
conn.commit()
print('✓ 密码已重置为: newpassword123')
conn.close()
"
```

### Q: 邀请码是什么？在哪里修改？
**默认邀请码**: `stocktest2026`
**修改方法**: 编辑 `auth.py` 第 12 行，然后重启 Flask

### Q: 如何查看所有用户？
```bash
source venv/bin/activate
python -c "
import psycopg2
conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
cursor = conn.cursor()
cursor.execute('SELECT id, username, is_active FROM users')
for row in cursor.fetchall():
    print(f'ID: {row[0]}, Username: {row[1]}, Active: {row[2]}')"
```

---

## 🌐 网络和访问

### Q: 朋友无法访问我的系统
**检查清单**:
1. ✅ Flask 服务器正在运行？
2. ✅ Mac 防火墙允许 Python？
3. ✅ 使用了正确的 IP/URL？
4. ✅ 如果用端口转发，路由器配置了吗？

**最简单方案**: 使用 Ngrok
```bash
# 终端 2
ngrok http 8080
# 分享显示的 https://xxx.ngrok.io 给朋友
```

### Q: 我没有路由器控制权怎么办？
**方案**: 使用 Ngrok 内网穿透
详见：[网络配置指南](NETWORK.md#方案-4ngrok-内网穿透无路由器控制权-推荐)

### Q: Mac 休眠后服务器停止响应
**解决方案**:
- 系统偏好设置 → 节能 → 防止电脑自动睡眠
- 或使用：`caffeinate -s python web_dashboard.py`

### Q: Ngrok 域名每次都变怎么办？
**免费版**: 每次重启域名会变
**解决方案**:
1. 付费版 ($8/月) 可以固定域名
2. 或者保持 Ngrok 一直运行（用 screen）

---

## 💾 数据库

### Q: 如何检查数据库是否运行？
```bash
docker ps | grep postgres
# 如果没有输出，启动 Docker 容器
```

### Q: 数据库连接失败
**检查**:
```bash
# 测试连接
python -c "
import psycopg2
try:
    conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
    print('✓ 数据库连接成功')
    conn.close()
except Exception as e:
    print(f'✗ 连接失败: {e}')
"
```

### Q: 如何备份数据库？
```bash
# 备份
pg_dump -h localhost -U stock_user stock_db > backup_$(date +%Y%m%d).sql

# 恢复
psql -h localhost -U stock_user stock_db < backup_20260106.sql
```

---

## 📊 功能使用

### Q: 如何更新股票数据？
**方法 1**: Web 界面
- 点击右上角 "Update Data" 按钮
- 等待 5-10 分钟

**方法 2**: 命令行
```bash
source venv/bin/activate
python tools/update_recent_data.py --days 5 --yes
python strategy_recommender_fast.py
```

### Q: 为什么某些股票没有推荐？
**可能原因**:
- 数据不足（少于 30 天）
- 评分低于阈值
- 价格数据异常

**解决方案**: 调低评分阈值（在 Web 界面使用滑块）

### Q: 如何改变 Watchlist 中股票的仓位类型？
**目前**: 需要先删除，再重新添加并选择新类型
**未来**: 计划添加快速编辑功能

### Q: 为什么我的 Watchlist 空了？
**可能原因**:
1. 登录了不同的账号（每个用户独立）
2. 数据库迁移问题

**检查**:
```bash
python -c "
import psycopg2
conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
cursor = conn.cursor()
cursor.execute('SELECT user_id, symbol FROM user_watchlist WHERE is_active = true')
for row in cursor.fetchall():
    print(f'User {row[0]}: {row[1]}')"
```

---

## ⚡ 性能

### Q: 推荐生成太慢（超过 10 分钟）
**正常时间**: 5-10 分钟（2156 只股票）
**如果太慢**:
- 检查 CPU 使用率
- 关闭其他占用资源的程序
- 等数据全部加载到内存后会快很多

### Q: Web 界面加载慢
**可能原因**:
- 数据库查询慢
- Watchlist 股票太多（> 50）

**优化**:
- 删除不需要的 watchlist 条目
- 重启 Flask 服务器

---

## 🐛 常见错误

### 错误: "Authentication required"
**原因**: Session 过期或未登录
**解决**: 重新登录

### 错误: "Username already taken"
**原因**: 用户名已存在
**解决**: 换个用户名

### 错误: "Invalid invitation code"
**原因**: 邀请码错误
**解决**: 使用正确的邀请码 `stocktest2026`

### 错误: "duplicate key value violates unique constraint"
**原因**: 尝试添加已在 watchlist 中的股票
**解决**: 该股票已在你的 watchlist 中

---

## 🔧 高级操作

### Q: 如何运行数据库迁移？
```bash
# 查看迁移文件
ls migrations/

# 运行迁移（例如）
docker exec -i <容器名> psql -U stock_user -d stock_db < migrations/002_add_position_type.sql
```

### Q: 如何禁用某个用户？
```bash
python -c "
import psycopg2
conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
cursor = conn.cursor()
cursor.execute(\"UPDATE users SET is_active = false WHERE username = 'baduser'\")
conn.commit()
print('✓ 用户已禁用')"
```

### Q: 如何保持服务器持续运行？
**使用 Screen**:
```bash
screen -S stockserver
cd /Users/hostsjim/StockItsMygo
source venv/bin/activate
python web_dashboard.py
# 按 Ctrl+A 然后 D 分离

# 重新连接
screen -r stockserver
```

---

## 📱 移动端

### Q: 可以在手机上使用吗？
**可以！** Dashboard 是响应式设计，支持手机浏览器。

### Q: 有 App 吗？
**目前没有**。但可以在手机浏览器中"添加到主屏幕"，像 App 一样使用。

---

## 🔒 安全

### Q: 系统安全吗？
**当前安全措施**:
- ✅ 密码 PBKDF2-SHA256 哈希
- ✅ Session 加密
- ✅ 邀请码限制注册
- ✅ SQL 参数化查询

**已知限制**:
- ⚠️ 无 HTTPS（除非用 Ngrok）
- ⚠️ 无登录频率限制

**建议**: 只分享给信任的朋友（10-20 人）

### Q: 密码会被看到吗？
**本地/端口转发**: 明文传输（HTTP）
**Ngrok**: 加密传输（HTTPS）✅ 更安全

---

## 🆘 还有问题？

1. **查看完整文档**: [docs/MASTER_README.md](../MASTER_README.md)
2. **查看具体功能文档**: [docs/features/](../features/)
3. **网络问题**: [docs/setup/NETWORK.md](NETWORK.md)

---

*最后更新：2026-01-06*
