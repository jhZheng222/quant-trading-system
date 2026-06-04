"""
Binance 数据采集器
支持实时行情、K线、深度、资金费率等数据
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
import httpx
from loguru import logger


class BinanceDataClient:
    """Binance 数据客户端"""
    
    REST_URL = "https://data-api.binance.vision"
    WS_URL = "wss://data-stream.binance.vision"
    
    def __init__(self):
        """初始化客户端"""
        self.session = httpx.Client(timeout=30.0)
        self.ws = None
        self.callbacks = {}
        logger.info("Binance数据客户端初始化完成")
    
    def get_ticker(self, symbol: str) -> Dict:
        """获取实时行情"""
        try:
            url = f"{self.REST_URL}/api/v3/ticker/24hr"
            params = {'symbol': symbol}
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            return {
                'symbol': data['symbol'],
                'last': float(data['lastPrice']),
                'bid': float(data['bidPrice']),
                'ask': float(data['askPrice']),
                'high': float(data['highPrice']),
                'low': float(data['lowPrice']),
                'volume': float(data['volume']),
                'change': float(data['priceChangePercent']),
                'timestamp': int(time.time() * 1000)
            }
        except Exception as e:
            logger.error(f"获取行情失败 {symbol}: {e}")
            raise
    
    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 100) -> List:
        """获取K线数据
        
        Returns:
            List: [[timestamp, open, high, low, close, volume], ...]
        """
        try:
            url = f"{self.REST_URL}/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            return [[
                int(k[0]),      # timestamp
                float(k[1]),    # open
                float(k[2]),    # high
                float(k[3]),    # low
                float(k[4]),    # close
                float(k[5]),    # volume
            ] for k in data]
        except Exception as e:
            logger.error(f"获取K线失败 {symbol}: {e}")
            raise
    
    def get_depth(self, symbol: str, limit: int = 20) -> Dict:
        """获取深度数据"""
        try:
            url = f"{self.REST_URL}/api/v3/depth"
            params = {'symbol': symbol, 'limit': limit}
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            return {
                'bids': [[float(p), float(q)] for p, q in data['bids']],
                'asks': [[float(p), float(q)] for p, q in data['asks']],
                'timestamp': int(time.time() * 1000)
            }
        except Exception as e:
            logger.error(f"获取深度失败 {symbol}: {e}")
            raise
    
    def get_trades(self, symbol: str, limit: int = 50) -> List:
        """获取最近成交"""
        try:
            url = f"{self.REST_URL}/api/v3/trades"
            params = {'symbol': symbol, 'limit': limit}
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            return [{
                'id': t['id'],
                'price': float(t['price']),
                'qty': float(t['qty']),
                'time': t['time'],
                'is_buyer_maker': t['isBuyerMaker']
            } for t in data]
        except Exception as e:
            logger.error(f"获取成交失败 {symbol}: {e}")
            raise
    
    def get_exchange_info(self, symbol: str = None) -> Dict:
        """获取交易所信息"""
        try:
            url = f"{self.REST_URL}/api/v3/exchangeInfo"
            params = {}
            if symbol:
                params['symbol'] = symbol
            
            response = self.session.get(url, params=params, timeout=10)
            return response.json()
        except Exception as e:
            logger.error(f"获取交易所信息失败: {e}")
            raise
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        """获取资金费率
        
        Args:
            symbol: 交易对，如 'DOGEUSDT'
            
        Returns:
            资金费率信息字典
        """
        try:
            # Binance 资金费率 API
            url = "https://fapi.binance.com/fapi/v1/fundingRate"
            params = {'symbol': symbol, 'limit': 1}
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data and len(data) > 0:
                return {
                    'symbol': data[0]['symbol'],
                    'fundingRate': float(data[0]['fundingRate']),
                    'fundingTime': data[0]['fundingTime'],
                    'lastFundingRate': float(data[0]['fundingRate']),
                    'nextFundingRate': float(data[0]['fundingRate'])  # 简化处理
                }
            return None
        except Exception as e:
            logger.error(f"获取资金费率失败 {symbol}: {e}")
            return None
    
    async def connect_ws(self, streams: List[str]):
        """连接WebSocket"""
        import websockets
        
        url = f"{self.WS_URL}/ws/{'/'.join(streams)}"
        self.ws = await websockets.connect(url)
        logger.info(f"WebSocket连接成功: {url}")
    
    async def subscribe_ticker(self, symbols: List[str]):
        """订阅实时行情"""
        streams = [f"{s.lower()}@ticker" for s in symbols]
        await self.connect_ws(streams)
    
    async def subscribe_kline(self, symbols: List[str], interval: str = '1h'):
        """订阅K线"""
        streams = [f"{s.lower()}@kline_{interval}" for s in symbols]
        await self.connect_ws(streams)
    
    async def subscribe_depth(self, symbols: List[str]):
        """订阅深度"""
        streams = [f"{s.lower()}@depth20" for s in symbols]
        await self.connect_ws(streams)
    
    async def subscribe_trades(self, symbols: List[str]):
        """订阅成交"""
        streams = [f"{s.lower()}@trade" for s in symbols]
        await self.connect_ws(streams)
    
    def on(self, event: str, callback: Callable):
        """注册回调"""
        self.callbacks[event] = callback
    
    async def listen(self):
        """监听WebSocket消息"""
        if not self.ws:
            logger.error("WebSocket未连接")
            return
        
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self._handle_message(data)
        except Exception as e:
            logger.error(f"WebSocket监听失败: {e}")
    
    async def _handle_message(self, data: Dict):
        """处理WebSocket消息"""
        event = data.get('e', '')
        
        if event == 'ticker':
            if 'ticker' in self.callbacks:
                await self.callbacks['ticker'](data)
        elif event == 'kline':
            if 'kline' in self.callbacks:
                await self.callbacks['kline'](data)
        elif event == 'trade':
            if 'trade' in self.callbacks:
                await self.callbacks['trade'](data)
    
    async def close(self):
        """关闭连接"""
        if self.ws:
            await self.ws.close()
            logger.info("WebSocket连接关闭")


class BinanceDataCollector:
    """Binance数据采集器"""
    
    def __init__(self):
        """初始化采集器"""
        self.client = BinanceDataClient()
        self.data_store = {
            'tickers': {},
            'klines': {},
            'depth': {},
        }
        logger.info("Binance数据采集器初始化完成")
    
    def collect_ticker(self, symbol: str) -> Dict:
        """采集实时行情"""
        ticker = self.client.get_ticker(symbol)
        self.data_store['tickers'][symbol] = ticker
        return ticker
    
    def collect_klines(self, symbol: str, interval: str = '1h', limit: int = 100) -> List:
        """采集K线数据"""
        klines = self.client.get_klines(symbol, interval, limit)
        key = f"{symbol}_{interval}"
        self.data_store['klines'][key] = klines
        return klines
    
    def collect_depth(self, symbol: str, limit: int = 20) -> Dict:
        """采集深度数据"""
        depth = self.client.get_depth(symbol, limit)
        self.data_store['depth'][symbol] = depth
        return depth
    
    def get_latest_ticker(self, symbol: str) -> Optional[Dict]:
        """获取最新行情（从缓存）"""
        return self.data_store['tickers'].get(symbol)
    
    def get_latest_klines(self, symbol: str, interval: str = '1h') -> Optional[List]:
        """获取最新K线（从缓存）"""
        key = f"{symbol}_{interval}"
        return self.data_store['klines'].get(key)
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        """获取资金费率"""
        return self.client.get_funding_rate(symbol)
    
    async def start_realtime(self, symbols: List[str]):
        """启动实时数据采集"""
        # 注册回调
        async def on_ticker(data):
            symbol = data.get('s', '')
            self.data_store['tickers'][symbol] = {
                'symbol': symbol,
                'last': float(data.get('c', 0)),
                'change': float(data.get('P', 0)),
                'volume': float(data.get('v', 0)),
                'timestamp': data.get('E', 0)
            }
            logger.debug(f"行情更新: {symbol} = {self.data_store['tickers'][symbol]['last']}")
        
        self.client.on('ticker', on_ticker)
        
        # 订阅行情
        await self.client.subscribe_ticker(symbols)
        
        # 开始监听
        await self.client.listen()


# 测试代码
if __name__ == '__main__':
    client = BinanceDataClient()
    
    # 测试获取行情
    ticker = client.get_ticker('DOGEUSDT')
    print(f"DOGE行情: ${ticker['last']:.6f}")
    
    # 测试获取K线
    klines = client.get_klines('DOGEUSDT', '1h', 5)
    print(f"K线数据: {len(klines)} 条")
    
    # 测试获取资金费率
    funding = client.get_funding_rate('DOGEUSDT')
    if funding:
        print(f"资金费率: {funding['fundingRate']:.6f}")
