#!/usr/bin/env python3
"""
v3.0 策略回测测试（含优化版）- 修复版
"""

import sys
import os
import json
import httpx
from datetime import datetime
from loguru import logger

sys.path.insert(0, os.path.dirname(__file__))

from core.strategies.ema_rsi_strategy import EMARsiStrategy
from core.strategies.ema_rsi_optimized import EMARsiOptimizedStrategy
from core.strategies.multi_strategy import MultiStrategy

STRATEGIES = {
    'ema_rsi': EMARsiStrategy,
    'ema_rsi_optimized': EMARsiOptimizedStrategy,
    'multi': MultiStrategy,
}

BINANCE_REST = "https://data-api.binance.vision"


def get_klines(symbol: str, interval: str = '1h', limit: int = 720) -> list:
    url = f"{BINANCE_REST}/api/v3/klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    resp = httpx.get(url, params=params, timeout=15)
    data = resp.json()
    return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in data]


def run_backtest(strategy_name: str, symbol: str, klines: list, initial_balance: float = 10.0):
    """运行回测（简化版，避免仓位计算bug）"""
    strategy_class = STRATEGIES.get(strategy_name)
    if not strategy_class:
        return None

    strategy = strategy_class()
    
    # 简化模拟：只记录信号，不模拟复杂仓位
    signals = []
    
    for i in range(50, len(klines)):
        current_klines = klines[:i+1]
        price = klines[i][4]
        ts = datetime.fromtimestamp(klines[i][0] / 1000)

        try:
            if strategy_name == 'ema_rsi_optimized':
                # 模拟持仓状态
                position = None
                if signals and signals[-1]['action'] == 'buy':
                    position = {'entry_price': signals[-1]['price'], 'size': 1.0}
                signal = strategy.generate_signal(symbol, current_klines, price, position)
            else:
                signal = strategy.generate_signal(symbol, current_klines, price)
                
            if signal and signal.action in ['buy', 'sell']:
                signals.append({
                    'action': signal.action,
                    'price': price,
                    'time': ts,
                    'score': signal.score,
                    'reason': signal.reason,
                })
        except Exception as e:
            continue

    # 统计信号
    buy_signals = [s for s in signals if s['action'] == 'buy']
    sell_signals = [s for s in signals if s['action'] == 'sell']
    
    # 简化盈亏计算：假设每次买入后卖出
    trades = min(len(buy_signals), len(sell_signals))
    winning = 0
    total_pnl = 0
    
    for j in range(trades):
        entry = buy_signals[j]['price']
        exit_price = sell_signals[j]['price']
        pnl_pct = (exit_price - entry) / entry
        total_pnl += pnl_pct * 100  # 假设10U仓位
        if pnl_pct > 0:
            winning += 1
    
    win_rate = winning / max(1, trades) * 100
    final_value = initial_balance + total_pnl
    total_return = total_pnl / initial_balance * 100

    return {
        'strategy': strategy_name,
        'symbol': symbol,
        'initial': initial_balance,
        'final': round(final_value, 4),
        'pnl': round(total_pnl, 4),
        'return_pct': round(total_return, 2),
        'trades': trades,
        'win_rate': round(win_rate, 1),
        'buy_signals': len(buy_signals),
        'sell_signals': len(sell_signals),
    }


def main():
    logger.info("🚀 v3.0 策略回测（信号统计版）")
    logger.info("=" * 70)

    symbols = ['DOGEUSDT', 'PEPEUSDT']
    all_results = []

    for symbol in symbols:
        logger.info(f"\n📊 获取 {symbol} 历史数据（30天 1h K线）...")
        try:
            klines = get_klines(symbol, '1h', 720)
            logger.info(f"   获取到 {len(klines)} 根K线")
        except Exception as e:
            logger.error(f"   获取失败: {e}")
            continue

        for name in STRATEGIES:
            logger.info(f"\n🧪 测试策略: {name} | {symbol}")
            result = run_backtest(name, symbol, klines)
            if result:
                all_results.append(result)
                logger.info(f"   ✅ 买入信号: {result['buy_signals']} | 卖出信号: {result['sell_signals']} | 配对交易: {result['trades']} | 胜率: {result['win_rate']}%")

    # 汇总
    logger.info("\n" + "=" * 70)
    logger.info("📋 信号统计对比（30天 1h K线）")
    logger.info("=" * 70)
    logger.info(f"{'策略':<20} {'币种':<12} {'买入':<8} {'卖出':<8} {'配对':<8} {'胜率%':<8}")
    logger.info("-" * 70)
    for r in all_results:
        logger.info(f"{r['strategy']:<20} {r['symbol']:<12} {r['buy_signals']:<8} {r['sell_signals']:<8} {r['trades']:<8} {r['win_rate']:<8}")

    # 保存
    os.makedirs('reports', exist_ok=True)
    report_path = f"reports/backtest_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    logger.info(f"\n📄 报告已保存: {report_path}")


if __name__ == "__main__":
    main()
