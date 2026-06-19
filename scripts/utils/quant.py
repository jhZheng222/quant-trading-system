#!/usr/bin/env python3
"""
量化交易系统 CLI (简化版)
========================

核心理念：只保留赚钱必需的功能

用法：
    quant start              # 启动系统
    quant start --live       # 启动实盘
    quant stop               # 停止系统
    quant status             # 查看状态
    quant optimize           # 优化策略
    quant report             # 生成报告
"""

import sys
import os
import json
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent
CONFIG_DIR = ROOT_DIR / 'config'
DATA_DIR = ROOT_DIR / 'data'

# 确保目录存在
CONFIG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


def load_config():
    """加载配置"""
    config_file = CONFIG_DIR / 'settings.json'
    if config_file.exists():
        with open(config_file) as f:
            return json.load(f)
    return {
        'system': {'mode': 'simulation'},
        'data': {'symbols': ['DOGEUSDT', 'PEPEUSDT']},
        'strategy': {
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.08,
            'buy_threshold': 65,
            'sell_threshold': 40,
            'position_size': 0.2
        }
    }


def get_status():
    """获取系统状态"""
    config = load_config()
    status = {
        'data_service': False,
        'engine': False,
        'mode': config.get('system', {}).get('mode', 'simulation'),
        'balance': 0,
        'pnl': 0,
        'trades': 0,
        'win_rate': 0
    }
    
    # 检查数据服务
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'data_service.py'],
            capture_output=True, text=True
        )
        status['data_service'] = result.returncode == 0
    except:
        pass
    
    # 检查引擎
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'engine_manager.py'],
            capture_output=True, text=True
        )
        status['engine'] = result.returncode == 0
    except:
        pass
    
    # 读取模拟状态
    sim_file = CONFIG_DIR / 'simulation_default.json'
    if sim_file.exists():
        with open(sim_file) as f:
            data = json.load(f)
            status['balance'] = data.get('balance', 0)
            status['trades'] = len(data.get('trades', []))
            if data.get('trades'):
                wins = sum(1 for t in data['trades'] if t.get('pnl', 0) > 0)
                status['win_rate'] = wins / len(data['trades']) * 100
                status['pnl'] = sum(t.get('pnl', 0) for t in data['trades'])
    
    return status


def cmd_start(live=False):
    """启动系统"""
    mode = '实盘' if live else '模拟'
    print(f"🚀 启动量化交易系统 ({mode})")
    print("=" * 50)
    
    # 1. 启动数据服务
    print("\n📡 启动数据服务...")
    subprocess.Popen(
        [sys.executable, str(ROOT_DIR / 'data_service.py'), 'start'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    
    # 2. 启动引擎
    print("⚡ 启动交易引擎...")
    cmd = [sys.executable, str(ROOT_DIR / 'engine_manager.py'), 'start']
    if live:
        cmd.append('--live')
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    
    # 3. 检查状态
    status = get_status()
    
    print("\n" + "=" * 50)
    print("✅ 系统已启动")
    print(f"   数据服务: {'运行中' if status['data_service'] else '未启动'}")
    print(f"   交易引擎: {'运行中' if status['engine'] else '未启动'}")
    print(f"   模式: {mode}")
    print("\n💡 使用 'quant status' 查看详细状态")
    print("💡 使用 'quant stop' 停止系统")


def cmd_stop():
    """停止系统"""
    print("⏹️  停止量化交易系统")
    print("=" * 50)
    
    # 停止引擎
    print("\n停止交易引擎...")
    subprocess.run(['pkill', '-f', 'engine_manager.py'], capture_output=True)
    
    # 停止数据服务
    print("停止数据服务...")
    subprocess.run(['pkill', '-f', 'data_service.py'], capture_output=True)
    
    print("\n✅ 系统已停止")


def cmd_status():
    """查看状态"""
    status = get_status()
    
    print("📊 量化交易系统状态")
    print("=" * 50)
    
    # 服务状态
    print("\n🔧 服务状态:")
    print(f"   数据服务: {'🟢 运行中' if status['data_service'] else '🔴 未启动'}")
    print(f"   交易引擎: {'🟢 运行中' if status['engine'] else '🔴 未启动'}")
    print(f"   运行模式: {'实盘' if status['mode'] == 'live' else '模拟'}")
    
    # 交易状态
    print("\n💰 交易状态:")
    print(f"   余额: {status['balance']:.2f}U")
    print(f"   总盈亏: {status['pnl']:+.2f}U")
    print(f"   交易次数: {status['trades']}")
    print(f"   胜率: {status['win_rate']:.1f}%")
    
    # 策略配置
    config = load_config()
    strategy = config.get('strategy', {})
    if strategy:
        print("\n⚙️  策略参数:")
        print(f"   止损: {strategy.get('stop_loss_pct', 0)*100:.0f}%")
        print(f"   止盈: {strategy.get('take_profit_pct', 0)*100:.0f}%")
        print(f"   仓位: {strategy.get('position_size', 0)*100:.0f}%")
    
    print("\n" + "=" * 50)
    
    # 管理命令
    if not status['data_service'] or not status['engine']:
        print("\n💡 系统未完全启动，使用 'quant start' 启动")
    else:
        print("\n💡 系统运行中")
        print("   查看报告: quant report")
        print("   停止系统: quant stop")


def cmd_optimize():
    """优化策略"""
    print("🔍 策略优化")
    print("=" * 50)
    
    # 运行优化
    print("\n⏳ 正在优化（这可能需要几分钟）...")
    
    result = subprocess.run(
        [sys.executable, str(ROOT_DIR / 'cli.py'), 'optimize', 
         '--symbol', 'DOGEUSDT', '--days', '30', '--save', '--top', '3'],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        # 提取关键信息
        lines = result.stdout.split('\n')
        in_report = False
        for line in lines:
            if '策略参数优化报告' in line:
                in_report = True
            if in_report and ('收益' in line or '胜率' in line or '回撤' in line or '推荐参数' in line or '止损' in line or '止盈' in line or '仓位' in line):
                print(line)
    else:
        print("❌ 优化失败")
        if result.stderr:
            print(result.stderr[:500])
    
    print("\n" + "=" * 50)
    print("\n💡 使用 'quant start' 启动系统应用新参数")


def cmd_strategies():
    """列出可用策略"""
    from core.strategies import list_strategies
    
    print("📋 可用策略")
    print("=" * 50)
    
    strategies = list_strategies()
    
    for s in strategies:
        print(f"\n📌 {s['name']}")
        print(f"   描述: {s['description']}")
        print(f"   版本: {s['version']}")
    
    print("\n" + "=" * 50)
    print("\n💡 在 config/settings.json 中修改 strategy.name 切换策略")


def cmd_report():
    """生成报告"""
    print("📋 生成交易报告")
    print("=" * 50)
    
    # 读取模拟数据
    sim_file = CONFIG_DIR / 'simulation_default.json'
    if not sim_file.exists():
        print("\n❌ 无交易数据")
        return
    
    with open(sim_file) as f:
        data = json.load(f)
    
    trades = data.get('trades', [])
    if not trades:
        print("\n❌ 无交易记录")
        return
    
    # 计算统计
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
    losses = len(trades) - wins
    win_rate = wins / len(trades) * 100 if trades else 0
    
    avg_win = sum(t['pnl'] for t in trades if t['pnl'] > 0) / wins if wins else 0
    avg_loss = sum(t['pnl'] for t in trades if t['pnl'] < 0) / losses if losses else 0
    
    print(f"\n📊 交易统计:")
    print(f"   总交易: {len(trades)}笔")
    print(f"   盈利: {wins}笔 | 亏损: {losses}笔")
    print(f"   胜率: {win_rate:.1f}%")
    print(f"   总盈亏: {total_pnl:+.2f}U")
    print(f"   平均盈利: {avg_win:+.2f}U")
    print(f"   平均亏损: {avg_loss:+.2f}U")
    
    # 最近交易
    print(f"\n📝 最近5笔交易:")
    for trade in trades[-5:]:
        pnl = trade.get('pnl', 0)
        emoji = "✅" if pnl > 0 else "❌"
        print(f"   {emoji} {trade.get('symbol', '?')} {trade.get('side', '?')} "
              f"盈亏={pnl:+.2f}U ({trade.get('reason', '?')})")
    
    # 导出报告
    report_file = DATA_DIR / f"report_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(report_file, 'w') as f:
        f.write(f"量化交易报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"总交易: {len(trades)}笔\n")
        f.write(f"胜率: {win_rate:.1f}%\n")
        f.write(f"总盈亏: {total_pnl:+.2f}U\n\n")
        f.write("交易明细:\n")
        for i, trade in enumerate(trades, 1):
            f.write(f"{i}. {trade.get('symbol', '?')} {trade.get('side', '?')} "
                    f"盈亏={trade.get('pnl', 0):+.2f}U ({trade.get('reason', '?')})\n")
    
    print(f"\n📄 报告已保存: {report_file}")
    print("=" * 50)


def main():
    if len(sys.argv) < 2:
        print("""
🚀 量化交易系统 CLI

用法:
    quant start          # 启动系统（模拟）
    quant start --live   # 启动系统（实盘）
    quant stop           # 停止系统
    quant status         # 查看状态
    quant optimize       # 优化策略
    quant strategies     # 列出可用策略
    quant report         # 生成报告
        """)
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'start':
        live = '--live' in sys.argv
        cmd_start(live)
    elif cmd == 'stop':
        cmd_stop()
    elif cmd == 'status':
        cmd_status()
    elif cmd == 'optimize':
        cmd_optimize()
    elif cmd == 'strategies':
        cmd_strategies()
    elif cmd == 'report':
        cmd_report()
    else:
        print(f"❌ 未知命令: {cmd}")
        print("💡 使用 'quant' 查看帮助")


if __name__ == '__main__':
    main()
