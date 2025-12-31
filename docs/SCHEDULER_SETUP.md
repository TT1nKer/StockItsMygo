# Windows任务计划调度器设置指南

本指南将帮助您设置Windows任务计划程序，每天自动运行股票数据更新。

## 📋 前提条件

1. Python 3.x 已安装并在PATH中
2. 项目位于 `d:\strategy=Z`
3. 所有依赖已安装 (`pip install -r requirements.txt`)
4. 数据库已初始化

## 🚀 快速设置（5分钟）

### 步骤 1: 创建日志目录

打开命令提示符，运行：

```batch
cd d:\strategy=Z
mkdir logs
```

### 步骤 2: 测试批处理文件

首先手动测试批处理文件是否正常工作：

```batch
cd d:\strategy=Z
tools\setup_scheduler.bat
```

这将运行一次完整的每日更新流程（约25-30分钟）。检查：
- 是否有错误输出
- `logs` 目录中是否生成了日志文件
- `docs/reports` 目录中是否生成了报告

### 步骤 3: 打开任务计划程序

按 `Win + R`，输入 `taskschd.msc`，点击"确定"

### 步骤 4: 创建新任务

1. 在右侧面板点击 **"创建基本任务..."**

2. **任务名称和描述**
   - 名称: `Stock Market Daily Update`
   - 描述: `每日更新股票数据、分析观察列表、生成报告`
   - 点击"下一步"

3. **触发器设置**
   - 选择: **"每天"**
   - 点击"下一步"

4. **每天触发时间**
   - 开始时间: **17:30** (美股收盘后，美东时间 16:00 + 1.5小时缓冲)
   - 每隔: **1 天**
   - 点击"下一步"

5. **操作类型**
   - 选择: **"启动程序"**
   - 点击"下一步"

6. **启动程序设置**
   - 程序或脚本: `d:\strategy=Z\tools\setup_scheduler.bat`
   - 添加参数: (留空)
   - 起始于: `d:\strategy=Z`
   - 点击"下一步"

7. **完成**
   - 勾选 ☑ **"当单击'完成'时，打开此任务属性的对话框"**
   - 点击"完成"

### 步骤 5: 高级设置

在任务属性对话框中：

#### **常规选项卡**
- ☑ 使用最高权限运行
- 配置: **Windows 10** (或您的Windows版本)

#### **触发器选项卡**
- 双击触发器，点击"高级设置"
- ☑ 启用
- ☐ 如果任务运行时间超过以下时间则停止: **1 小时**
- 勾选: ☑ 已启用

#### **条件选项卡**
- 电源:
  - ☐ 只有在计算机使用交流电源时才启动此任务 (取消勾选，允许笔记本电池模式运行)
  - ☐ 如果计算机改用电池电源，则停止 (取消勾选)

#### **设置选项卡**
- ☑ 允许按需运行任务
- ☑ 如果过了计划开始时间，立即启动任务
- 如果任务失败，重新启动间隔: **10 分钟**
- 尝试重新启动次数: **3 次**
- 如果任务已运行，则强行停止: **2 小时**

点击"确定"保存所有设置。

## 🧪 测试任务

### 手动运行测试

1. 在任务计划程序库中找到 `Stock Market Daily Update`
2. 右键点击 → **运行**
3. 观察"上次运行结果"列，应显示 `0x0` (成功)

### 检查日志

打开日志文件查看执行详情：

```batch
notepad d:\strategy=Z\logs\daily_update_20251229.log
```

### 检查报告

打开生成的报告：

```batch
notepad d:\strategy=Z\docs\reports\daily_report_2025-12-29.md
```

## 📅 调度时间建议

### 推荐时间: 每天 17:30 (本地时间)

假设您在美东时区 (EST/EDT):
- 美股收盘: 16:00 EST
- 数据更新延迟: ~15-20分钟
- 开始执行: 16:30 EST (17:30 如果您在中部/山地/太平洋时区)
- 执行时长: ~25-30分钟
- 完成时间: 17:00-17:30 EST

### 其他时区调整

- **太平洋时间 (PST/PDT)**: 13:30 (美股收盘后1.5小时)
- **中部时间 (CST/CDT)**: 15:30
- **中国/亚洲 (GMT+8)**: 次日 05:30 (美股收盘后1.5小时)

## 📊 监控和维护

### 每日检查清单

1. **查看日志文件** (`logs` 目录)
   - 是否有ERROR或FAILED消息
   - 各步骤是否正常完成

2. **查看报告** (`docs/reports` 目录)
   - 报告是否生成
   - 数据更新统计是否合理

3. **检查观察列表** (可选)
   ```python
   python -c "from script.watchlist import WatchlistManager; WatchlistManager().print_summary()"
   ```

### 每周维护

- **清理旧日志** (保留最近30天)
  ```batch
  forfiles /p "d:\strategy=Z\logs" /s /m *.log /d -30 /c "cmd /c del @path"
  ```

- **检查数据库大小**
  ```batch
  dir d:\strategy=Z\db\stock.db
  ```

### 故障排除

#### 问题1: 任务未执行

**可能原因**:
- 计算机关闭或休眠
- 触发器设置错误

**解决方案**:
- 确保计算机在触发时间开机
- 检查触发器设置，确认"已启用"勾选

#### 问题2: 任务执行失败

**检查步骤**:
1. 查看最新日志文件
2. 手动运行批处理文件测试
   ```batch
   cd d:\strategy=Z
   tools\setup_scheduler.bat
   ```
3. 检查Python环境和依赖

**常见错误**:
- `ModuleNotFoundError`: 依赖未安装，运行 `pip install -r requirements.txt`
- `PermissionError`: 以管理员权限运行
- `ConnectionError`: 网络问题，检查网络连接

#### 问题3: 执行时间过长

**优化建议**:
- 减少扫描的股票数量
- 调整workers数量
- 仅更新观察列表的分钟数据

## 🔔 高级配置

### 仅工作日运行

如果只想在工作日（周一至周五）运行：

1. 打开任务属性 → **触发器**选项卡
2. 双击触发器 → **高级设置**
3. 勾选: ☑ **延迟任务时间（随机）**: 最多 **1 小时** (可选)
4. 在"重复任务间隔"中不勾选"无限期"
5. 使用PowerShell脚本判断工作日:

创建 `tools\run_on_weekdays.bat`:

```batch
@echo off
REM 仅工作日运行
powershell -Command "if ((Get-Date).DayOfWeek -in 1..5) { d:\strategy=Z\tools\setup_scheduler.bat }"
```

然后在任务计划中使用此批处理文件。

### 邮件通知（可选）

在 `tools\daily_update.py` 末尾添加邮件发送代码（需要配置SMTP服务器）:

```python
import smtplib
from email.mime.text import MIMEText

def send_email_report(report_path):
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    msg = MIMEText(content, 'plain', 'utf-8')
    msg['Subject'] = f'Stock Market Daily Report - {datetime.now().strftime("%Y-%m-%d")}'
    msg['From'] = 'your_email@example.com'
    msg['To'] = 'recipient@example.com'

    # 配置SMTP服务器
    server = smtplib.SMTP('smtp.example.com', 587)
    server.starttls()
    server.login('your_email@example.com', 'your_password')
    server.send_message(msg)
    server.quit()

# 在报告生成后调用
send_email_report(report_path)
```

## ✅ 验证清单

完成设置后，确认以下各项：

- ☑ 批处理文件手动运行成功
- ☑ 日志目录已创建
- ☑ 报告目录已创建
- ☑ 任务计划已创建并启用
- ☑ 触发器时间正确
- ☑ 高级设置已配置
- ☑ 手动运行任务成功
- ☑ 日志文件正确生成
- ☑ 报告文件正确生成

## 📞 支持

如有问题，请检查：
1. 项目 README.md
2. 日志文件 (`logs` 目录)
3. GitHub Issues

---

**最后更新**: 2025-12-29
**文档版本**: 1.0
