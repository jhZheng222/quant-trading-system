"""
WebSocket 数据转发服务
===================

独立的实时数据服务，支持多个客户端订阅。

架构：
  币安 WebSocket → 数据转发服务 → 多个客户端（模拟/实盘/监控）

功能：
- 订阅多个交易对的实时数据
- 支持K线、Ticker、深度数据
- 历史数据缓存
- 多客户端广播
"""

import asyncio
import json
import time
import websockets
from datetime import datetime
from typing import Dict, List, Set, Callable, Optional
from collections import defaultdict
from loguru import logger
import threading
import httpx


class BinanceDataSource:
    """币安数据源"""
    
    BASE_URL = "wss://data-stream.binance.vision/ws"
    REST_URL = "https://data-api.binance.vision"
    
    def __init__(self, symbols: List[str], intervals: List[str] = None):
        self.symbols = [s.lower() for s in symbols]
        self.intervals = intervals or ['1h', '15m']
        self._ws = None
        self._running = False
        
        # 数据缓存
        self.klines: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
        self.tickers: Dict[str, Dict] = {}
        self.depth: Dict[str, Dict] = {}
        
        # 回调
        self.on_kline: Optional[Callable] = None
        self.on_ticker: Optional[Callable] = None
        self.on_depth: Optional[Callable] = None
        
        logger.info(f"📡 币安数据源初始化: {self.symbols}")
    
    def _build_streams(self) -> List[str]:
        """构建订阅流"""
        streams = []
        for symbol in self.symbols:
            # K线流
            for interval in self.intervals:
                streams.append(f"{symbol}@kline_{interval}")
            # Ticker流
            streams.append(f"{symbol}@mini_ticker")
            # 深度流
            streams.append(f"{symbol}@depth20")
        return streams
    
    async def connect(self):
        """连接WebSocket"""
        streams = self._build_streams()
        url = f"{self.BASE_URL}/{'/'.join(streams)}"
        
        logger.info(f"📡 连接: {url[:80]}...")
        
        while self._running:
            try:
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5
                ) as ws:
                    self._ws = ws
                    logger.info("✅ 币安WebSocket已连接")
                    
                    async for message in ws:
                        if not self._running:
                            break
                        self._handle_message(message)
                        
            except websockets.ConnectionClosed as e:
                logger.warning(f"WebSocket断开: {e}")
            except Exception as e:
                logger.error(f"WebSocket异常: {e}")
            
            if self._running:
                await asyncio.sleep(5)
    
    def _handle_message(self, raw: str):
        """处理消息"""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return
        
        event = data.get('e')
        
        if event == 'kline':
            self._handle_kline(data)
        elif event == '24hrMiniTicker':
            self._handle_ticker(data)
        elif event == 'depthUpdate':
            self._handle_depth(data)
    
    def _handle_kline(self, data: Dict):
        """处理K线"""
        k = data.get('k', {})
        symbol = k.get('s', '').upper()
        interval = k.get('i', '')
        is_closed = k.get('x', False)
        
        kline = {
            'timestamp': k.get('t'),
            'open': float(k.get('o', 0)),
            'high': float(k.get('h', 0)),
            'low': float(k.get('l', 0)),
            'close': float(k.get('c', 0)),
            'volume': float(k.get('v', 0)),
            'is_closed': is_closed
        }
        
        # 更新缓存
        cache = self.klines[symbol][interval]
        
        if is_closed:
            cache.append([
                kline['timestamp'],
                kline['open'],
                kline['high'],
                kline['low'],
                kline['close'],
                kline['volume']
            ])
            if len(cache) > 100:
                cache.pop(0)
        
        # 触发回调
        if self.on_kline:
            self.on_kline(symbol, interval, kline, cache.copy())
    
    def _handle_ticker(self, data: Dict):
        """处理Ticker"""
        symbol = data.get('s', '').upper()
        
        ticker = {
            'symbol': symbol,
            'price': float(data.get('c', 0)),
            'change_pct': float(data.get('P', 0)),
            'high': float(data.get('h', 0)),
            'low': float(data.get('l', 0)),
            'volume': float(data.get('v', 0)),
            'timestamp': data.get('E')
        }
        
        self.tickers[symbol] = ticker
        
        # 触发回调
        if self.on_ticker:
            self.on_ticker(symbol, ticker)
    
    def _handle_depth(self, data: Dict):
        """处理深度"""
        symbol = data.get('s', '').upper()
        
        depth = {
            'bids': [[float(p), float(q)] for p, q in data.get('b', [])[:10]],
            'asks': [[float(p), float(q)] for p, q in data.get('a', [])[:10]],
            'timestamp': data.get('E')
        }
        
        self.depth[symbol] = depth
        
        # 触发回调
        if self.on_depth:
            self.on_depth(symbol, depth)
    
    def start(self):
        """启动数据源"""
        self._running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        logger.info("📡 币安数据源已启动")
    
    def stop(self):
        """停止数据源"""
        self._running = False
        logger.info("📡 币安数据源已停止")
    
    def _run_loop(self):
        """事件循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.connect())
    
    def get_klines(self, symbol: str, interval: str = '1h') -> List:
        """获取K线缓存"""
        return self.klines.get(symbol, {}).get(interval, [])
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """获取Ticker缓存"""
        return self.tickers.get(symbol)
    
    def get_depth(self, symbol: str) -> Optional[Dict]:
        """获取深度缓存"""
        return self.depth.get(symbol)


class WebSocketForwarder:
    """WebSocket 数据转发服务
    
    接收多个客户端订阅，广播实时数据
    """
    
    def __init__(self, host: str = 'localhost', port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.data_source: Optional[BinanceDataSource] = None
        self._server = None
        
        logger.info(f"📡 WebSocket转发服务初始化: {host}:{port}")
    
    def set_data_source(self, data_source: BinanceDataSource):
        """设置数据源"""
        self.data_source = data_source
        
        # 注册回调
        data_source.on_kline = self._broadcast_kline
        data_source.on_ticker = self._broadcast_ticker
        data_source.on_depth = self._broadcast_depth
    
    async def _handle_client(self, websocket, path):
        """处理客户端连接"""
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"✅ 客户端连接: {client_id} (总数: {len(self.clients)})")
        
        try:
            # 发送当前缓存数据
            await self._send_cached_data(websocket)
            
            # 监听客户端消息
            async for message in websocket:
                await self._handle_client_message(websocket, message)
                
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            logger.info(f"❌ 客户端断开: {client_id} (总数: {len(self.clients)})")
    
    async def _send_cached_data(self, websocket):
        """发送缓存数据给新客户端"""
        if not self.data_source:
            return
        
        # 发送Ticker缓存
        for symbol, ticker in self.data_source.tickers.items():
            await websocket.send(json.dumps({
                'type': 'ticker',
                'data': ticker
            }))
        
        # 发送K线缓存
        for symbol, intervals in self.data_source.klines.items():
            for interval, klines in intervals.items():
                if klines:
                    await websocket.send(json.dumps({
                        'type': 'kline_history',
                        'symbol': symbol,
                        'interval': interval,
                        'data': klines
                    }))
    
    async def _handle_client_message(self, websocket, message: str):
        """处理客户端消息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'ping':
                await websocket.send(json.dumps({'type': 'pong'}))
            elif msg_type == 'subscribe':
                # 处理订阅请求
                symbol = data.get('symbol')
                logger.info(f"📡 客户端订阅: {symbol}")
                
        except json.JSONDecodeError:
            pass
    
    async def _broadcast_kline(self, symbol: str, interval: str, kline: Dict, history: List):
        """广播K线数据"""
        message = json.dumps({
            'type': 'kline',
            'symbol': symbol,
            'interval': interval,
            'data': kline,
            'is_closed': kline.get('is_closed', False)
        })
        
        await self._broadcast(message)
    
    async def _broadcast_ticker(self, symbol: str, ticker: Dict):
        """广播Ticker数据"""
        message = json.dumps({
            'type': 'ticker',
            'data': ticker
        })
        
        await self._broadcast(message)
    
    async def _broadcast_depth(self, symbol: str, depth: Dict):
        """广播深度数据"""
        message = json.dumps({
            'type': 'depth',
            'symbol': symbol,
            'data': depth
        })
        
        await self._broadcast(message)
    
    async def _broadcast(self, message: str):
        """广播消息给所有客户端"""
        if not self.clients:
            return
        
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.ConnectionClosed:
                disconnected.add(client)
        
        # 清理断开的客户端
        self.clients -= disconnected
    
    async def start(self):
        """启动转发服务"""
        self._server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port
        )
        logger.info(f"✅ WebSocket转发服务已启动: ws://{self.host}:{self.port}")
    
    def stop(self):
        """停止转发服务"""
        if self._server:
            self._server.close()
            logger.info("❌ WebSocket转发服务已停止")


class DataClient:
    """数据客户端
    
    连接转发服务，获取实时数据
    """
    
    def __init__(self, url: str = 'ws://localhost:8765'):
        self.url = url
        self._ws = None
        self._running = False
        
        # 数据缓存
        self.klines: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
        self.tickers: Dict[str, Dict] = {}
        
        # 回调
        self.on_kline: Optional[Callable] = None
        self.on_ticker: Optional[Callable] = None
        
        logger.info(f"📡 数据客户端初始化: {url}")
    
    async def connect(self):
        """连接转发服务"""
        while self._running:
            try:
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    logger.info("✅ 已连接数据服务")
                    
                    async for message in ws:
                        if not self._running:
                            break
                        self._handle_message(message)
                        
            except websockets.ConnectionClosed:
                logger.warning("连接断开")
            except Exception as e:
                logger.error(f"连接异常: {e}")
            
            if self._running:
                await asyncio.sleep(3)
    
    def _handle_message(self, raw: str):
        """处理消息"""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return
        
        msg_type = data.get('type')
        
        if msg_type == 'ticker':
            ticker = data.get('data', {})
            symbol = ticker.get('symbol')
            self.tickers[symbol] = ticker
            
            if self.on_ticker:
                self.on_ticker(symbol, ticker)
        
        elif msg_type == 'kline':
            symbol = data.get('symbol')
            interval = data.get('interval')
            kline = data.get('data', {})
            is_closed = data.get('is_closed', False)
            
            if is_closed:
                cache = self.klines[symbol][interval]
                cache.append([
                    kline['timestamp'],
                    kline['open'],
                    kline['high'],
                    kline['low'],
                    kline['close'],
                    kline['volume']
                ])
                if len(cache) > 100:
                    cache.pop(0)
            
            if self.on_kline:
                self.on_kline(symbol, interval, kline)
        
        elif msg_type == 'kline_history':
            symbol = data.get('symbol')
            interval = data.get('interval')
            history = data.get('data', [])
            self.klines[symbol][interval] = history
    
    def start(self):
        """启动客户端"""
        self._running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        logger.info("📡 数据客户端已启动")
    
    def stop(self):
        """停止客户端"""
        self._running = False
        logger.info("📡 数据客户端已停止")
    
    def _run_loop(self):
        """事件循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.connect())
    
    def get_klines(self, symbol: str, interval: str = '1h') -> List:
        """获取K线数据"""
        return self.klines.get(symbol, {}).get(interval, [])
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """获取Ticker"""
        return self.tickers.get(symbol)
    
    def get_price(self, symbol: str) -> float:
        """获取最新价格"""
        ticker = self.get_ticker(symbol)
        if ticker:
            return ticker.get('price', 0)
        return 0.0


# 全局实例
_forwarder: Optional[WebSocketForwarder] = None
_data_source: Optional[BinanceDataSource] = None


def get_forwarder() -> WebSocketForwarder:
    """获取转发服务实例"""
    global _forwarder
    if _forwarder is None:
        _forwarder = WebSocketForwarder()
    return _forwarder


def get_data_source() -> BinanceDataSource:
    """获取数据源实例"""
    global _data_source
    return _data_source


def init_data_service(symbols: List[str], intervals: List[str] = None,
                      host: str = 'localhost', port: int = 8765):
    """初始化数据服务
    
    Args:
        symbols: 交易对列表
        intervals: K线周期
        host: 服务地址
        port: 服务端口
    """
    global _data_source, _forwarder
    
    # 创建数据源
    _data_source = BinanceDataSource(symbols, intervals)
    
    # 创建转发服务
    _forwarder = WebSocketForwarder(host, port)
    _forwarder.set_data_source(_data_source)
    
    return _forwarder, _data_source


# 使用示例
if __name__ == '__main__':
    import sys
    
    symbols = ['DOGEUSDT', 'PEPEUSDT']
    
    if len(sys.argv) > 1 and sys.argv[1] == 'server':
        # 启动服务端
        print("启动数据服务...")
        
        forwarder, data_source = init_data_service(symbols)
        data_source.start()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(forwarder.start())
        
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            forwarder.stop()
            data_source.stop()
    
    else:
        # 启动客户端测试
        print("连接数据服务...")
        
        client = DataClient()
        client.on_ticker = lambda s, t: print(f"{s}: ${t['price']:.6f}")
        client.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            client.stop()
