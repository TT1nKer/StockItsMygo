# 用户认证系统设置指南

## 概览

StockItsMygo 支持多用户登录，每个用户有独立的 watchlist。使用邀请码控制注册。

---

## 默认账号

**管理员账号**：
- 用户名：`admin`
- 密码：`admin123`
- **⚠️ 部署后立即修改密码！**

---

## 注册新用户

### 步骤
1. 访问 http://localhost:8080
2. 点击 "New User? Register here"
3. 填写信息：
   - Username（最少 3 个字符）
   - Password（最少 8 个字符）
   - Invitation Code：`stocktest2026`
4. 注册成功后返回登录页面

### 修改邀请码

编辑 `auth.py` 文件第 12 行：
```python
INVITATION_CODE = "your-new-code"
```

重启 Flask 服务器使更改生效。

---

## 用户管理

### 查看所有用户

```bash
source venv/bin/activate
python -c "
import psycopg2
conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
cursor = conn.cursor()
cursor.execute('SELECT id, username, created_at, last_login, is_active FROM users ORDER BY id')
print('ID | Username       | Created             | Last Login          | Active')
print('-' * 75)
for row in cursor.fetchall():
    print(f'{row[0]:2d} | {row[1]:15s} | {str(row[2])[:19]} | {str(row[3])[:19] if row[3] else \"Never\":19s} | {\"✓\" if row[4] else \"✗\"}')
conn.close()
"
```

### 禁用用户

```bash
source venv/bin/activate
python -c "
import psycopg2
conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
cursor = conn.cursor()
cursor.execute(\"UPDATE users SET is_active = false WHERE username = 'baduser'\")
conn.commit()
print('✓ 用户已禁用')
conn.close()
"
```

### 重置用户密码

```bash
source venv/bin/activate
python -c "
from werkzeug.security import generate_password_hash
import psycopg2

new_password = 'newpassword123'
username = 'admin'

password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
cursor = conn.cursor()
cursor.execute('UPDATE users SET password_hash = %s WHERE username = %s', (password_hash, username))
conn.commit()
print(f'✓ {username} 的密码已重置')
conn.close()
"
```

---

## 用户隔离

每个用户的 watchlist 是完全独立的：
- 用户 A 添加 AAPL → 只有用户 A 能看到
- 用户 B 也可以添加 AAPL → 不会冲突
- 删除操作只影响自己的数据

**技术实现**：
- `user_watchlist` 表有 `user_id` 外键
- UNIQUE 约束：`(user_id, symbol)`
- 所有查询都过滤 `WHERE user_id = current_user`

---

## 安全措施

### 当前安全措施
- ✅ 密码使用 PBKDF2-SHA256 哈希（1,000,000 次迭代）
- ✅ Session 使用加密 cookie
- ✅ 邀请码限制注册
- ✅ 参数化 SQL 查询（防止 SQL 注入）

### 已知限制（小规模使用可接受）
- ⚠️ 无 HTTPS（明文传输密码）
- ⚠️ 无登录频率限制
- ⚠️ 无 CSRF 保护

### 建议改进（可选）
- 添加 HTTPS（使用 Let's Encrypt）
- 添加登录尝试限制（Flask-Limiter）
- 添加 CSRF token（Flask-WTF）

---

## 故障排查

### 问题：Admin 密码忘记
**解决方案**：使用上面的"重置用户密码"命令

### 问题：邀请码泄露
**解决方案**：
1. 修改 `auth.py` 中的 `INVITATION_CODE`
2. 重启 Flask 应用
3. 可选：禁用可疑用户账号

### 问题：Session 过期
**正常行为**：关闭浏览器后 session 会过期，需要重新登录

### 问题：多个用户无法添加同一股票
**已修复**：UNIQUE 约束已从 `(symbol)` 改为 `(user_id, symbol)`

---

## 数据库结构

### users 表
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);
```

### user_watchlist 表（部分）
```sql
CREATE TABLE user_watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    ...
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, symbol)
);
```

---

*设置完成日期：2026-01-05*
*默认邀请码：stocktest2026*
*默认密码：admin123（请立即修改！）*
