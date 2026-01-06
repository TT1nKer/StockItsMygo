# 网络配置指南

让朋友可以从任何地方访问你的股票推荐系统

---

## 访问方式对比

| 方式 | URL | 适用场景 | 需要配置 |
|------|-----|----------|----------|
| 本地 | `http://localhost:8080` | 只有你自己 | 无 |
| 局域网 | `http://192.168.x.x:8080` | 同一 WiFi 的朋友 | Mac 防火墙 |
| 端口转发 | `http://公网IP:8080` | 任何地方（有路由器控制权）| 路由器 + 防火墙 |
| Ngrok | `https://xxx.ngrok.io` | 任何地方（无路由器控制权）| Ngrok 账号 |

---

## 方案 1：本地访问（最简单）

### 步骤
1. 启动 Flask 服务器
   ```bash
   cd /Users/hostsjim/StockItsMygo
   source venv/bin/activate
   python web_dashboard.py
   ```

2. 访问：`http://localhost:8080`

**适用场景**：自己测试使用

---

## 方案 2：局域网访问（同一 WiFi）

### 步骤

1. **获取 Mac IP 地址**
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```
   例如：`inet 192.168.2.236`

2. **配置 Mac 防火墙**
   - 系统偏好设置 → 安全性与隐私 → 防火墙
   - 点击 **防火墙选项**
   - 确保 **Python** 设置为 **允许传入连接**

3. **启动服务器**
   ```bash
   python web_dashboard.py
   ```

4. **朋友访问**
   - 连接同一个 WiFi
   - 打开浏览器访问：`http://192.168.2.236:8080`

**适用场景**：朋友来你家，或者公司同事

---

## 方案 3：端口转发（有路由器控制权）

### 前提条件
- ✅ 你可以登录路由器管理界面
- ✅ Mac 在路由器的局域网内

### 步骤

#### 1. 获取 Mac 本地 IP
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

#### 2. 登录路由器管理界面
常见路由器登录地址：
- `http://192.168.1.1` 或 `http://192.168.2.1`
- TP-Link: `http://tplogin.cn`
- 华为: `http://192.168.3.1`
- 小米: `http://192.168.31.1`

用户名/密码通常在路由器背面标签上。

#### 3. 配置端口转发
找到菜单（不同品牌位置不同）：
- **TP-Link**: 转发规则 → 虚拟服务器
- **华为**: 安全 → 虚拟服务器
- **小米**: 高级设置 → 端口转发

填写配置：
| 字段 | 值 |
|------|------|
| 服务名称 | Stock Dashboard |
| 外部端口 | 8080 |
| 内部 IP | 192.168.2.236（你的 Mac IP）|
| 内部端口 | 8080 |
| 协议 | TCP |
| 状态 | 启用 |

保存后，某些路由器需要重启。

#### 4. 获取公网 IP
```bash
curl ifconfig.me
```

例如：`123.45.67.89`

#### 5. 测试访问

**本地测试**：
```bash
# Mac 浏览器
http://localhost:8080
```

**局域网测试**：
```bash
# 手机连接同一 WiFi
http://192.168.2.236:8080
```

**外网测试**（最重要）：
```bash
# 手机断开 WiFi，使用 4G/5G
http://123.45.67.89:8080
```

如果能看到登录页面 → ✅ 配置成功！

#### 6. 分享给朋友
```
访问地址：http://123.45.67.89:8080
邀请码：stocktest2026
```

### 故障排查

❌ **无法访问？检查清单**：
- [ ] Flask 服务器正在运行（终端有输出）
- [ ] Mac 未休眠（活动监视器能看到 Python 进程）
- [ ] Mac 防火墙允许 Python 连接
- [ ] 公网 IP 是最新的（`curl ifconfig.me`）
- [ ] 路由器端口转发规则已保存并启用
- [ ] 路由器已重启（如果刚配置）

❌ **某些运营商屏蔽 8080 端口？**：
尝试换成 9090：
1. 修改 `web_dashboard.py` 最后一行：`port=9090`
2. 修改路由器端口转发：外部端口改成 9090
3. 重启 Flask 服务器
4. 告诉朋友新地址：`http://公网IP:9090`

---

## 方案 4：Ngrok 内网穿透（无路由器控制权）⭐ 推荐

### 为什么选择 Ngrok？
- ✅ **无需路由器配置** - 楼下路由器也没关系
- ✅ **5 分钟搞定** - 最快速的解决方案
- ✅ **自动 HTTPS** - 密码传输更安全
- ✅ **免费版够用** - 10-20 个朋友完全没问题

### 安装步骤

#### 1. 安装 Ngrok
```bash
brew install ngrok
```

#### 2. 注册账号（免费）
1. 访问 https://dashboard.ngrok.com/signup
2. 用 Google 或 GitHub 账号登录
3. 登录后会看到你的 **Authtoken**

#### 3. 配置 Authtoken
```bash
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
```

例如：
```bash
ngrok config add-authtoken 2abcdefGHIJKLMN1234567890
```

### 启动服务

#### 终端 1：启动 Flask
```bash
cd /Users/hostsjim/StockItsMygo
source venv/bin/activate
python web_dashboard.py
```

保持这个终端运行！

#### 终端 2：启动 Ngrok
打开新终端窗口：
```bash
ngrok http 8080
```

会显示类似：
```
ngrok

Forwarding   https://abc123def456.ngrok.io -> http://localhost:8080
```

**关键信息**：`https://abc123def456.ngrok.io` ← 这就是你的公网地址！

### 分享给朋友

```
🎯 股票推荐系统 - 测试邀请

访问地址：https://abc123def456.ngrok.io
邀请码：stocktest2026

注意：
1. 必须使用 HTTPS（不是 HTTP）
2. 第一次访问可能看到 ngrok 警告页面，点击 "Visit Site" 继续
```

### 测试访问

**本地测试**：
```bash
# Mac 浏览器
https://abc123def456.ngrok.io
```

**手机测试**：
```bash
# 用手机（WiFi 或 4G 都可以）
https://abc123def456.ngrok.io
```

**监控面板**：
```bash
# 打开这个地址查看所有请求
http://127.0.0.1:4040
```

### 保持服务持续运行

#### 方法 1：使用 Screen（推荐）
```bash
# 创建 Flask session
screen -S flask
cd /Users/hostsjim/StockItsMygo
source venv/bin/activate
python web_dashboard.py
# 按 Ctrl+A 然后 D 分离

# 创建 Ngrok session
screen -S ngrok
ngrok http 8080
# 按 Ctrl+A 然后 D 分离

# 查看所有 screen
screen -ls

# 重新连接
screen -r flask
screen -r ngrok
```

#### 方法 2：自动启动脚本
创建 `start_server.sh`：
```bash
#!/bin/bash
cd /Users/hostsjim/StockItsMygo
source venv/bin/activate
python web_dashboard.py > flask.log 2>&1 &
sleep 3
ngrok http 8080 > ngrok.log 2>&1 &
echo "✓ 服务已启动"
```

使用：
```bash
chmod +x start_server.sh
./start_server.sh
```

### Ngrok 常见问题

**Q: 每次重启域名会变吗？**
A: 是的，免费版每次重启域名会变。付费版（$8/月）可以固定域名。

**Q: 如何查看当前 Ngrok URL？**
A:
```bash
curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'
```
或访问 http://127.0.0.1:4040

**Q: 朋友说访问很慢怎么办？**
A: Ngrok 免费版可能有延迟。可以：
1. 使用付费版（更快的服务器）
2. 换用 Cloudflare Tunnel（需要域名）

**Q: Mac 休眠后 Ngrok 断开了**
A:
- 系统偏好设置 → 节能 → 防止电脑自动睡眠
- 或使用 `caffeinate -s ngrok http 8080`

### 免费版限制
- ✅ 带宽：无限制
- ✅ 请求数：无限制
- ✅ 连接数：40 个/分钟（够用）
- ⚠️ 域名：随机，每次重启会变
- ⚠️ 同时 tunnel：1 个

**对于 10-20 个朋友完全够用！**

---

## 方案 5：Cloudflare Tunnel（高级，需要域名）

如果你有自己的域名（如 `example.com`），可以用 Cloudflare Tunnel（完全免费）：

```bash
# 安装
brew install cloudflare/cloudflare/cloudflared

# 登录
cloudflared tunnel login

# 创建 tunnel
cloudflared tunnel create stockdash

# 配置 DNS
cloudflared tunnel route dns stockdash stocks.example.com

# 运行
cloudflared tunnel run --url http://localhost:8080 stockdash
```

朋友访问：`https://stocks.example.com`

**优点**：
- 完全免费
- 固定域名
- 无限制
- 中国大陆也快

---

## Mac 作为服务器的注意事项

### 防止 Mac 休眠
**系统偏好设置** → **节能** → **防止电脑自动进入睡眠**（接通电源时）

或使用命令：
```bash
caffeinate -s python web_dashboard.py
```

### 监控资源使用
打开 **活动监视器**，查找 **Python** 进程：
- **CPU**: 正常情况下 < 5%（无请求时接近 0%）
- **内存**: 通常 100-300 MB
- **网络**: 有朋友访问时会有流量

### 查看 Flask 日志
```bash
# 如果用 nohup 启动
tail -f flask_server.log

# 如果用 screen 启动
screen -r flask
```

---

## 安全提示

1. **不要把 URL 发到公开论坛** - 只分享给朋友
2. **邀请码保密** - 防止陌生人注册
3. **定期检查用户列表** - 看看有没有可疑账号
4. **如果 URL 泄露**：
   - 端口转发：更换端口
   - Ngrok：重启会得到新 URL

---

## 推荐方案总结

| 场景 | 推荐方案 | 原因 |
|------|----------|------|
| 只有自己用 | 本地访问 | 最简单 |
| 朋友来家里 | 局域网访问 | 无需配置 |
| 有路由器控制权 | 端口转发 | 稳定、免费 |
| **无路由器控制权** | **Ngrok** ⭐ | 5 分钟搞定 |
| 有域名 | Cloudflare Tunnel | 最专业 |

---

*最后更新：2026-01-06*
*推荐方案：Ngrok（无路由器控制权时）*
