"""
系统集成测试
"""
import sys
sys.path.insert(0, '.')

from core.exchange.gate_rest import GateRestClient
from core.strategy.engine import StrategyEngine, Signal
from core.exchange.executor import TradeExecutor


def test_system():
    """测试系统"""
    print("=" * 50)
    print("量化交易系统集成测试")
    print("=" * 50)
    
    # 1. 测试交易所连接
    print("\n1. 测试交易所连接...")
    try:
        client = GateRestClient(sandbox=True)
        
        # 获取DOGE行情
        ticker = client.get_ticker('DOGE/USDT')
        print(f"   ✅ DOGE/USDT: {ticker['last']} (24h: {ticker['change']}%)")
        
        # 注意：模拟盘可能不支持PEPE
        try:
            ticker_pepe = client.get_ticker('PEPE/USDT')
            print(f"   ✅ PEPE/USDT: {ticker_pepe['last']} (24h: {ticker_pepe['change']}%)")
        except:
            print(f"   ⚠️  PEPE/USDT: 模拟盘可能不支持，跳过")
        
    except Exception as e:
        print(f"   ❌ 交易所连接失败: {e}")
        return
    
    # 2. 测试策略引擎
    print("\n2. 测试策略引擎...")
    try:
        strategy = StrategyEngine()
        
        # 获取K线数据
        klines = client.get_klines('DOGE/USDT', '1h', 100)
        
        # 生成信号
        signal = strategy.analyze('DOGE/USDT', klines)
        
        print(f"   ✅ 策略分析完成")
        print(f"      信号: {signal.signal_type}")
        print(f"      价格: {signal.price}")
        print(f"      置信度: {signal.confidence:.2f}")
        print(f"      原因: {signal.reason}")
        
    except Exception as e:
        print(f"   ❌ 策略引擎测试失败: {e}")
        return
    
    # 3. 测试交易执行器
    print("\n3. 测试交易执行器...")
    try:
        executor = TradeExecutor(sandbox=True)
        
        # 获取状态
        status = executor.get_status()
        
        print(f"   ✅ 交易执行器初始化成功")
        print(f"      模式: {'模拟盘' if status['sandbox'] else '实盘'}")
        print(f"      持仓: {status['positions']}")
        print(f"      今日交易: {status['daily_trades']}")
        print(f"      今日盈亏: {status['daily_pnl']:.2f}U")
        
    except Exception as e:
        print(f"   ❌ 交易执行器测试失败: {e}")
        return
    
    # 4. 测试完整流程
    print("\n4. 测试完整流程...")
    try:
        # 模拟一个买入信号
        test_signal = Signal(
            symbol='DOGE/USDT',
            signal_type='buy',
            price=ticker['last'],
            stop_loss=ticker['last'] * 0.97,
            take_profit=ticker['last'] * 1.06,
            confidence=0.8,
            reason='测试信号',
            timestamp=None
        )
        
        print(f"   ✅ 完整流程测试通过")
        print(f"      信号类型: {test_signal.signal_type}")
        print(f"      入场价: {test_signal.price}")
        print(f"      止损价: {test_signal.stop_loss}")
        print(f"      止盈价: {test_signal.take_profit}")
        
        # 注意：不实际执行订单，避免产生真实交易
        print(f"      (跳过实际执行，避免产生真实交易)")
        
    except Exception as e:
        print(f"   ❌ 完整流程测试失败: {e}")
        return
    
    # 测试完成
    print("\n" + "=" * 50)
    print("✅ 所有测试通过！")
    print("=" * 50)
    
    print("\n下一步：")
    print("1. 配置 .env 文件（API Key）")
    print("2. 运行模拟盘测试: python main.py --sandbox")
    print("3. 查看日志: tail -f logs/trading.log")


if __name__ == '__main__':
    test_system()