"""
完整系统测试
Binance数据 + Gate.io交易 + 策略引擎
"""
import sys
sys.path.insert(0, '.')

from core.data.service import DataCollectionService
from core.strategy.engine import StrategyEngine
from core.exchange.executor import TradeExecutor


def test_full_system():
    """测试完整系统"""
    print("=" * 60)
    print("量化交易系统 - 完整测试")
    print("=" * 60)
    print("数据源: Binance (公开API)")
    print("交易所: Gate.io (模拟盘)")
    print("=" * 60)
    
    # 1. 测试数据采集
    print("\n📊 1. 测试数据采集服务...")
    try:
        data_service = DataCollectionService()
        
        # 采集行情
        tickers = data_service.collect_all_tickers()
        
        print("   ✅ 行情数据:")
        for symbol, ticker in tickers.items():
            print(f"      {symbol}: {ticker['last']} ({ticker['change']}%)")
        
        # 采集K线
        klines = data_service.collect_all_klines('1h', 50)
        
        print("   ✅ K线数据:")
        for key, data in klines.items():
            print(f"      {key}: {len(data)} 条")
        
        # 采集深度
        depths = data_service.collect_all_depth(5)
        
        print("   ✅ 深度数据:")
        for symbol, depth in depths.items():
            print(f"      {symbol}: 买一={depth['bids'][0][0]} 卖一={depth['asks'][0][0]}")
        
    except Exception as e:
        print(f"   ❌ 数据采集失败: {e}")
        return
    
    # 2. 测试策略引擎
    print("\n📈 2. 测试策略引擎...")
    try:
        # 使用默认配置
        strategy = StrategyEngine()
        
        # 分析DOGE
        doge_klines = data_service.get_latest_klines('DOGEUSDT', '1h')
        if doge_klines:
            doge_signal = strategy.analyze('DOGE/USDT', doge_klines)
            print(f"   ✅ DOGE/USDT 策略分析:")
            print(f"      信号: {doge_signal.signal_type}")
            print(f"      价格: {doge_signal.price}")
            print(f"      置信度: {doge_signal.confidence:.2f}")
            print(f"      原因: {doge_signal.reason}")
        
        # 分析PEPE
        pepe_klines = data_service.get_latest_klines('PEPEUSDT', '1h')
        if pepe_klines:
            pepe_signal = strategy.analyze('PEPE/USDT', pepe_klines)
            print(f"   ✅ PEPE/USDT 策略分析:")
            print(f"      信号: {pepe_signal.signal_type}")
            print(f"      价格: {pepe_signal.price}")
            print(f"      置信度: {pepe_signal.confidence:.2f}")
            print(f"      原因: {pepe_signal.reason}")
        
    except Exception as e:
        print(f"   ❌ 策略引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 测试交易执行器
    print("\n💰 3. 测试交易执行器...")
    try:
        executor = TradeExecutor(sandbox=True)
        
        status = executor.get_status()
        
        print(f"   ✅ 交易执行器:")
        print(f"      模式: {'模拟盘' if status['sandbox'] else '实盘'}")
        print(f"      持仓: {status['positions']}")
        print(f"      今日交易: {status['daily_trades']}")
        print(f"      今日盈亏: {status['daily_pnl']:.2f}U")
        
    except Exception as e:
        print(f"   ❌ 交易执行器测试失败: {e}")
        return
    
    # 4. 模拟交易流程
    print("\n🔄 4. 模拟交易流程...")
    try:
        # 获取最新行情
        doge_ticker = data_service.get_latest_ticker('DOGEUSDT')
        
        if doge_ticker and doge_signal.signal_type != 'hold':
            print(f"   ✅ 交易信号:")
            print(f"      交易对: DOGE/USDT")
            print(f"      方向: {doge_signal.signal_type}")
            print(f"      入场价: {doge_signal.price}")
            print(f"      止损价: {doge_signal.stop_loss}")
            print(f"      止盈价: {doge_signal.take_profit}")
            print(f"      置信度: {doge_signal.confidence:.2f}")
            
            # 注意：不实际执行
            print(f"      (模拟测试，不实际执行)")
        else:
            print(f"   ℹ️  当前无交易信号，观望中...")
        
    except Exception as e:
        print(f"   ❌ 模拟交易流程失败: {e}")
        return
    
    # 测试完成
    print("\n" + "=" * 60)
    print("✅ 系统测试完成")
    print("=" * 60)
    
    print("\n📋 系统架构:")
    print("   数据源: Binance (国内直连，无需API Key)")
    print("   交易所: Gate.io (模拟盘)")
    print("   策略: 趋势跟踪 + 事件驱动")
    print("   资金: 10U (模拟)")
    
    print("\n🚀 下一步:")
    print("   1. 注册Gate.io账号")
    print("   2. 获取模拟盘API Key")
    print("   3. 配置 .env 文件")
    print("   4. 运行: python main.py --sandbox --once")
    print("   5. 观察策略表现")
    
    print("\n💡 运行命令:")
    print("   # 测试运行一次")
    print("   python main.py --sandbox --once")
    print("")
    print("   # 持续运行（每小时）")
    print("   python main.py --sandbox --interval 3600")
    print("")
    print("   # 查看日志")
    print("   tail -f logs/trading.log")


if __name__ == '__main__':
    test_full_system()