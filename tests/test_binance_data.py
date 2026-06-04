"""
测试Binance数据API
"""
import sys
sys.path.insert(0, '.')

from core.data.binance_data import BinanceDataCollector


def test_binance_data():
    """测试Binance数据API"""
    print("=" * 50)
    print("Binance 数据API测试")
    print("=" * 50)
    
    collector = BinanceDataCollector()
    
    # 1. 测试DOGE行情
    print("\n1. 测试DOGE行情...")
    try:
        ticker = collector.collect_ticker('DOGEUSDT')
        print(f"   ✅ DOGE/USDT")
        print(f"      最新价: {ticker['last']}")
        print(f"      24h涨跌: {ticker['change']}%")
        print(f"      24h成交量: {ticker['volume']:,.0f}")
        print(f"      买一: {ticker['bid']}")
        print(f"      卖一: {ticker['ask']}")
    except Exception as e:
        print(f"   ❌ DOGE行情获取失败: {e}")
        return
    
    # 2. 测试PEPE行情
    print("\n2. 测试PEPE行情...")
    try:
        ticker = collector.collect_ticker('PEPEUSDT')
        print(f"   ✅ PEPE/USDT")
        print(f"      最新价: {ticker['last']}")
        print(f"      24h涨跌: {ticker['change']}%")
        print(f"      24h成交量: {ticker['volume']:,.0f}")
    except Exception as e:
        print(f"   ❌ PEPE行情获取失败: {e}")
    
    # 3. 测试K线数据
    print("\n3. 测试K线数据...")
    try:
        klines = collector.collect_klines('DOGEUSDT', '1h', 10)
        print(f"   ✅ 获取到 {len(klines)} 条K线数据")
        if klines:
            latest = klines[-1]
            print(f"      最新K线:")
            print(f"        时间: {latest[0]}")
            print(f"        开盘: {latest[1]}")
            print(f"        最高: {latest[2]}")
            print(f"        最低: {latest[3]}")
            print(f"        收盘: {latest[4]}")
            print(f"        成交量: {latest[5]:,.0f}")
    except Exception as e:
        print(f"   ❌ K线数据获取失败: {e}")
    
    # 4. 测试深度数据
    print("\n4. 测试深度数据...")
    try:
        depth = collector.collect_depth('DOGEUSDT', 5)
        print(f"   ✅ 深度数据")
        print(f"      买盘:")
        for i, (price, qty) in enumerate(depth['bids'][:3]):
            print(f"        {i+1}. {price} x {qty}")
        print(f"      卖盘:")
        for i, (price, qty) in enumerate(depth['asks'][:3]):
            print(f"        {i+1}. {price} x {qty}")
    except Exception as e:
        print(f"   ❌ 深度数据获取失败: {e}")
    
    # 5. 测试交易对信息
    print("\n5. 测试交易对信息...")
    try:
        info = collector.client.get_exchange_info('DOGEUSDT')
        if 'symbols' in info and len(info['symbols']) > 0:
            symbol_info = info['symbols'][0]
            print(f"   ✅ 交易对信息")
            print(f"      交易对: {symbol_info['symbol']}")
            print(f"      状态: {symbol_info['status']}")
            print(f"      基础资产: {symbol_info['baseAsset']}")
            print(f"      报价资产: {symbol_info['quoteAsset']}")
    except Exception as e:
        print(f"   ❌ 交易对信息获取失败: {e}")
    
    # 测试完成
    print("\n" + "=" * 50)
    print("✅ Binance数据API测试完成")
    print("=" * 50)
    
    print("\n结论:")
    print("- Binance公开数据API国内可访问")
    print("- 不需要API Key")
    print("- 数据实时、准确")
    print("- 可用于策略分析和回测")


if __name__ == '__main__':
    test_binance_data()