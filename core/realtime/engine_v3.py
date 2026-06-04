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

from core.config.strategy_config import StrategyConfig, SimulatedTrader

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
            streams.append(f"{symbol}@mini_ticker")
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
        elif event == '24hrMiniTicker':
            self._handle_ticker(data)
    
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
    
    def _handle_ticker(self, data: Dict):
        symbol = data.get('s', '').upper()
        ticker = {
            'symbol': symbol,
            'price': float(data.get('c', 0)),
            'change_pct': float(data.get('P', 0)),
            'timestamp': data.get('E')
        }
        
        self.tickers[symbol] = ticker
        
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
    
    直接连接币安，不需要转发服务。
    """
    
    def __init__(self, config_name: str = 'default', mode: str = 'simulation',
                 symbols: List[str] = None):
        self.config_name = config_name
        self.mode = mode
        self.symbols = symbols or ['DOGEUSDT', 'PEPEUSDT']
        
        # 加载策略配置
        config_file = 'config/settings.json'
        try:
            with open(config_file) as f:
                config = json.load(f)
                self.params = config.get('strategy', {})
        except:
            self.params = {
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.08,
                'buy_threshold': 65,
                'sell_threshold': 40,
                'position_size': 0.2
            }
        
        # 币安客户端（内嵌）
        self.client = BinanceClient(self.symbols, ['1h'])
        self.client.on_ticker = self._on_ticker
        self.client.on_kline = self._on_kline
        
        # 模拟交易器
        self.simulator = SimulatedTrader(config_name) if mode == 'simulation' else None
        
        # 状态
        self.evaluation_count = 0
        
        logger.info(f"⚡ 引擎 v3 初始化: {mode}")
    
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
        
        # 生成信号
        klines = self.client.get_klines(symbol, interval)
        signal = self._generate_signal(klines, kline['close'])
        
        if signal:
            self._execute_signal(symbol, signal, kline['close'])
    
    def _generate_signal(self, klines: List, price: float) -> Optional[Dict]:
        """生成信号"""
        if len(klines) < 24:
            return None
        
        closes = [k[4] for k in klines]
        
        # 简单EMA策略
        ema_20 = sum(closes[-20:]) / 20
        ema_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else ema_20
        
        # RSI
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-14:]]
        losses = [-d if d < 0 else 0 for d in deltas[-14:]]
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 100
        
        # 计算得分
        score = 50
        if ema_20 > ema_50:
            score += 10
        else:
            score -= 10
        
        if rsi < 30:
            score += 15
        elif rsi > 70:
            score -= 15
        
        # 信号
        if score >= self.params.get('buy_threshold', 65):
            signal = 'buy'
        elif score <= self.params.get('sell_threshold', 40):
            signal = 'sell'
        else:
            signal = 'hold'
        
        return {'signal': signal, 'score': score, 'rsi': rsi}
    
    def _execute_signal(self, symbol: str, signal: Dict, price: float):
        """执行交易"""
        if not self.simulator:
            return
        
        has_position = any(p['symbol'] == symbol for p in self.simulator.positions)
        
        if signal['signal'] == 'buy' and not has_position:
            self.simulator.open_position(symbol, 'buy', price, reason=f"score={signal['score']}")
            logger.info(f"📈 开仓 {symbol} @ {price}")
        elif signal['signal'] == 'sell' and has_position:
            for i, pos in enumerate(self.simulator.positions):
                if pos['symbol'] == symbol:
                    self.simulator.close_position(i, price, '反向信号')
                    logger.info(f"📉 平仓 {symbol} @ {price}")
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
                symbols: List[str] = None) -> RealtimeEngineV3:
    global _engine
    _engine = RealtimeEngineV3(config_name, mode, symbols)
    return _engine
