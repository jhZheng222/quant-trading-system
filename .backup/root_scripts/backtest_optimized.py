#!/usr/bin/env python3
"""
v3.0 策略回测测试（含优化版）
"""

import sys
import os
import json
import numpy as np
import pandas as pd
import httpx
from datetime import datetime, timedelta
from loguru import logger

sys.path.insert(0, os.path.dirname(__file__))

from core.strategies.ema_rsi_strategy import EMARsiStrategy
from core.strategies.ema_rsi_optimized import EMARsiOptimizedStrategy
from core.strategies.macd_strategy import MACDStrategy
from core.strategies.bollinger_strategy import BollingerStrategy
from core.strategies.livermore_strategy import LivermoreStrategy
from core.strategies.multi_strategy import MultiStrategy

STRATEGIES = {
    'ema_rsi': EMARsiStrategy,
    'ema_rsi_optimized': EMARsiOptimizedStrategy,
    'macd': MACDStrategy,
    'bollinger': BollingerStrategy,
    'livermore': LivermoreStrategy,
    'multi': MultiStrategy,
}

BINANCE_REST = "https://data-api.binance.vision"


def get_klines(symbol: str, interval: str = '1h', limit: int = 720) -> list:
    """从 Binance 获取 K 线数据"""
    url = f"{BINANCE_REST}/api/v3/klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    resp = httpx.get(url, params=params, timeout=15)
    data = resp.json()
    return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in data]


def run_backtest(strategy_name: str, symbol: str, klines: list, initial_balance: float = 10.0):
    """运行单个策略回测"""
    strategy_class = STRATEGIES.get(strategy_name)
    if not strategy_class:
        logger.error(f"未知策略: {strategy_name}")
        return None

    strategy = strategy_class()
    balance = initial_balance
    position = None
    trades = []
    equity_curve = []

    for i in range(50, len(klines)):
        current_klines = klines[:i+1]
        price = klines[i][4]
        ts = datetime.fromtimestamp(klines[i][0] / 1000)

        # 生成信号
        try:
            if strategy_name == 'ema_rsi_optimized':
                signal = strategy.generate_signal(symbol, current_klines, price, position)
            else:
                signal = strategy.generate_signal(symbol, current_klines, price)
        except Exception as e:
            continue

        if signal and signal.action == 'buy' and position is None:
            # 计算仓位（支持动态仓位）
            position_size_pct = signal.metadata.get('position_size', 0.2) if signal.metadata else 0.2
            leverage = strategy.params.get('leverage', 1) if hasattr(strategy, 'params') else 1
            
            size = balance * position_size_pct * leverage / price
            balance -= balance * position_size_pct
            position = {
                'entry_price': price, 
                'entry_time': ts, 
                'size': size,
                'added': False,
            }
            trades.append({'type': 'buy', 'price': price, 'time': ts, 'size': size})

        elif signal and signal.action == 'add_position' and position and not position.get('added'):
            # 浮盈加仓
            add_size = initial_balance * 0.1 / price  # 10%仓位加仓
            position['size'] += add_size
            position['added'] = True
            trades.append({'type': 'add', 'price': price, 'time': ts, 'size': add_size})

        elif signal and signal.action == 'sell' and position is not None:
            pnl = (price - position['entry_price']) * position['size']
            balance += position['size'] * price
            trades.append({'type': 'sell', 'price': price, 'time': ts, 'pnl': pnl})
            position = None

        total_value = balance + (position['size'] * price if position else 0)
        equity_curve.append({'time': ts, 'value': total_value})

    # 强制平仓
    if position:
        final_price = klines[-1][4]
        pnl = (final_price - position['entry_price']) * position['size']
        balance += position['size'] * final_price
        trades.append({'type': 'sell', 'price': final_price, 'time': datetime.now(), 'pnl': pnl})

    final_value = balance
    total_pnl = final_value - initial_balance
    total_return = total_pnl / initial_balance * 100

    sell_trades = [t for t in trades if t['type'] == 'sell']
    winning = [t for t in sell_trades if t.get('pnl', 0) > 0]
    losing = [t for t in sell_trades if t.get('pnl', 0) < 0]
    win_rate = len(winning) / max(1, len(sell_trades)) * 100
    avg_win = sum(t['pnl'] for t in winning) / max(1, len(winning))
    avg_loss = sum(t['pnl'] for t in losing) / max(1, len(losing))
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    max_equity = initial_balance
    max_drawdown = 0
    for pt in equity_curve:
        if pt['value'] > max_equity:
            max_equity = pt['value']
        dd = (max_equity - pt['value']) / max_equity * 100
        if dd > max_drawdown:
            max_drawdown = dd

    return {
        'strategy': strategy_name,
        'symbol': symbol,
        'initial': initial_balance,
        'final': round(final_value, 4),
        'pnl': round(total_pnl, 4),
        'return_pct': round(total_return, 2),
        'trades': len(sell_trades),
        'win_rate': round(win_rate, 1),
        'avg_win': round(avg_win, 4),
        'avg_loss': round(avg_loss, 4),
        'profit_factor': round(profit_factor, 2),
        'max_drawdown': round(max_drawdown, 2),
    }


def main():
    logger.info("🚀 v3.0 策略回测测试（含优化版）")
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

        # 只测3个策略：原版、优化版、multi
        test_strategies = ['ema_rsi', 'ema_rsi_optimized', 'multi']
        
        for name in test_strategies:
            logger.info(f"\n🧪 测试策略: {name} | {symbol}")
            result = run_backtest(name, symbol, klines)
            if result:
                all_results.append(result)
                logger.info(f"   ✅ 收益: {result['pnl']}U ({result['return_pct']}%) | 胜率: {result['win_rate']}% | 交易: {result['trades']}笔 | 回撤: {result['max_drawdown']}%")

    # 汇总对比
    logger.info("\n" + "=" * 70)
    logger.info("📋 回测对比（30天 1h K线 | 10U 本金）")
    logger.info("=" * 70)
    logger.info(f"{'策略':<20} {'币种':<12} {'收益(U)':<10} {'收益率%':<10} {'胜率%':<8} {'交易数':<8} {'回撤%':<8}")
    logger.info("-" * 80)
    for r in all_results:
        logger.info(f"{r['strategy']:<20} {r['symbol']:<12} {r['pnl']:<10} {r['return_pct']:<10} {r['win_rate']:<8} {r['trades']:<8} {r['max_drawdown']:<8}")

    # 计算优化提升
    logger.info("\n" + "=" * 70)
    logger.info("📈 优化效果对比")
    logger.info("=" * 70)
    
    for symbol in symbols:
        original = next((r for r in all_results if r['strategy'] == 'ema_rsi' and r['symbol'] == symbol), None)
        optimized = next((r for r in all_results if r['strategy'] == 'ema_rsi_optimized' and r['symbol'] == symbol), None)
        
        if original and optimized:
            pnl_diff = optimized['pnl'] - original['pnl']
            dd_diff = original['max_drawdown'] - optimized['max_drawdown']
            logger.info(f"\n{symbol}:")
            logger.info(f"  收益变化: {original['pnl']}U → {optimized['pnl']}U ({'↑' if pnl_diff > 0 else '↓'}{abs(pnl_diff):.2f}U)")
            logger.info(f"  回撤变化: {original['max_drawdown']}% → {optimized['max_drawdown']}% ({'↓' if dd_diff > 0 else '↑'}{abs(dd_diff):.2f}%)")

    # 保存
    os.makedirs('reports', exist_ok=True)
    report_path = f"reports/backtest_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    logger.info(f"\n📄 报告已保存: {report_path}")


if __name__ == "__main__":
    main()
