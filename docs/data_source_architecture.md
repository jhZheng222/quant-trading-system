# 数据源统一架构

## 概述

所有组件使用统一的数据服务层（DataService），避免重复API调用，保证数据一致性。

## 架构图

```
┌─────────────────────────────────────────────────────────┐
│                   统一数据源架构                          │
├─────────────────────────────────────────────────────────┤
│  data_manager.py (单例模式)                              │
│    ├── 币安 WebSocket (实时，30秒)                       │
│    ├── 币安 REST API (历史K线)                           │
│    └── SQLite 数据库 (持久化)                            │
│                                                         │
│  ├── get_ticker(symbol)      → 实时价格                 │
│  ├── get_history(symbol, 30) → 历史K线                  │
│  ├── get_latest_price(symbol) → 最新价格                │
│  └── get_symbols()           → 交易对列表               │
└─────────────────────────────────────────────────────────┘
```

## 组件接入状态

| 组件 | 数据源 | 状态 |
|------|--------|------|
| 实时引擎 | DataService | ✅ 已接入 |
| 回测引擎 v1 | DataService | ✅ 已接入 |
| 回测引擎 v2 | SQLiteStorage (数据库) | ✅ 已接入 |
| CLI 命令 | SQLiteStorage (数据库) | ✅ 已接入 |

## 数据流向

```
                    ┌─────────────────┐
                    │  币安 WebSocket  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   DataService   │
                    │   (单例模式)     │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───┐  ┌──────▼──────┐  ┌───▼────────┐
     │  实时引擎   │  │  策略回测   │  │  CLI 命令  │
     └────────────┘  └─────────────┘  └────────────┘
```

## 优势

1. **单一数据源** - 所有组件读取同一份数据
2. **避免重复API调用** - 节省API配额
3. **数据一致性** - 回测和实盘使用相同数据
4. **易于维护** - 数据逻辑集中管理

## 使用方式

```python
from core.data.service import DataService

# 获取单例
service = DataService.get_instance()

# 采集数据
service.collect_all_tickers()
service.collect_all_klines('1h', 100)

# 获取数据
ticker = service.get_latest_ticker('DOGEUSDT')
klines = service.get_latest_klines('DOGEUSDT', '1h')
```

## 测试

```bash
# 测试数据源统一
python -c "
from core.data.service import DataService
service = DataService.get_instance()
service.collect_all_tickers()
print('DOGEUSDT:', service.get_latest_ticker('DOGEUSDT'))
"

# 测试回测引擎
python -c "
from core.backtest.engine import BacktestEngine
engine = BacktestEngine()
result = engine.run_backtest('DOGEUSDT', days=7)
print('回测结果:', result)
"
```
