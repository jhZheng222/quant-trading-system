#!/usr/bin/env python3
"""
v3.0 策略回测测试
================

使用历史数据测试所有策略。

用法：
    python backtest_test.py                    # 测试所有策略
    python backtest_test.py --strategy ema_rsi # 测试指定策略
    python backtest_test.py --symbol DOGEUSDT  # 测试指定币种
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta
from loguru import logger

# 确保项目路径在sys.path中
sys.path.insert(0, os.path.dirname(__file__))

from core.data_manager import DataManager
from core.strategy.engine import TrendStrategy
from core.strategy.livermore import LivermoreStrategy
from core.strategy.multi_strategy import MultiStrategy

STRATEGIES = {
    'ema_rsi': TrendStrategy,
    'livermore': LivermoreStrategy,
    'multi': MultiStrategy,
}


def get_historical_data(symbol: str, days: int = 30) -> pd.DataFrame:
    """获取历史数据"""
    dm = DataManager()
    history = dm.get_history(symbol, days)
    
    if not history:
        logger.error(f"无法获取 {symbol} 的历史数据")
        return None
    
    # 转换为DataFrame
    df = pd.DataFrame(history, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    return df


def run_backtest(strategy_name: str, symbol: str, days: int = 30, initial_balance: float = 10.0):
    """运行回测"""
    logger.info(f"{'='*50}")
    logger.info(f"📊 回测开始 | 策略: {strategy_name} | 币种: {symbol}")
    logger.info(f"{'='*50}")
    
    # 1. 获取历史数据
    df = get_historical_data(symbol, days)
    if df is None:
        return None
    
    logger.info(f"📈 历史数据: {len(df)} 根K线 | {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")
    
    # 2. 创建策略实例
    strategy_class = STRATEGIES.get(strategy_name)
    if not strategy_class:
        logger.error(f"未知策略: {strategy_name}")
        return None
    
    strategy = strategy_class()
    
    # 3. 模拟交易
    balance = initial_balance
    position = None
    trades = []
    equity_curve = []
    
    for i in range(50, len(df)):  # 从第50根K线开始（需要足够数据计算指标）
        # 获取当前K线数据
        current_klines = df.iloc[:i+1].values.tolist()
        current_price = df.iloc[i]['close']
        current_time = df.iloc[i]['timestamp']
        
        # 生成信号
        if strategy_name == 'livermore':
            signal = strategy.generate_signal(symbol, current_price, position)
        elif strategy_name == 'multi':
            signal = strategy.generate_signal(symbol, current_klines, position)
        else:
            signal = strategy.generate_signal(symbol, current_klines)
        
        # 执行交易
        if signal and signal['action'] == 'buy' and position is None:
            # 开仓
            position = {
                'symbol': symbol,
                'entry_price': current_price,
                'entry_time': current_time,
                'size': balance * 0.9 / current_price,  # 90%资金
            }
            balance *= 0.1  # 保留10%现金
            trades.append({
                'type': 'buy',
                'price': current_price,
                'time': current_time,
                'size': position['size'],
            })
            
        elif signal and signal['action'] == 'sell' and position is not None:
            # 平仓
            pnl = (current_price - position['entry_price']) * position['size']
            balance += position['size'] * current_price
            trades.append({
                'type': 'sell',
                'price': current_price,
                'time': current_time,
                'pnl': pnl,
            })
            position = None
        
        # 记录权益曲线
        total_value = balance
        if position:
            total_value += position['size'] * current_price
        equity_curve.append({
            'time': current_time,
            'value': total_value,
        })
    
    # 4. 计算统计
    if position:
        # 强制平仓
        final_price = df.iloc[-1]['close']
        pnl = (final_price - position['entry_price']) * position['size']
        balance += position['size'] * final_price
        trades.append({
            'type': 'sell',
            'price': final_price,
            'time': df.iloc[-1]['timestamp'],
            'pnl': pnl,
        })
    
    final_value = balance
    total_pnl = final_value - initial_balance
    total_return = total_pnl / initial_balance * 100
    
    winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
    losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
    win_rate = len(winning_trades) / max(1, len([t for t in trades if t['type'] == 'sell'])) * 100
    
    avg_win = sum(t['pnl'] for t in winning_trades) / max(1, len(winning_trades))
    avg_loss = sum(t['pnl'] for t in losing_trades) / max(1, len(losing_trades))
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
    
    # 最大回撤
    max_equity = initial_value
    max_drawdown = 0
    for point in equity_curve:
        if point['value'] > max_equity:
            max_equity = point['value']
        drawdown = (max_equity - point['value']) / max_equity * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # 5. 输出结果
    logger.info(f"\n{'='*50}")
    logger.info(f"📊 回测结果 | {strategy_name} | {symbol}")
    logger.info(f"{'='*50}")
    logger.info(f"💰 初始资金: {initial_balance:.2f} USDT")
    logger.info(f"💰 最终资金: {final_value:.2f} USDT")
    logger.info(f"📈 总收益: {total_pnl:.2f} USDT ({total_return:.2f}%)")
    logger.info(f"📊 总交易: {len([t for t in trades if t['type'] == 'sell'])} 笔")
    logger.info(f"✅ 胜率: {win_rate:.1f}%")
    logger.info(f"📉 最大回撤: {max_drawdown:.2f}%")
    logger.info(f"📊 盈亏比: {profit_factor:.2f}")
    logger.info(f"{'='*50}\n")
    
    return {
        'strategy': strategy_name,
        'symbol': symbol,
        'days': days,
        'initial_balance': initial_balance,
        'final_value': final_value,
        'total_pnl': total_pnl,
        'total_return': total_return,
        'total_trades': len([t for t in trades if t['type'] == 'sell']),
        'win_rate': win_rate,
        'max_drawdown': max_drawdown,
        'profit_factor': profit_factor,
    }


def main():
    parser = argparse.ArgumentParser(description='v3.0 策略回测测试')
    parser.add_argument('--strategy', default='ema_rsi', help='策略名称')
    parser.add_argument('--symbol', default='DOGEUSDT', help='交易对')
    parser.add_argument('--days', type=int, default=30, help='回测天数')
    parser.add_argument('--balance', type=float, default=10.0, help='初始资金')
    
    args = parser.parse_args()
    
    # 检查策略是否存在
    if args.strategy not in STRATEGIES:
        logger.error(f"未知策略: {args.strategy}，可用: {list(STRATEGIES.keys())}")
        return
    
    # 运行回测
    result = run_backtest(args.strategy, args.symbol, args.days, args.balance)
    
    if result:
        # 保存结果
        report_path = f"reports/backtest_{args.strategy}_{args.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 回测报告已保存: {report_path}")


if __name__ == "__main__":
    main()
