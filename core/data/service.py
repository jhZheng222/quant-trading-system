"""
数据采集服务
使用Binance获取真实数据，用于策略分析
"""
import asyncio
from datetime import datetime
from typing import Dict, List
from loguru import logger

from core.data.binance_data import BinanceDataCollector
from config.settings import trading_config


class DataCollectionService:
    """数据采集服务"""
    
    def __init__(self):
        """初始化数据采集服务"""
        self.collector = BinanceDataCollector()
        self.symbols = ['DOGEUSDT', 'PEPEUSDT']
        self.data_cache = {
            'tickers': {},
            'klines': {},
            'depth': {},
            'last_update': {}
        }
        logger.info("数据采集服务初始化完成")
    
    def collect_all_tickers(self) -> Dict:
        """采集所有交易对行情"""
        results = {}
        for symbol in self.symbols:
            try:
                ticker = self.collector.collect_ticker(symbol)
                results[symbol] = ticker
                self.data_cache['tickers'][symbol] = ticker
                self.data_cache['last_update'][symbol] = datetime.now()
                logger.info(f"行情更新: {symbol} = {ticker['last']} ({ticker['change']}%)")
            except Exception as e:
                logger.error(f"采集行情失败 {symbol}: {e}")
        
        return results
    
    def collect_all_klines(self, interval: str = '1h', limit: int = 100) -> Dict:
        """采集所有交易对K线"""
        results = {}
        for symbol in self.symbols:
            try:
                klines = self.collector.collect_klines(symbol, interval, limit)
                key = f"{symbol}_{interval}"
                results[key] = klines
                self.data_cache['klines'][key] = klines
                logger.info(f"K线更新: {symbol} {interval} = {len(klines)} 条")
            except Exception as e:
                logger.error(f"采集K线失败 {symbol}: {e}")
        
        return results
    
    def collect_all_depth(self, limit: int = 20) -> Dict:
        """采集所有交易对深度"""
        results = {}
        for symbol in self.symbols:
            try:
                depth = self.collector.collect_depth(symbol, limit)
                results[symbol] = depth
                self.data_cache['depth'][symbol] = depth
                logger.info(f"深度更新: {symbol} 买一={depth['bids'][0][0]} 卖一={depth['asks'][0][0]}")
            except Exception as e:
                logger.error(f"采集深度失败 {symbol}: {e}")
        
        return results
    
    def get_latest_ticker(self, symbol: str) -> Dict:
        """获取最新行情（从缓存）"""
        return self.data_cache['tickers'].get(symbol, {})
    
    def get_latest_klines(self, symbol: str, interval: str = '1h') -> List:
        """获取最新K线（从缓存）"""
        key = f"{symbol}_{interval}"
        return self.data_cache['klines'].get(key, [])
    
    def get_latest_depth(self, symbol: str) -> Dict:
        """获取最新深度（从缓存）"""
        return self.data_cache['depth'].get(symbol, {})
    
    def get_cache_status(self) -> Dict:
        """获取缓存状态"""
        status = {}
        for symbol in self.symbols:
            last_update = self.data_cache['last_update'].get(symbol)
            status[symbol] = {
                'has_ticker': symbol in self.data_cache['tickers'],
                'has_klines': any(k.startswith(symbol) for k in self.data_cache['klines']),
                'has_depth': symbol in self.data_cache['depth'],
                'last_update': last_update.isoformat() if last_update else None
            }
        return status
    
    async def start_realtime(self, callback=None):
        """启动实时数据采集
        
        Args:
            callback: 数据更新回调函数
        """
        logger.info("启动实时数据采集...")
        
        # 注册回调
        async def on_ticker(data):
            symbol = data.get('s', '')
            if symbol in [s.replace('USDT', '') + 'USDT' for s in self.symbols]:
                ticker = {
                    'symbol': symbol,
                    'last': float(data.get('c', 0)),
                    'change': float(data.get('P', 0)),
                    'volume': float(data.get('v', 0)),
                    'timestamp': data.get('E', 0)
                }
                self.data_cache['tickers'][symbol] = ticker
                self.data_cache['last_update'][symbol] = datetime.now()
                
                if callback:
                    await callback('ticker', ticker)
        
        self.collector.client.on('ticker', on_ticker)
        
        # 订阅数据流
        await self.collector.client.subscribe_ticker(self.symbols)
        
        # 开始监听
        await self.collector.client.listen()
    
    def stop(self):
        """停止数据采集"""
        self.collector.client.running = False
        logger.info("数据采集服务已停止")


class DataService:
    """数据服务（单例）"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> DataCollectionService:
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = DataCollectionService()
        return cls._instance


# 使用示例
if __name__ == '__main__':
    import asyncio
    
    async def main():
        # 创建数据服务
        service = DataCollectionService()
        
        # 采集数据
        print("采集行情数据...")
        tickers = service.collect_all_tickers()
        
        for symbol, ticker in tickers.items():
            print(f"{symbol}: {ticker['last']} ({ticker['change']}%)")
        
        print("\n采集K线数据...")
        klines = service.collect_all_klines('1h', 10)
        
        for key, data in klines.items():
            print(f"{key}: {len(data)} 条")
        
        print("\n采集深度数据...")
        depths = service.collect_all_depth(5)
        
        for symbol, depth in depths.items():
            print(f"{symbol}: 买一={depth['bids'][0][0]} 卖一={depth['asks'][0][0]}")
        
        print("\n缓存状态:")
        status = service.get_cache_status()
        for symbol, info in status.items():
            print(f"{symbol}: {info}")
        
        print("\n✅ 数据采集测试完成")
    
    asyncio.run(main())