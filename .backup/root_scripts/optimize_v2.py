#!/usr/bin/env python3
"""
策略优化测试脚本
使用优化版参数优化器
"""

import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
from core.storage.sqlite_storage import SQLiteStorage
from core.backtest.optimizer_v2 import ParameterOptimizerV2

print("=" * 60)
print("🚀 开始策略优化")
print("=" * 60)
print()

# 初始化
db = SQLiteStorage("data/trading.db")
optimizer = ParameterOptimizerV2(db)

# 运行随机搜索
symbol = "PEPEUSDT"
days = 30
n_iter = 50

print(f"📊 交易对: {symbol}")
print(f"📅 回测天数: {days}")
print(f"🔄 迭代次数: {n_iter}")
print()

# 运行优化
results = optimizer.random_search(symbol, days, n_iter)

# 打印优化报告
print(optimizer.get_optimization_report())

# 保存结果
optimizer.save_results()

print()
print("✅ 优化完成！")