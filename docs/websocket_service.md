# WebSocket 数据转发服务架构

## 概述

独立的实时数据服务，支持多个客户端订阅，避免重复连接币安API。

## 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        WebSocket 数据转发服务                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐                                                    │
│  │   币安 API   │                                                    │
│  │  WebSocket   │                                                    │
│  └──────┬───────┘                                                    │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐       │
│  │  数据源      │ ───▶ │  转发服务    │ ───▶ │  客户端 A   │       │
│  │ (DataSource) │      │ (Forwarder)  │      │ (实盘策略)  │       │
│  └──────────────┘      └──────┬───────┘      └──────────────┘       │
│                               │                                      │
│                               │            ┌──────────────┐          │
│                               └───────────▶│  客户端 B   │          │
│                                            │ (模拟交易)  │          │
│                                            └──────────────┘          │
│                                                                      │
│                                            ┌──────────────┐          │
│                                            └───────────▶│  客户端 C   │
│                                                         │ (监控面板)  │
│                                                         └──────────────┘
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 组件说明

### 1. 数据源 (BinanceDataSource)
- 连接币安WebSocket
- 接收K线、Ticker、深度数据
- 缓存最近100根K线

### 2. 转发服务 (WebSocketForwarder)
- 监听本地端口（默认8765）
- 接收客户端连接
- 广播实时数据给所有客户端
- 新客户端连接时发送缓存数据

### 3. 数据客户端 (DataClient)
- 连接转发服务
- 接收实时数据
- 提供API给策略使用

## 优势

| 优势 | 说明 |
|------|------|
| **单一数据源** | 只有一个进程连接币安 |
| **多客户端** | 支持多个策略同时运行 |
| **数据一致** | 所有客户端获取相同数据 |
| **易于扩展** | 新策略只需连接转发服务 |
| **资源节省** | 避免重复API调用 |

## 使用方法

### 1. 启动数据服务

```bash
# 启动服务
python data_service.py start

# 查看状态
python data_service.py status

# 测试连接
python data_service.py test

# 修改配置
python data_service.py config
```

### 2. 客户端连接

```python
from core.data.websocket_service import DataClient

# 创建客户端
client = DataClient('ws://localhost:8765')

# 注册回调
def on_ticker(symbol, ticker):
    print(f"{symbol}: ${ticker['price']:.6f}")

client.on_ticker = on_ticker

# 启动
client.start()

# 获取数据
price = client.get_price('DOGEUSDT')
klines = client.get_klines('DOGEUSDT', '1h')
```

### 3. 配置文件

配置文件位置：`config/data_service.json`

```json
{
  "symbols": ["DOGEUSDT", "PEPEUSDT"],
  "intervals": ["1h", "15m"],
  "host": "localhost",
  "port": 8765
}
```

## CLI 命令

```bash
# 查看数据服务状态
python cli.py data-service

# 启动服务
python data_service.py start

# 停止服务
python data_service.py stop

# 测试连接
python data_service.py test
```

## 部署建议

### 开发环境
```bash
# 终端1：启动数据服务
python data_service.py start

# 终端2：运行实盘策略
python cli.py simulate --config optimized_DOGEUSDT_30d

# 终端3：运行监控
python cli.py data-service
```

### 生产环境
```bash
# 使用systemd或launchd管理服务
# 创建服务文件：/etc/systemd/system/quant-data.service

[Unit]
Description=Quant Data Service
After=network.target

[Service]
Type=simple
User=zhengxiaoyu
WorkingDirectory=/Users/zhengxiaoyu/quant-trading-system
ExecStart=/Users/zhengxiaoyu/quant-trading-system/venv/bin/python data_service.py start
Restart=always

[Install]
WantedBy=multi-user.target
```

## 故障排除

### 1. 无法连接
```bash
# 检查服务是否启动
python data_service.py status

# 测试连接
python data_service.py test
```

### 2. 无数据
```bash
# 检查币安API是否可访问
curl https://data-api.binance.vision/api/v3/ticker/price?symbol=DOGEUSDT

# 检查防火墙
# 确保端口8765未被占用
lsof -i :8765
```

### 3. 数据延迟
- 检查网络连接
- 减少订阅的交易对数量
- 增加K线周期（如从1m改为5m）
