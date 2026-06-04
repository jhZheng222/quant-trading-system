#!/usr/bin/env python3
"""
量化交易系统 CLI 接口
====================

功能：
- 查看当前持仓（带实时盈亏）
- 查看交易历史
- 导出交易记录
- 查看账户状态
- 查看风控状态

用法：
    python cli.py status              # 查看账户状态
    python cli.py positions           # 查看当前持仓
    python cli.py positions --live    # 查看持仓（实时盈亏）
    python cli.py history             # 查看交易历史
    python cli.py history --limit 20  # 查看最近20条
    python cli.py export              # 导出CSV
    python cli.py risk                # 查看风控状态
    python cli.py signals             # 查看最新信号
"""

import sys
import os
import argparse
import sqlite3
import csv
from datetime import datetime
from typing import List, Dict, Optional, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ==================== 配置 ====================

DEFAULT_DB = os.path.join(os.path.dirname(__file__), "data", "trading.db")

SYMBOLS = {
    "DOGEUSDT": {"name": "DOGE", "precision": 6},
    "PEPEUSDT": {"name": "PEPE", "precision": 10},
}


# ==================== 工具函数 ====================

def get_current_prices() -> Dict[str, float]:
    """获取当前价格"""
    if not HAS_REQUESTS:
        return {}
    
    prices = {}
    for symbol in SYMBOLS:
        try:
            resp = requests.get(
                "https://data-api.binance.vision/api/v3/ticker/price",
                params={"symbol": symbol},
                timeout=10
            )
            prices[symbol] = float(resp.json()["price"])
        except:
            prices[symbol] = 0.0
    return prices


def get_db_connection(db_path: str = None) -> sqlite3.Connection:
    """获取数据库连接"""
    db_path = db_path or DEFAULT_DB
    if not os.path.exists(db_path):
        print(f"❌ 数据库不存在: {db_path}")
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def format_price(price: float, symbol: str = None) -> str:
    """格式化价格"""
    if price is None:
        return "0"
    if symbol and symbol in SYMBOLS:
        precision = SYMBOLS[symbol]["precision"]
        return f"{price:.{precision}f}"
    if price < 0.0001:
        return f"{price:.10f}"
    elif price < 0.01:
        return f"{price:.8f}"
    else:
        return f"{price:.6f}"


def format_pnl(pnl: float) -> str:
    """格式化盈亏"""
    if pnl > 0:
        return f"\033[32m+{pnl:.4f}U\033[0m"  # 绿色
    elif pnl < 0:
        return f"\033[31m{pnl:.4f}U\033[0m"    # 红色
    else:
        return f"{pnl:.4f}U"


def format_pnl_pct(pct: float) -> str:
    """格式化盈亏百分比"""
    if pct > 0:
        return f"\033[32m+{pct:.2f}%\033[0m"
    elif pct < 0:
        return f"\033[31m{pct:.2f}%\033[0m"
    else:
        return f"{pct:.2f}%"


# ==================== 核心功能 ====================

def show_status(db_path: str = None):
    """显示账户状态"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # 获取最新快照
    cursor.execute("""
        SELECT * FROM account_snapshots 
        ORDER BY timestamp DESC LIMIT 1
    """)
    snapshot = cursor.fetchone()
    
    if not snapshot:
        print("❌ 无账户快照数据")
        conn.close()
        return
    
    # 获取open trades统计
    cursor.execute("""
        SELECT 
            symbol,
            COUNT(*) as count,
            SUM(amount * entry_price / 10) as margin
        FROM trades 
        WHERE status = 'open'
        GROUP BY symbol
    """)
    positions = cursor.fetchall()
    
    # 获取今日交易统计
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning,
            SUM(pnl) as total_pnl
        FROM trades 
        WHERE status = 'closed' 
        AND exit_time LIKE ?
    """, (f"{today}%",))
    today_stats = cursor.fetchone()
    
    conn.close()
    
    # 输出
    print("=" * 60)
    print("📊 账户状态")
    print("=" * 60)
    
    print(f"\n💰 资金:")
    print(f"   余额: {snapshot['balance']:.4f}U")
    print(f"   总盈亏: {format_pnl(snapshot['total_pnl'])}")
    print(f"   总交易: {snapshot['total_trades']}笔")
    print(f"   胜率: {snapshot['winning_trades']}/{snapshot['total_trades']} = {snapshot['winning_trades']/max(1,snapshot['total_trades'])*100:.1f}%")
    
    print(f"\n📋 当前持仓:")
    if positions:
        total_margin = 0
        for pos in positions:
            margin = pos['margin'] or 0
            total_margin += margin
            print(f"   {pos['symbol']}: {pos['count']}笔, 保证金={margin:.4f}U")
        print(f"   总保证金: {total_margin:.4f}U")
    else:
        print("   无持仓")
    
    print(f"\n📅 今日统计:")
    if today_stats and today_stats['total'] > 0:
        print(f"   交易: {today_stats['total']}笔")
        print(f"   盈利: {today_stats['winning']}笔")
        print(f"   盈亏: {format_pnl(today_stats['total_pnl'] or 0)}")
    else:
        print("   无交易记录")
    
    print("=" * 60)


def show_positions(db_path: str = None, live: bool = False):
    """显示当前持仓"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, symbol, side, entry_price, amount, entry_time, 
               stop_loss, take_profit
        FROM trades 
        WHERE status = 'open'
        ORDER BY entry_time DESC
    """)
    positions = cursor.fetchall()
    conn.close()
    
    if not positions:
        print("📋 当前无持仓")
        return
    
    # 获取实时价格
    prices = {}
    if live:
        print("⏳ 获取实时价格...")
        prices = get_current_prices()
    
    # 输出
    print("=" * 80)
    print("📋 当前持仓")
    print("=" * 80)
    
    total_cost = 0
    total_pnl = 0
    
    print(f"\n{'ID':<5} {'币种':<12} {'方向':<6} {'开仓价':<14} {'数量':<15} {'保证金':<10}", end="")
    if live:
        print(f" {'当前价':<14} {'浮盈%':<10} {'浮盈U':<10}", end="")
    print()
    print("-" * 80)
    
    for pos in positions:
        symbol = pos['symbol']
        entry_price = pos['entry_price']
        amount = pos['amount']
        cost = amount * entry_price / 10  # 保证金 = 数量 * 价格 / 杠杆
        total_cost += cost
        
        print(f"{pos['id']:<5} {symbol:<12} {pos['side']:<6} {format_price(entry_price, symbol):<14} {amount:<15.2f} {cost:<10.4f}", end="")
        
        if live and symbol in prices:
            current_price = prices[symbol]
            if pos['side'] == 'buy':
                pnl_pct = (current_price - entry_price) / entry_price * 100
                pnl_u = (current_price - entry_price) * amount
            else:
                pnl_pct = (entry_price - current_price) / entry_price * 100
                pnl_u = (entry_price - current_price) * amount
            
            total_pnl += pnl_u
            print(f" {format_price(current_price, symbol):<14} {format_pnl_pct(pnl_pct):<20} {format_pnl(pnl_u):<20}", end="")
        
        print()
    
    print("-" * 80)
    print(f"总保证金: {total_cost:.4f}U", end="")
    if live:
        print(f"  总浮盈: {format_pnl(total_pnl)}", end="")
    print()
    print("=" * 80)


def show_history(db_path: str = None, limit: int = 20, symbol: str = None):
    """显示交易历史"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    query = """
        SELECT id, symbol, side, entry_price, exit_price, amount, 
               leverage, pnl, pnl_pct, entry_time, exit_time, reason, status
        FROM trades 
        WHERE status = 'closed'
    """
    params = []
    
    if symbol:
        query += " AND symbol = ?"
        params.append(symbol)
    
    query += " ORDER BY exit_time DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    trades = cursor.fetchall()
    conn.close()
    
    if not trades:
        print("📋 无交易历史")
        return
    
    # 输出
    print("=" * 100)
    print("📋 交易历史")
    print("=" * 100)
    
    total_pnl = 0
    winning = 0
    
    print(f"\n{'ID':<5} {'币种':<12} {'方向':<6} {'开仓价':<14} {'平仓价':<14} {'盈亏':<12} {'盈亏%':<10} {'原因':<15} {'平仓时间'}")
    print("-" * 100)
    
    for trade in trades:
        pnl = trade['pnl'] or 0
        total_pnl += pnl
        if pnl > 0:
            winning += 1
        
        exit_time = trade['exit_time'] or ''
        if exit_time:
            exit_time = exit_time[:19]  # 截取到秒
        
        print(f"{trade['id']:<5} {trade['symbol']:<12} {trade['side']:<6} "
              f"{format_price(trade['entry_price'], trade['symbol']):<14} "
              f"{format_price(trade['exit_price'], trade['symbol']):<14} "
              f"{format_pnl(pnl):<22} {format_pnl_pct(trade['pnl_pct'] or 0):<20} "
              f"{trade['reason'] or '':<15} {exit_time}")
    
    print("-" * 100)
    print(f"总计: {len(trades)}笔 | 盈利: {winning}笔 | 胜率: {winning/len(trades)*100:.1f}% | 总盈亏: {format_pnl(total_pnl)}")
    print("=" * 100)


def export_trades(db_path: str = None, output: str = None):
    """导出交易记录为CSV"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, symbol, side, entry_price, exit_price, amount, 
               leverage, pnl, pnl_pct, entry_time, exit_time, reason, status
        FROM trades 
        ORDER BY entry_time DESC
    """)
    trades = cursor.fetchall()
    conn.close()
    
    if not trades:
        print("❌ 无交易记录")
        return
    
    # 默认输出文件名
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"trades_export_{timestamp}.csv"
    
    # 写入CSV
    with open(output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'ID', '币种', '方向', '开仓价', '平仓价', '数量', 
            '杠杆', '盈亏', '盈亏%', '开仓时间', '平仓时间', '原因', '状态'
        ])
        
        for trade in trades:
            writer.writerow([
                trade['id'], trade['symbol'], trade['side'],
                trade['entry_price'], trade['exit_price'], trade['amount'],
                trade['leverage'], trade['pnl'], trade['pnl_pct'],
                trade['entry_time'], trade['exit_time'], trade['reason'], trade['status']
            ])
    
    print(f"✅ 已导出 {len(trades)} 条交易记录到: {output}")


def show_risk(db_path: str = None):
    """显示风控状态"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # 获取账户快照
    cursor.execute("SELECT * FROM account_snapshots ORDER BY timestamp DESC LIMIT 1")
    snapshot = cursor.fetchone()
    
    # 获取open trades
    cursor.execute("""
        SELECT symbol, side, SUM(amount * entry_price / 10) as margin
        FROM trades WHERE status = 'open'
        GROUP BY symbol, side
    """)
    positions = cursor.fetchall()
    
    # 获取今日亏损
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT SUM(pnl) as daily_pnl
        FROM trades 
        WHERE status = 'closed' AND exit_time LIKE ?
    """, (f"{today}%",))
    daily = cursor.fetchone()
    
    # 获取连续亏损
    cursor.execute("""
        SELECT pnl FROM trades 
        WHERE status = 'closed' 
        ORDER BY exit_time DESC 
        LIMIT 5
    """)
    recent_trades = cursor.fetchall()
    
    conn.close()
    
    if not snapshot:
        print("❌ 无账户数据")
        return
    
    # 计算风控指标
    balance = snapshot['balance']
    total_margin = sum(p['margin'] for p in positions) if positions else 0
    margin_ratio = total_margin / balance if balance > 0 else 0
    daily_pnl = daily['daily_pnl'] if daily and daily['daily_pnl'] else 0
    
    consecutive_losses = 0
    for trade in recent_trades:
        if trade['pnl'] and trade['pnl'] < 0:
            consecutive_losses += 1
        else:
            break
    
    # 输出
    print("=" * 60)
    print("🛡️ 风控状态")
    print("=" * 60)
    
    print(f"\n📊 资金状态:")
    print(f"   余额: {balance:.4f}U")
    print(f"   使用保证金: {total_margin:.4f}U")
    print(f"   保证金使用率: {margin_ratio*100:.1f}%", end="")
    if margin_ratio > 0.5:
        print(" \033[31m⚠️ 超过50%限制\033[0m")
    else:
        print(" ✅")
    
    print(f"\n📅 今日状态:")
    print(f"   今日盈亏: {format_pnl(daily_pnl)}", end="")
    if daily_pnl < -balance * 0.15:
        print(" \033[31m⚠️ 超过15%限制\033[0m")
    else:
        print(" ✅")
    
    print(f"\n⚡ 连续亏损:")
    print(f"   连续亏损次数: {consecutive_losses}", end="")
    if consecutive_losses >= 3:
        print(" \033[31m⚠️ 已触发暂停\033[0m")
    else:
        print(" ✅")
    
    print(f"\n📋 持仓限制:")
    print(f"   单币种最大仓位: 30%")
    print(f"   同方向最大敞口: 60%")
    print(f"   总保证金上限: 50%")
    
    print("=" * 60)


def show_signals(db_path: str = None, limit: int = 10):
    """显示最新信号"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT symbol, signal_type, price, confidence, reason, timestamp
        FROM signals 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    signals = cursor.fetchall()
    conn.close()
    
    if not signals:
        print("📋 无信号记录")
        return
    
    print("=" * 80)
    print("📡 最新信号")
    print("=" * 80)
    
    print(f"\n{'时间':<20} {'币种':<12} {'信号':<8} {'价格':<14} {'置信度':<10} {'原因'}")
    print("-" * 80)
    
    for sig in signals:
        timestamp = sig['timestamp'] or ''
        if timestamp:
            timestamp = timestamp[:19]
        
        signal_type = sig['signal_type']
        if signal_type == 'buy':
            signal_display = "\033[32m买入\033[0m"
        elif signal_type == 'sell':
            signal_display = "\033[31m卖出\033[0m"
        else:
            signal_display = "持有"
        
        print(f"{timestamp:<20} {sig['symbol']:<12} {signal_display:<18} "
              f"{format_price(sig['price'], sig['symbol']):<14} "
              f"{sig['confidence']:<10.2f} {sig['reason'] or ''}")
    
    print("=" * 80)


def run_optimization(db_path: str = None, symbol: str = 'DOGEUSDT', days: int = 30, top_n: int = 5, save: bool = False):
    """运行参数优化"""
    from core.optimization.strategy_optimizer import StrategyOptimizer
    from core.config.strategy_config import StrategyConfig
    
    print("=" * 60)
    print("📊 策略参数优化")
    print("=" * 60)
    
    print(f"\n交易对: {symbol}")
    print(f"回测天数: {days}")
    print(f"显示前: {top_n}个结果")
    print("\n⏳ 正在优化...")
    
    # 创建优化器
    optimizer = StrategyOptimizer(symbol, days)
    
    # 定义参数网格（精简版，快速测试）
    param_grid = {
        'stop_loss_pct': [0.02, 0.03, 0.05],
        'take_profit_pct': [0.08, 0.10, 0.15],
        'buy_threshold': [55, 60, 65],
        'sell_threshold': [40, 45],
        'position_size': [0.2, 0.3],
    }
    
    # 运行优化
    results = optimizer.run_optimization(param_grid)
    
    # 打印报告
    print(optimizer.format_report(top_n))
    
    # 返回最优参数
    if results:
        best = results[0]
        print("\n✅ 最优参数已返回，可用于更新策略配置")
        
        # 保存优化结果
        if save:
            config = StrategyConfig()
            config.save_params(
                best.params,
                f'optimized_{symbol}_{days}d',
                f'{symbol} {days}天优化结果 - 收益:{best.total_return_pct:.2f}%'
            )
            print(f"✅ 参数已保存到配置文件")
        
        return best.params
    
    return None


def save_optimal_params(params: Dict[str, Any], name: str = 'optimal', description: str = ''):
    """保存优化后的参数"""
    from core.config.strategy_config import StrategyConfig
    
    config = StrategyConfig()
    config.save_params(params, name, description)
    print(f"✅ 参数已保存: {name}")


def list_strategy_configs():
    """列出所有策略配置"""
    from core.config.strategy_config import StrategyConfig
    
    config = StrategyConfig()
    configs = config.list_configs()
    
    if not configs:
        print("📋 无策略配置")
        return
    
    print("=" * 60)
    print("📋 策略配置列表")
    print("=" * 60)
    
    for name, info in configs.items():
        params = info.get('params', {})
        print(f"\n📌 {name}")
        print(f"   描述: {info.get('description', '无')}")
        print(f"   创建时间: {info.get('created_at', '未知')}")
        print(f"   参数: 止损={params.get('stop_loss_pct', 0)*100:.0f}%, "
              f"止盈={params.get('take_profit_pct', 0)*100:.0f}%, "
              f"买入阈值={params.get('buy_threshold', 0)}, "
              f"卖出阈值={params.get('sell_threshold', 0)}, "
              f"仓位={params.get('position_size', 0)*100:.0f}%")
    
    print("=" * 60)


def show_simulated_status(config_name: str = 'default'):
    """显示模拟交易状态"""
    from core.config.strategy_config import SimulatedTrader
    
    trader = SimulatedTrader(config_name)
    print(trader.format_status())


def show_simulated_trades(config_name: str = 'default', limit: int = 10):
    """显示模拟交易历史"""
    from core.config.strategy_config import SimulatedTrader
    
    trader = SimulatedTrader(config_name)
    print(trader.format_trades(limit))


def export_simulated_report(config_name: str = 'default', output: str = None):
    """导出模拟交易报告"""
    from core.config.strategy_config import SimulatedTrader
    
    trader = SimulatedTrader(config_name)
    output_file = trader.export_report(output)
    print(f"✅ 报告已导出: {output_file}")


def reset_simulation(config_name: str = 'default'):
    """重置模拟状态"""
    from core.config.strategy_config import SimulatedTrader
    
    trader = SimulatedTrader(config_name)
    trader.reset()
    print(f"✅ 模拟状态已重置: {config_name}")


def show_data_service_status():
    """显示数据服务状态"""
    import subprocess
    
    print("=" * 60)
    print("📡 数据服务状态")
    print("=" * 60)
    
    # 检查进程
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'data_service.py'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"\n✅ 服务运行中 (PID: {pids[0]})")
        else:
            print("\n❌ 服务未运行")
    except Exception:
        print("\n⚠️  无法检查服务状态")
    
    # 显示配置
    config_file = os.path.join(os.path.dirname(__file__), 'config', 'data_service.json')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print(f"\n📋 配置:")
        print(f"   交易对: {', '.join(config.get('symbols', []))}")
        print(f"   周期: {', '.join(config.get('intervals', []))}")
        print(f"   地址: ws://{config.get('host', 'localhost')}:{config.get('port', 8765)}")
    
    print("\n" + "=" * 60)
    print("\n管理命令:")
    print("  python data_service.py start    # 启动服务")
    print("  python data_service.py stop     # 停止服务")
    print("  python data_service.py test     # 测试连接")
    print("  python data_service.py config   # 修改配置")


def show_engine_status():
    """显示实时引擎状态"""
    import subprocess
    
    print("=" * 60)
    print("⚡ 实时引擎状态")
    print("=" * 60)
    
    # 检查进程
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'engine_manager.py'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"\n✅ 引擎运行中 (PID: {pids[0]})")
        else:
            print("\n❌ 引擎未运行")
    except Exception:
        print("\n⚠️  无法检查引擎状态")
    
    # 显示配置
    config_file = os.path.join(os.path.dirname(__file__), 'config', 'engine_config.json')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print(f"\n📋 配置:")
        print(f"   模式: {'实盘' if config.get('mode') == 'live' else '模拟'}")
        print(f"   策略: {config.get('config_name', 'default')}")
        print(f"   数据源: {config.get('data_url', 'ws://localhost:8765')}")
    
    print("\n" + "=" * 60)
    print("\n管理命令:")
    print("  python engine_manager.py start          # 启动模拟交易")
    print("  python engine_manager.py start --live   # 启动实盘交易")
    print("  python engine_manager.py stop           # 停止引擎")
    print("  python engine_manager.py config         # 修改配置")


def run_backtest(db_path: str = None, symbol: str = 'DOGEUSDT', days: int = 30):
    """运行单次回测"""
    from core.backtest.engine import BacktestEngine
    
    print("=" * 60)
    print("📊 策略回测")
    print("=" * 60)
    
    print(f"\n交易对: {symbol}")
    print(f"回测天数: {days}")
    print("\n⏳ 正在回测...")
    
    # 创建回测引擎
    engine = BacktestEngine(initial_balance=1000.0)
    
    # 运行回测
    result = engine.run_backtest(symbol, days)
    
    if result:
        print(engine.format_report(result))
    else:
        print("❌ 回测失败")


# ==================== 主函数 ====================

def main():
    parser = argparse.ArgumentParser(
        description="量化交易系统 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli.py status              # 查看账户状态
  python cli.py positions           # 查看当前持仓
  python cli.py positions --live    # 查看持仓（实时盈亏）
  python cli.py history             # 查看交易历史
  python cli.py history --limit 20  # 查看最近20条
  python cli.py export              # 导出CSV
  python cli.py export -o trades.csv
  python cli.py risk                # 查看风控状态
  python cli.py signals             # 查看最新信号
  python cli.py backtest            # 运行策略回测
  python cli.py optimize            # 参数优化
  python cli.py optimize --save     # 参数优化并保存
  python cli.py configs             # 查看策略配置
  python cli.py simulate            # 模拟交易状态
  python cli.py simulate --trades   # 模拟交易历史
  python cli.py simulate --export   # 导出模拟报告
  python cli.py simulate --reset    # 重置模拟状态
  python cli.py data-service        # 数据服务状态
  python cli.py engine              # 实时引擎状态
        """
    )
    
    parser.add_argument('--db', help='数据库路径')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # status 命令
    subparsers.add_parser('status', help='查看账户状态')
    
    # positions 命令
    pos_parser = subparsers.add_parser('positions', help='查看当前持仓')
    pos_parser.add_argument('--live', action='store_true', help='显示实时盈亏')
    
    # history 命令
    hist_parser = subparsers.add_parser('history', help='查看交易历史')
    hist_parser.add_argument('--limit', type=int, default=20, help='显示条数')
    hist_parser.add_argument('--symbol', help='筛选币种')
    
    # export 命令
    export_parser = subparsers.add_parser('export', help='导出交易记录')
    export_parser.add_argument('-o', '--output', help='输出文件名')
    
    # risk 命令
    subparsers.add_parser('risk', help='查看风控状态')
    
    # signals 命令
    sig_parser = subparsers.add_parser('signals', help='查看最新信号')
    sig_parser.add_argument('--limit', type=int, default=10, help='显示条数')
    
    # backtest 命令
    bt_parser = subparsers.add_parser('backtest', help='运行策略回测')
    bt_parser.add_argument('--symbol', default='DOGEUSDT', help='交易对')
    bt_parser.add_argument('--days', type=int, default=30, help='回测天数')
    
    # optimize 命令
    opt_parser = subparsers.add_parser('optimize', help='参数优化')
    opt_parser.add_argument('--symbol', default='DOGEUSDT', help='交易对')
    opt_parser.add_argument('--days', type=int, default=30, help='回测天数')
    opt_parser.add_argument('--top', type=int, default=5, help='显示前N个结果')
    opt_parser.add_argument('--save', action='store_true', help='保存优化结果')
    
    # configs 命令
    subparsers.add_parser('configs', help='查看策略配置')
    
    # simulate 命令
    sim_parser = subparsers.add_parser('simulate', help='模拟交易')
    sim_parser.add_argument('--config', default='default', help='配置名称')
    sim_parser.add_argument('--trades', action='store_true', help='显示交易历史')
    sim_parser.add_argument('--export', action='store_true', help='导出报告')
    sim_parser.add_argument('--reset', action='store_true', help='重置状态')
    sim_parser.add_argument('--limit', type=int, default=10, help='显示条数')
    
    # data-service 命令
    subparsers.add_parser('data-service', help='数据服务状态')
    
    # engine 命令
    subparsers.add_parser('engine', help='实时引擎状态')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行命令
    if args.command == 'status':
        show_status(args.db)
    elif args.command == 'positions':
        show_positions(args.db, args.live)
    elif args.command == 'history':
        show_history(args.db, args.limit, args.symbol)
    elif args.command == 'export':
        export_trades(args.db, args.output)
    elif args.command == 'risk':
        show_risk(args.db)
    elif args.command == 'signals':
        show_signals(args.db, args.limit)
    elif args.command == 'backtest':
        run_backtest(args.db, args.symbol, args.days)
    elif args.command == 'optimize':
        run_optimization(args.db, args.symbol, args.days, args.top, args.save)
    elif args.command == 'configs':
        list_strategy_configs()
    elif args.command == 'simulate':
        if args.reset:
            reset_simulation(args.config)
        elif args.export:
            export_simulated_report(args.config)
        elif args.trades:
            show_simulated_trades(args.config, args.limit)
        else:
            show_simulated_status(args.config)
    elif args.command == 'data-service':
        show_data_service_status()
    elif args.command == 'engine':
        show_engine_status()


if __name__ == '__main__':
    main()
