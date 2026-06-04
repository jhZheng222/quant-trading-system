"""
实时交易引擎 v3 (简化版)
========================

直接连接币安WebSocket，不需要转发服务。

架构：
  币安WebSocket → 引擎 → 交易执行
"""

import json
import time
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger

from core.strategies import load_strategy, list_strategies, Signal

try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False


class BinanceClient:
    """币安WebSocket客户端（内嵌）"""
    
    BASE_URL = "wss://data-stream.binance.vision/ws"
    
    def __init__(self, symbols: List[str], intervals: List[str] = None):
        if not HAS_WS:
            raise RuntimeError("websockets未安装")
        
        self.symbols = [s.lower() for s in symbols]
        self.intervals = intervals or ['1h']
        
        # 数据缓存
        self.klines: Dict[str, Dict[str, List]] = {}
        self.tickers: Dict[str, Dict] = {}
        
        # 回调
        self.on_kline = None
        self.on_ticker = None
        
        # 状态
        self._running = False
        
        logger.info(f"📡 币安客户端初始化: {symbols}")
    
    def _build_streams(self) -> List[str]:
        streams = []
        for symbol in self.symbols:
            for interval in self.intervals:
                streams.append(f"{symbol}@kline_{interval}")
            streams.append(f"{symbol}@trade")  # 使用 trade 流
        return streams
    
    async def connect(self):
        streams = self._build_streams()
        url = f"{self.BASE_URL}/{'/'.join(streams)}"
        
        while self._running:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    logger.info("✅ 币安WebSocket已连接")
                    
                    async for message in ws:
                        if not self._running:
                            break
                        self._handle_message(message)
            except Exception as e:
                logger.warning(f"连接断开: {e}")
                if self._running:
                    await asyncio.sleep(5)
    
    def _handle_message(self, raw: str):
        try:
            data = json.loads(raw)
        except:
            return
        
        event = data.get('e')
        
        if event == 'kline':
            self._handle_kline(data)
        elif event == 'trade':  # 处理 trade 事件
            self._handle_trade(data)
    
    def _handle_kline(self, data: Dict):
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
        
        # 初始化缓存
        if symbol not in self.klines:
            self.klines[symbol] = {}
        if interval not in self.klines[symbol]:
            self.klines[symbol][interval] = []
        
        # 更新缓存
        cache = self.klines[symbol][interval]
        if is_closed:
            cache.append([
                kline['timestamp'], kline['open'], kline['high'],
                kline['low'], kline['close'], kline['volume']
            ])
            if len(cache) > 100:
                cache.pop(0)
        
        # 回调
        if self.on_kline:
            self.on_kline(symbol, interval, kline)
    
    def _handle_trade(self, data: Dict):
        """处理 trade 事件"""
        symbol = data.get('s', '').upper()
        price = float(data.get('p', 0))
        
        ticker = {
            'symbol': symbol,
            'price': price,
            'timestamp': data.get('T')
        }
        
        self.tickers[symbol] = ticker
        
        # 回调
        if self.on_ticker:
            self.on_ticker(symbol, ticker)
    
    def start(self):
        self._running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        logger.info("📡 币安客户端已启动")
    
    def stop(self):
        self._running = False
    
    def _run_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.connect())
    
    def get_klines(self, symbol: str, interval: str = '1h') -> List:
        return self.klines.get(symbol, {}).get(interval, [])
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        return self.tickers.get(symbol)
    
    def get_price(self, symbol: str) -> float:
        ticker = self.get_ticker(symbol)
        return ticker['price'] if ticker else 0.0


class RealtimeEngineV3:
    """
    实时交易引擎 v3 (简化版)
    
    直接连接币安，支持策略插件。
    """
    
    def __init__(self, config_name: str = 'default', mode: str = 'simulation',
                 symbols: List[str] = None, strategy_name: str = None):
        self.config_name = config_name
        self.mode = mode
        self.symbols = symbols or ['DOGEUSDT', 'PEPEUSDT']
        
        # 加载配置
        config_file = 'config/settings.json'
        try:
            with open(config_file) as f:
                config = json.load(f)
                self.params = config.get('strategy', {})
                strategy_name = strategy_name or config.get('strategy', {}).get('name', 'ema_rsi')
        except:
            self.params = {
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.08,
                'buy_threshold': 65,
                'sell_threshold': 40,
                'position_size': 0.2
            }
            strategy_name = strategy_name or 'ema_rsi'
        
        # 加载策略
        self.strategy = load_strategy(strategy_name, self.params)
        logger.info(f"📊 加载策略: {self.strategy.name} v{self.strategy.version}")
        
        # 币安客户端（内嵌）
        self.client = BinanceClient(self.symbols, ['1h'])
        self.client.on_ticker = self._on_ticker
        self.client.on_kline = self._on_kline
        
        # 模拟交易器
        self.simulator = self._create_simulator()
        
        # 状态
        self.evaluation_count = 0
        
        logger.info(f"⚡ 引擎 v3 初始化: {mode}")
    
    def _create_simulator(self):
        """创建模拟交易器"""
        if self.mode != 'simulation':
            return None
        
        from core.config.strategy_config import SimulatedTrader
        return SimulatedTrader(self.config_name)
    
    def _on_ticker(self, symbol: str, ticker: Dict):
        """Ticker更新"""
        if self.simulator:
            price = ticker['price']
            closed = self.simulator.check_stop_loss_take_profit(symbol, price)
            for trade in closed:
                logger.info(f"📉 自动平仓: {trade['reason']} 盈亏={trade['pnl']:.2f}U")
    
    def _on_kline(self, symbol: str, interval: str, kline: Dict):
        """K线更新"""
        if not kline.get('is_closed'):
            return
        
        self.evaluation_count += 1
        logger.info(f"⚡ K线收盘 {symbol} | #{self.evaluation_count}")
        
        # 使用策略生成信号
        klines = self.client.get_klines(symbol, interval)
        signal = self.strategy.generate_signal(symbol, klines, kline['close'])
        
        if signal and signal.action != 'hold':
            self._execute_signal(symbol, signal)
    
    def _execute_signal(self, symbol: str, signal: Signal):
        """执行交易"""
        if not self.simulator:
            return
        
        has_position = any(p['symbol'] == symbol for p in self.simulator.positions)
        
        if signal.action == 'buy' and not has_position:
            self.simulator.open_position(
                symbol, 'buy', signal.price,
                reason=signal.reason
            )
            logger.info(f"📈 开仓 {symbol} @ {signal.price} ({signal.reason})")
        elif signal.action == 'sell' and has_position:
            for i, pos in enumerate(self.simulator.positions):
                if pos['symbol'] == symbol:
                    self.simulator.close_position(i, signal.price, '反向信号')
                    logger.info(f"📉 平仓 {symbol} @ {signal.price} ({signal.reason})")
                    break
    
    def start(self):
        self.client.start()
        logger.info("⚡ 引擎已启动")
    
    def stop(self):
        self.client.stop()
        logger.info("⚡ 引擎已停止")
    
    def get_status(self) -> Dict:
        status = {
            'mode': self.mode,
            'symbols': self.symbols,
            'evaluations': self.evaluation_count,
            'prices': {}
        }
        
        for symbol in self.symbols:
            price = self.client.get_price(symbol)
            if price > 0:
                status['prices'][symbol] = price
        
        if self.simulator:
            sim = self.simulator.get_status()
            status['balance'] = sim['balance']
            status['pnl'] = sim['total_pnl']
            status['trades'] = sim['total_trades']
            status['win_rate'] = sim['win_rate']
        
        return status


# 全局实例
_engine: Optional[RealtimeEngineV3] = None


def get_engine() -> Optional[RealtimeEngineV3]:
    return _engine


def init_engine(config_name: str = 'default', mode: str = 'simulation',
                symbols: List[str] = None, strategy_name: str = None) -> RealtimeEngineV3:
    global _engine
    _engine = RealtimeEngineV3(config_name, mode, symbols, strategy_name)
    return _engine
