"""
测试OKX API封装
"""
import sys
sys.path.insert(0, '.')

from core.exchange.okx_rest import OKXRestClient

def test_okx_rest():
    """测试OKX REST API"""
    print("测试OKX REST API...")
    
    try:
        client = OKXRestClient()
        
        # 测试获取行情
        print("\n1. 测试获取DOGE行情...")
        ticker = client.get_ticker('DOGE-USDT-SWAP')
        print(f"   DOGE/USDT 最新价: {ticker['last']}")
        print(f"   24h涨跌幅: {ticker['change']}%")
        
        # 测试获取PEPE行情
        print("\n2. 测试获取PEPE行情...")
        ticker = client.get_ticker('PEPE-USDT-SWAP')
        print(f"   PEPE/USDT 最新价: {ticker['last']}")
        print(f"   24h涨跌幅: {ticker['change']}%")
        
        # 测试获取K线数据
        print("\n3. 测试获取K线数据...")
        klines = client.get_klines('DOGE-USDT-SWAP', '1h', 5)
        print(f"   获取到 {len(klines)} 条K线数据")
        if klines:
            print(f"   最新K线: 开={klines[-1][1]}, 高={klines[-1][2]}, 低={klines[-1][3]}, 收={klines[-1][4]}")
        
        # 测试获取深度数据
        print("\n4. 测试获取深度数据...")
        depth = client.get_depth('DOGE-USDT-SWAP', 5)
        print(f"   买一: {depth['bids'][0][0]} ({depth['bids'][0][1]})")
        print(f"   卖一: {depth['asks'][0][0]} ({depth['asks'][0][1]})")
        
        print("\n✅ 所有测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_okx_rest()