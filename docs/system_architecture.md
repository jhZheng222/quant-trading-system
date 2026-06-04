# 量化交易系统完整架构

## 系统概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            量化交易系统 v2.0                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐               │
│  │  数据服务    │      │  策略优化    │      │  模拟交易    │               │
│  │ (WebSocket)  │ ───▶ │ (Backtest)   │ ───▶ │ (Simulation) │               │
│  └──────────────┘      └──────────────┘      └──────────────┘               │
│         │                                                            ┌───────┤
│         │            ┌──────────────┐      ┌──────────────┐          │       │
│         └───────────▶│  实时引擎    │ ───▶ │  风控系统    │◀─────────┤       │
│                      │ (Live Trade) │      │ (Risk Mgmt)  │          │       │
│                      └──────────────┘      └──────────────┘          │       │
│                                                                      │       │
│  ┌───────────────────────────────────────────────────────────────────┘       │
│  │  CLI 管理工具                                                             │
│  └───────────────────────────────────────────────────────────────────────────│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 组件说明

### 1. 数据服务 (WebSocket Forwarder)
- **位置**: `core/data/websocket_service.py`
- **管理**: `data_service.py`
- **功能**: 
  - 连接币安WebSocket获取实时数据
  - 转发给多个客户端（模拟/实盘/监控）
  - 缓存历史K线数据

### 2. 策略优化器 (Backtest Engine)
- **位置**: `core/backtest/engine.py`, `core/optimization/strategy_optimizer.py`
- **功能**:
  - 使用历史数据回测策略
  - 网格搜索最优参数
  - 生成优化报告

### 3. 配置管理 (Strategy Config)
- **位置**: `core/config/strategy_config.py`
- **功能**:
  - 保存/加载策略参数
  - 管理多套配置
  - 导出/导入配置

### 4. 模拟交易 (Simulated Trader)
- **位置**: `core/config/strategy_config.py`
- **功能**:
  - 使用优化参数进行模拟
  - 记录交易历史
  - 计算风险指标

### 5. 实时引擎 (Realtime Engine v2)
- **位置**: `core/realtime/engine_v2.py`
- **管理**: `engine_manager.py`
- **功能**:
  - 从数据服务获取实时数据
  - 生成交易信号
  - 执行模拟/实盘交易

### 6. CLI 管理工具
- **位置**: `cli.py`
- **功能**:
  - 统一管理入口
  - 查看系统状态
  - 执行各种操作

## 使用流程

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 检查配置
python cli.py configs
```

### 2. 策略优化

```bash
# 运行回测
python cli.py backtest --symbol DOGEUSDT --days 30

# 参数优化并保存
python cli.py optimize --symbol DOGEUSDT --days 30 --save

# 查看优化结果
python cli.py configs
```

### 3. 模拟交易

```bash
# 启动数据服务
python data_service.py start

# 启动模拟交易
python engine_manager.py start

# 查看状态
python cli.py engine
python cli.py simulate --config optimized_DOGEUSDT_30d
```

### 4. 实盘交易

```bash
# 启动数据服务
python data_service.py start

# 启动实盘交易
python engine_manager.py start --live

# 查看状态
python cli.py engine
```

## CLI 命令大全

### 账户管理
```bash
python cli.py status              # 查看账户状态
python cli.py positions           # 查看当前持仓
python cli.py positions --live    # 查看持仓（实时盈亏）
python cli.py history             # 查看交易历史
python cli.py export              # 导出交易记录
python cli.py risk                # 查看风控状态
python cli.py signals             # 查看最新信号
```

### 策略管理
```bash
python cli.py backtest            # 运行策略回测
python cli.py optimize            # 参数优化
python cli.py optimize --save     # 参数优化并保存
python cli.py configs             # 查看策略配置
```

### 模拟交易
```bash
python cli.py simulate            # 模拟交易状态
python cli.py simulate --trades   # 模拟交易历史
python cli.py simulate --export   # 导出模拟报告
python cli.py simulate --reset    # 重置模拟状态
```

### 系统管理
```bash
python cli.py data-service        # 数据服务状态
python cli.py engine              # 实时引擎状态
```

### 独立管理脚本
```bash
# 数据服务
python data_service.py start      # 启动服务
python data_service.py stop       # 停止服务
python data_service.py status     # 查看状态
python data_service.py test       # 测试连接
python data_service.py config     # 修改配置

# 实时引擎
python engine_manager.py start          # 启动模拟交易
python engine_manager.py start --live   # 启动实盘交易
python engine_manager.py stop           # 停止引擎
python engine_manager.py status         # 查看状态
python engine_manager.py config         # 修改配置
```

## 配置文件

### 数据服务配置
**位置**: `config/data_service.json`
```json
{
  "symbols": ["DOGEUSDT", "PEPEUSDT"],
  "intervals": ["1h", "15m"],
  "host": "localhost",
  "port": 8765
}
```

### 实时引擎配置
**位置**: `config/engine_config.json`
```json
{
  "config_name": "optimized_DOGEUSDT_30d",
  "mode": "simulation",
  "data_url": "ws://localhost:8765"
}
```

### 策略参数配置
**位置**: `config/strategy_params.json`
```json
{
  "optimized_DOGEUSDT_30d": {
    "params": {
      "stop_loss_pct": 0.05,
      "take_profit_pct": 0.08,
      "buy_threshold": 65,
      "sell_threshold": 40,
      "position_size": 0.2
    },
    "description": "DOGEUSDT 30天优化结果",
    "created_at": "2026-06-03T22:36:32"
  }
}
```

## 部署建议

### 开发环境
```bash
# 终端1：启动数据服务
python data_service.py start

# 终端2：启动模拟交易
python engine_manager.py start

# 终端3：监控状态
watch -n 10 'python cli.py engine'
```

### 生产环境
```bash
# 使用systemd管理服务
sudo systemctl start quant-data
sudo systemctl start quant-engine

# 或使用Docker
docker-compose up -d
```

## 故障排除

### 1. 数据服务无法启动
```bash
# 检查端口占用
lsof -i :8765

# 检查币安API
curl https://data-api.binance.vision/api/v3/ticker/price?symbol=DOGEUSDT
```

### 2. 实时引擎无数据
```bash
# 检查数据服务状态
python data_service.py status

# 测试连接
python data_service.py test
```

### 3. 模拟交易无交易
```bash
# 检查策略参数
python cli.py configs

# 检查信号
python cli.py signals
```

## 性能优化

### 1. 减少API调用
- 使用WebSocket转发服务
- 缓存历史数据
- 合理设置K线周期

### 2. 优化策略
- 定期重新优化参数
- 使用多时间框架分析
- 结合多种指标

### 3. 风险控制
- 设置合理止损
- 控制仓位比例
- 监控最大回撤
