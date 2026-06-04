"""
模拟交易测试
"""
import sys
sys.path.insert(0, '.')

from core.simulation.engine import SimulationEngine


def test_simulation():
    """测试模拟交易"""
    print("=" * 60)
    print("🎯 模拟交易系统测试")
    print("=" * 60)
    print("数据源: Binance 真实数据")
    print("账户: 虚拟账户 (10U)")
    print("杠杆: 20x")
    print("=" * 60)
    
    # 创建模拟引擎
    engine = SimulationEngine(initial_balance=10.0)
    
    # 运行一次分析
    print("\n正在分析市场...")
    engine.run_once()
    
    # 打印详细状态
    print("\n" + "=" * 60)
    print("📊 详细状态")
    print("=" * 60)
    
    status = engine.get_status()
    
    print(f"\n账户余额: {status['account']['balance']:.4f}U")
    print(f"总盈亏: {status['account']['total_pnl']:+.4f}U")
    print(f"总交易: {status['account']['total_trades']} 笔")
    print(f"胜率: {status['account']['win_rate']:.1f}%")
    
    if status['positions']:
        print(f"\n当前持仓:")
        for symbol, pos in status['positions'].items():
            print(f"  {symbol}: {pos['side']} @ {pos['entry_price']}")
    
    if status['recent_trades']:
        print(f"\n最近交易:")
        for trade in status['recent_trades'][-3:]:
            print(f"  [{trade['exit_time'][:19]}] {trade['symbol']}: "
                  f"{trade['pnl']:+.4f}U ({trade['pnl_pct']:+.2f}%)")
    
    print("\n" + "=" * 60)
    print("✅ 模拟交易测试完成")
    print("=" * 60)
    
    print("\n💡 使用方法:")
    print("  # 单次运行")
    print("  python simulation.py --once")
    print("")
    print("  # 持续运行（每小时）")
    print("  python simulation.py --interval 3600")
    print("")
    print("  # 自定义初始资金")
    print("  python simulation.py --balance 100 --once")
    print("")
    print("  # 查看历史数据")
    print("  cat data/simulation_history.json | python -m json.tool")


if __name__ == '__main__':
    test_simulation()