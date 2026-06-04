"""
OKX WebSocket API封装
"""
import asyncio
import json
import websockets
from typing import Dict, List, Callable, Optional
from loguru import logger
from config.settings import okx_config


class OKXWebSocket:
    """OKX WebSocket客户端"""
    
    def __init__(self):
        """初始化WebSocket客户端"""
        self.ws = None
        self.private_ws = None
        self.callbacks = {}
        self.running = False
        self.reconnect_interval = 5  # 重连间隔（秒）
        logger.info("OKX WebSocket客户端初始化完成")
    
    async def connect(self):
        """连接公共频道"""
        try:
            self.ws = await websockets.connect(okx_config.ws_url)
            self.running = True
            logger.info("WebSocket公共频道连接成功")
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            raise
    
    async def connect_private(self):
        """连接私有频道（需要登录）"""
        try:
            self.private_ws = await websockets.connect(okx_config.private_ws_url)
            await self._login()
            logger.info("WebSocket私有频道连接成功")
        except Exception as e:
            logger.error(f"私有频道连接失败: {e}")
            raise
    
    async def _login(self):
        """登录私有频道"""
        import hmac
        import base64
        import hashlib
        import time
        
        timestamp = str(int(time.time()))
        sign = hmac.new(
            okx_config.secret_key.encode(),
            (timestamp + 'GET' + '/users/self/verify').encode(),
            hashlib.sha256
        ).digest()
        sign = base64.b64encode(sign).decode()
        
        login_msg = {
            "op": "login",
            "args": [{
                "apiKey": okx_config.api_key,
                "passphrase": okx_config.passphrase,
                "timestamp": timestamp,
                "sign": sign
            }]
        }
        
        await self.private_ws.send(json.dumps(login_msg))
        response = await self.private_ws.recv()
        data = json.loads(response)
        
        if data.get('event') == 'login':
            logger.info("私有频道登录成功")
        else:
            raise Exception(f"登录失败: {data}")
    
    async def subscribe(self, channels: List[Dict], private: bool = False):
        """订阅频道
        
        Args:
            channels: 频道列表，如：
                [{"channel": "tickers", "instId": "DOGE-USDT-SWAP"}]
            private: 是否使用私有频道
        """
        ws = self.private_ws if private else self.ws
        if not ws:
            raise Exception("WebSocket未连接")
        
        subscribe_msg = {
            "op": "subscribe",
            "args": channels
        }
        
        await ws.send(json.dumps(subscribe_msg))
        logger.info(f"订阅频道: {channels}")
    
    async def subscribe_ticker(self, symbols: List[str]):
        """订阅实时行情"""
        channels = [{"channel": "tickers", "instId": symbol} for symbol in symbols]
        await self.subscribe(channels)
    
    async def subscribe_kline(self, symbols: List[str], timeframe: str = '1H'):
        """订阅K线数据"""
        channels = [{"channel": f"candle{timeframe}", "instId": symbol} for symbol in symbols]
        await self.subscribe(channels)
    
    async def subscribe_depth(self, symbols: List[str]):
        """订阅深度数据"""
        channels = [{"channel": "books5", "instId": symbol} for symbol in symbols]
        await self.subscribe(channels)
    
    async def subscribe_trades(self, symbols: List[str]):
        """订阅成交数据"""
        channels = [{"channel": "trades", "instId": symbol} for symbol in symbols]
        await self.subscribe(channels)
    
    async def subscribe_funding_rate(self, symbols: List[str]):
        """订阅资金费率"""
        channels = [{"channel": "funding-rate", "instId": symbol} for symbol in symbols]
        await self.subscribe(channels)
    
    async def subscribe_positions(self):
        """订阅持仓变化（私有频道）"""
        channels = [{"channel": "positions", "instType": "SWAP"}]
        await self.subscribe(channels, private=True)
    
    async def subscribe_orders(self):
        """订阅订单变化（私有频道）"""
        channels = [{"channel": "orders", "instType": "SWAP"}]
        await self.subscribe(channels, private=True)
    
    def on(self, channel: str, callback: Callable):
        """注册回调函数
        
        Args:
            channel: 频道名称，如 'tickers', 'candle1H', 'positions'
            callback: 回调函数，接收 data 参数
        """
        self.callbacks[channel] = callback
        logger.info(f"注册回调: {channel}")
    
    async def _handle_message(self, data: Dict):
        """处理消息"""
        channel = data.get('arg', {}).get('channel', '')
        
        if channel in self.callbacks:
            try:
                await self.callbacks[channel](data)
            except Exception as e:
                logger.error(f"回调处理错误 {channel}: {e}")
        else:
            logger.debug(f"未处理的消息: {channel}")
    
    async def listen(self):
        """监听消息"""
        if not self.ws:
            await self.connect()
        
        logger.info("开始监听WebSocket消息")
        
        while self.running:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                
                # 处理订阅确认
                if data.get('event') == 'subscribe':
                    logger.info(f"订阅成功: {data}")
                    continue
                
                # 处理错误
                if data.get('event') == 'error':
                    logger.error(f"WebSocket错误: {data}")
                    continue
                
                # 处理数据
                if 'data' in data:
                    await self._handle_message(data)
                    
            except websockets.ConnectionClosed:
                logger.warning("WebSocket连接断开，尝试重连...")
                await self._reconnect()
            except Exception as e:
                logger.error(f"WebSocket处理错误: {e}")
                await asyncio.sleep(1)
    
    async def _reconnect(self):
        """重连"""
        await asyncio.sleep(self.reconnect_interval)
        try:
            await self.connect()
            logger.info("WebSocket重连成功")
        except Exception as e:
            logger.error(f"重连失败: {e}")
    
    async def close(self):
        """关闭连接"""
        self.running = False
        if self.ws:
            await self.ws.close()
        if self.private_ws:
            await self.private_ws.close()
        logger.info("WebSocket连接关闭")


# 使用示例
async def example_usage():
    """使用示例"""
    ws = OKXWebSocket()
    
    # 注册回调
    async def on_ticker(data):
        for ticker in data.get('data', []):
            print(f"行情: {ticker['instId']} 最新价: {ticker['last']}")
    
    ws.on('tickers', on_ticker)
    
    # 连接并订阅
    await ws.connect()
    await ws.subscribe_ticker(['DOGE-USDT-SWAP', 'PEPE-USDT-SWAP'])
    
    # 监听
    await ws.listen()


if __name__ == '__main__':
    asyncio.run(example_usage())