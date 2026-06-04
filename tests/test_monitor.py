"""
监控服务测试
"""
import sys
sys.path.insert(0, '.')

from core.monitor.contract_monitor import ContractMonitor


def test_monitor():
    """测试监控服务"""
    print("=" * 60)
    print("📊 合约数据监控测试")
    print("=" * 60)
    
    monitor = ContractMonitor()
    
    # 更新数据
    print("\n正在获取市场数据...")
    monitor.update()
    
    # 打印市场概览
    print(monitor.get_market_overview())
    
    # 打印技术指标详情
    print("\n" + "=" * 60)
    print("📈 技术指标详情")
    print("=" * 60)
    
    for symbol in monitor.symbols:
        if symbol in monitor.indicators:
            ind = monitor.indicators[symbol]
            print(f"\n{symbol}:")
            print(f"  EMA20:  ${ind.ema_20:.6f}")
            print(f"  EMA50:  ${ind.ema_50:.6f}")
            print(f"  RSI(14): {ind.rsi_14:.1f}")
            print(f"  MACD:   {ind.macd:.8f}")
            print(f"  布林上轨: ${ind.bb_upper:.6f}")
            print(f"  布林中轨: ${ind.bb_middle:.6f}")
            print(f"  布林下轨: ${ind.bb_lower:.6f}")
            print(f"  成交量比: {ind.volume_ratio:.2f}x")
    
    # 打印报警规则
    print("\n" + "=" * 60)
    print("🚨 报警规则")
    print("=" * 60)
    
    for rule in monitor.alert_rules:
        status = "✅" if rule.enabled else "❌"
        print(f"  {status} {rule.name} ({rule.condition} {rule.threshold})")
    
    print("\n✅ 监控测试完成")
    print("\n下一步:")
    print("  1. 运行CLI监控: python monitor.py --mode cli")
    print("  2. 运行Web监控: python monitor.py --mode web --port 8080")
    print("  3. 两者同时运行: python monitor.py --mode both")


if __name__ == '__main__':
    test_monitor()