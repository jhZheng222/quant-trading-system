# 🚀 量化交易系统

基于Hermes Agent协作架构的加密货币量化交易系统，优先支持DOGE和PEPE合约交易。

## 📋 系统概述

### 核心特性
- ✅ 自动化交易（无需人工盯盘）
- ✅ 多Agent协作（投策、数聚、研发、镇岳）
- ✅ 国内可用（OKX交易所、本地部署）
- ✅ 激进型策略（50%回撤可接受）

### 技术栈
- **语言**：Python 3.10+
- **交易所**：OKX（欧易）
- **数据库**：SQLite（可扩展到PostgreSQL）
- **Web框架**：FastAPI
- **日志**：Loguru

## 🛠️ 安装部署

### 1. 环境准备
```bash
# 克隆项目
cd ~/quant-trading-system

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
vim .env
```

配置内容：
```env
# OKX API配置
OKX_API_KEY=your_api_key_here
OKX_SECRET_KEY=your_secret_key_here
OKX_PASSPHRASE=your_passphrase_here
OKX_SANDBOX=false

# 数据库配置
DATABASE_URL=sqlite:///data/trading.db

# 监控报警配置
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_id
WECOM_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key
```

### 3. 初始化数据库
```bash
python -m models.init_db
```

### 4. 启动系统
```bash
# 启动所有服务
./scripts/start.sh

# 查看服务状态
./scripts/status.sh

# 停止所有服务
./scripts/stop.sh
```

## 📊 系统架构

### 目录结构
```
quant-trading-system/
├── config/                 # 配置文件
│   ├── settings.py        # 全局配置
│   └── __init__.py
├── core/                  # 核心模块
│   ├── exchange/          # 交易所接口
│   │   ├── okx_rest.py   # OKX REST API
│   │   └── okx_ws.py     # OKX WebSocket
│   ├── data/              # 数据处理
│   ├── strategy/          # 策略引擎
│   └── monitor/           # 监控模块
├── models/                # 数据模型
│   ├── tables.py          # 数据库表结构
│   └── init_db.py         # 数据库初始化
├── utils/                 # 工具函数
├── tests/                 # 测试代码
├── scripts/               # 管理脚本
│   ├── start.sh           # 启动脚本
│   ├── stop.sh            # 停止脚本
│   └── status.sh          # 状态检查
├── logs/                  # 日志目录
├── data/                  # 数据目录
├── main.py                # 主入口
├── requirements.txt       # 依赖列表
└── .env.example           # 环境变量模板
```

### 服务组件
| 服务 | 功能 | 端口 |
|------|------|------|
| data_collector | 数据采集服务 | - |
| strategy_engine | 策略引擎 | - |
| trade_executor | 交易执行服务 | - |
| monitor_dashboard | 监控面板 | 8080 |

## 📈 交易策略

### 策略1：趋势跟踪（主策略）
- **标的**：DOGE、PEPE
- **时间框架**：4H/1D（DOGE）、1H/4H（PEPE）
- **入场**：EMA金叉 + RSI确认
- **出场**：EMA死叉 或 移动止盈
- **杠杆**：DOGE 5-10x / PEPE 3-5x

### 策略2：事件驱动（辅策略）
- **触发**：马斯克发推、链上大额转账、社交热度飙升
- **动作**：轻仓跟进（5%仓位）
- **风控**：严格止损、快进快出

### 风控规则
```
单笔最大亏损：总资金 5%
单日最大亏损：总资金 15%
单周最大亏损：总资金 30%
总仓位上限：80%（留20%现金应急）
杠杆上限：DOGE 10x / PEPE 5x
同向持仓上限：最多2个策略同向
```

## 🔧 API文档

### OKX REST API
```python
from core.exchange.okx_rest import OKXRestClient

client = OKXRestClient()

# 获取账户余额
balance = client.get_balance()

# 获取持仓信息
positions = client.get_positions()

# 获取K线数据
klines = client.get_klines('DOGE-USDT-SWAP', '1h', 100)

# 创建订单
order = client.create_order(
    symbol='DOGE-USDT-SWAP',
    side='buy',
    amount=1000,
    order_type='market',
    stop_loss=0.000003,
    take_profit=0.000004
)
```

### OKX WebSocket API
```python
import asyncio
from core.exchange.okx_ws import OKXWebSocket

async def main():
    ws = OKXWebSocket()
    
    # 注册回调
    async def on_ticker(data):
        for ticker in data.get('data', []):
            print(f"行情: {ticker['instId']} 最新价: {ticker['last']}")
    
    ws.on('tickers', on_ticker)
    
    # 连接并订阅
    await ws.connect()
    await ws.subscribe_ticker(['DOGE-USDT-SWAP', 'PEPE-USDT-SWAP'])
    
    # 监听
    await ws.listen()

asyncio.run(main())
```

## 📊 监控报警

### 监控指标
- **系统监控**：CPU、内存、磁盘、网络
- **应用监控**：服务状态、API连接、错误率
- **业务监控**：盈亏、持仓、杠杆、资金费率

### 报警渠道
- 飞书机器人（主要）
- 企业微信机器人（备用）
- 短信（紧急情况）
- 邮件（日报/周报）

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_okx_rest.py

# 运行带覆盖率的测试
pytest --cov=core tests/
```

### 模拟交易
```bash
# 启用模拟模式
export OKX_SANDBOX=true

# 启动系统
./scripts/start.sh
```

## 📝 日志管理

### 日志位置
```
logs/
├── trading.log           # 主日志
├── data_collector.log    # 数据采集日志
├── strategy_engine.log   # 策略引擎日志
├── trade_executor.log    # 交易执行日志
└── monitor_dashboard.log # 监控面板日志
```

### 日志级别
- **DEBUG**：调试信息
- **INFO**：正常操作
- **WARNING**：警告信息
- **ERROR**：错误信息
- **CRITICAL**：严重错误

## 🔒 安全建议

### API安全
- 使用环境变量存储API密钥
- 启用IP白名单
- 定期更换API密钥
- 使用只读权限的API（测试时）

### 系统安全
- 定期更新系统补丁
- 使用防火墙限制端口访问
- 启用登录审计
- 定期备份数据

### 交易安全
- 设置严格的风控规则
- 使用模拟盘测试策略
- 小资金实盘验证
- 定期检查持仓和订单

## 🚨 故障处理

### 常见问题

**1. API连接失败**
```bash
# 检查网络连接
curl https://www.okx.com/api/v5/public/time

# 检查API密钥
echo $OKX_API_KEY
```

**2. 服务启动失败**
```bash
# 查看日志
tail -f logs/data_collector.log

# 检查进程
ps aux | grep python

# 重启服务
./scripts/stop.sh
./scripts/start.sh
```

**3. 数据库错误**
```bash
# 检查数据库文件
ls -la data/trading.db

# 重新初始化数据库
python -m models.init_db
```

### 紧急处理
```bash
# 立即停止所有交易
./scripts/stop.sh

# 取消所有未成交订单
python -c "
from core.exchange.okx_rest import OKXRestClient
client = OKXRestClient()
for symbol in ['DOGE-USDT-SWAP', 'PEPE-USDT-SWAP']:
    orders = client.get_open_orders(symbol)
    for order in orders:
        client.cancel_order(symbol, order['id'])
"
```

## 📞 技术支持

### 文档
- [OKX API文档](https://www.okx.com/zh-hans/okx-api)
- [CCXT文档](https://docs.ccxt.com/)
- [FastAPI文档](https://fastapi.tiangolo.com/)

### 联系方式
- 项目负责人：小五
- 技术支持：研发团队
- 紧急联系：镇岳（运维）

## 📅 更新日志

### v1.0.0 (2026-05-30)
- ✅ 项目初始化
- ✅ OKX API封装
- ✅ 数据库设计
- ✅ 服务管理脚本
- ✅ 基础监控

---

**⚠️ 风险提示**：加密货币交易具有高风险，可能导致本金损失。请在充分了解风险后谨慎投资。