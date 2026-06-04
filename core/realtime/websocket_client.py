"""
Binance WebSocket 实时数据客户端
================================

免费公开WebSocket，无需API Key。

数据流：
- K线实时推送（1h/15m/5m）
- 实时行情（ticker）
- 资金费率（定期）

架构：
  Binance WS → 本地缓存 → 引擎评估 → 交易信号
"""

import json
import time
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Callable, Optional
from collections import defaultdict
from loguru import logger

try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False
    logger.warning("websockets未安装，实时数据不可用")


class BinanceWebSocket:
    """
    Binance 公开 WebSocket 客户端
    
    免费、无需Key、国内可直连（data-stream.binance.vision）
    """
    
    BASE_URL = "wss://data-stream.binance.vision/ws"
    
    def __init__(self, symbols: List[str] = None, intervals: List[str] = None):
        """
        Args:
            symbols: 交易对列表 ['DOGEUSDT', 'PEPEUSDT']
            intervals: K线周期 ['1h', '15m', '5m']
        """
        if not HAS_WS:
            raise RuntimeError("websockets未安装")
        
        self.symbols = [s.lower() for s in (symbols or ['dogeusdt', 'pepeusdt'])]
        self.intervals = intervals or ['1h']
        
        # 数据缓存
        self.klines: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
        self.tickers: Dict[str, Dict] = {}
        self.funding_rates: Dict[str, float] = {}
        
        # 回调
        self.on_kline_close: Optional[Callable] = None
        self.on_ticker_update: Optional[Callable] = None
        
        # 状态
        self._running = False
        self._ws = None
        self._reconnect_delay = 1
        self._max_reconnect_delay = 60
        self._last_heartbeat = 0
        
        logger.info(f"📡 WebSocket客户端初始化: {self.symbols}, 周期={self.intervals}")
    
    def start(self):
        """启动WebSocket（非阻塞，在后台线程运行）"""
        if self._running:
            return
        
        self._running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        logger.info("📡 WebSocket后台线程已启动")
    
    def stop(self):
        """停止WebSocket"""
        self._running = False
        logger.info("📡 WebSocket已停止")
    
    def _run_loop(self):
        """事件循环（在独立线程中运行）"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._connect_and_listen())
    
    async def _connect_and_listen(self):
        """连接并监听"""
        streams = self._build_stream_names()
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
                    self._reconnect_delay = 1
                    logger.info("✅ WebSocket已连接")
                    
                    async for message in ws:
                        if not self._running:
                            break
                        self._handle_message(message)
                        
            except websockets.ConnectionClosed as e:
                logger.warning(f"WebSocket断开: {e}, {self._reconnect_delay}秒后重连")
            except Exception as e:
                logger.error(f"WebSocket异常: {e}")
            
            if self._running:
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    self._max_reconnect_delay
                )
    
    def _build_stream_names(self) -> List[str]:
        """构建订阅流名称"""
        streams = []
        for symbol in self.symbols:
            # K线流
            for interval in self.intervals:
                streams.append(f"{symbol}@kline_{interval}")
            # 实时行情
            streams.append(f"{symbol}@mini_ticker")
        return streams
    
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
        
        self._last_heartbeat = time.time()
    
    def _handle_kline(self, data: Dict):
        """处理K线数据"""
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
        
        # 更新缓存（保留最近100根）
        cache = self.klines[symbol][interval]
        
        if is_closed:
            # K线收盘，追加新数据
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
            
            logger.debug(f"📊 K线收盘 {symbol} {interval}: {kline['close']}")
            
            # 触发回调
            if self.on_kline_close:
                try:
                    self.on_kline_close(symbol, interval, cache.copy())
                except Exception as e:
                    logger.error(f"K线回调异常: {e}")
        else:
            # K线未收盘，更新最后一根（实时价格）
            if cache:
                last = cache[-1]
                last[2] = max(last[2], kline['high'])   # 更新最高
                last[3] = min(last[3], kline['low'])     # 更新最低
                last[4] = kline['close']                  # 更新收盘
                last[5] = kline['volume']                 # 更新成交量
    
    def _handle_ticker(self, data: Dict):
        """处理实时行情"""
        symbol = data.get('s', '').upper()
        
        self.tickers[symbol] = {
            'price': float(data.get('c', 0)),
            'change_pct': float(data.get('P', 0)),
            'high': float(data.get('h', 0)),
            'low': float(data.get('l', 0)),
            'volume': float(data.get('v', 0)),
            'quote_volume': float(data.get('q', 0)),
            'timestamp': data.get('E')
        }
        
        # 保存到数据库（通过engine的storage）
        if hasattr(self, 'engine') and self.engine and hasattr(self.engine, 'storage'):
            try:
                self.engine.storage.save_ticker(symbol, self.tickers[symbol])
            except Exception as e:
                logger.debug(f"保存ticker失败: {e}")
        
        if self.on_ticker_update:
            try:
                self.on_ticker_update(symbol, self.tickers[symbol])
            except Exception as e:
                logger.error(f"行情回调异常: {e}")
    
    def get_klines(self, symbol: str, interval: str = '1h') -> List:
        """获取缓存的K线数据"""
        return self.klines.get(symbol.upper(), {}).get(interval, [])
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """获取最新行情"""
        return self.tickers.get(symbol.upper())
    
    def get_price(self, symbol: str) -> float:
        """获取最新价格"""
        ticker = self.get_ticker(symbol)
        if ticker:
            return ticker['price']
        klines = self.get_klines(symbol, '1h')
        if klines:
            return klines[-1][4]
        return 0.0
    
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._running and self._ws is not None
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'connected': self.is_connected(),
            'symbols': self.symbols,
            'intervals': self.intervals,
            'kline_counts': {
                s: {i: len(self.klines[s.upper()][i]) for i in self.intervals}
                for s in self.symbols
            },
            'ticker_count': len(self.tickers),
            'last_heartbeat': self._last_heartbeat
        }


class RealtimeEngine:
    """
    实时交易引擎
    
    WebSocket驱动，K线收盘时触发分析。
    使用统一数据源（DataService）
    """
    
    def __init__(self, engine, symbols: List[str] = None,
                 intervals: List[str] = None):
        """
        Args:
            engine: BaseEngine实例（如LivermoreEngine）
            symbols: 交易对
            intervals: K线周期
        """
        self.engine = engine
        self.symbols = symbols or ['DOGEUSDT', 'PEPEUSDT']
        self.intervals = intervals or ['1h']
        
        # 使用统一数据源
        from core.data.service import DataService
        self.data_service = DataService.get_instance()
        
        # 初始化WebSocket（用于实时数据）
        self.ws = BinanceWebSocket(self.symbols, self.intervals)
        self.ws.on_kline_close = self._on_kline_close
        
        # 统计
        self.evaluation_count = 0
        self.last_evaluation = None
        
        logger.info(f"⚡ 实时引擎初始化: {self.symbols}")
    
    def start(self):
        """启动实时引擎"""
        # 先拉取历史K线（预热）
        self._warmup()
        
        # 启动WebSocket
        self.ws.start()
        logger.info("⚡ 实时引擎已启动，等待K线收盘...")
    
    def stop(self):
        """停止"""
        self.ws.stop()
        logger.info("⚡ 实时引擎已停止")
    
    def _warmup(self):
        """预热：从统一数据源获取历史K线数据"""
        for symbol in self.symbols:
            for interval in self.intervals:
                try:
                    # 从DataService获取数据
                    self.data_service.collect_all_klines(interval, 100)
                    klines = self.data_service.get_latest_klines(symbol, interval)
                    
                    if klines:
                        self.ws.klines[symbol.upper()][interval] = klines
                        logger.info(f"📊 预热 {symbol} {interval}: {len(klines)}根K线")
                    else:
                        logger.warning(f"预热 {symbol} {interval}: 无数据")
                except Exception as e:
                    logger.warning(f"预热失败 {symbol} {interval}: {e}")
    
    def _on_kline_close(self, symbol: str, interval: str, klines: List):
        """K线收盘回调 — 触发策略评估"""
        if interval != self.intervals[0]:
            return  # 只在主周期评估
        
        self.evaluation_count += 1
        self.last_evaluation = datetime.now()
        
        logger.info(f"{'='*40}")
        logger.info(f"⚡ K线收盘 {symbol} {interval} | 第{self.evaluation_count}次评估")
        
        # 获取最新价格
        current_price = klines[-1][4] if klines else 0
        
        # 市场情绪（每次评估都更新）
        from core.analysis.market_sentiment import MarketSentiment
        sentiment = MarketSentiment().get_full_sentiment(self.symbols)
        
        # 市场状态
        market_state = self.engine.analyze_market(
            {symbol: klines}, sentiment
        )
        
        # 多策略信号
        signals = self.engine.generate_signals(
            symbol, klines, market_state, sentiment
        )
        
        # 保存信号到数据库（修复信号生成与存储分离问题）
        for sig in signals:
            if sig.action != 'hold':  # 只存储有效信号
                self.engine.storage.save_signal({
                    'symbol': symbol,
                    'signal_type': sig.action,
                    'price': current_price,
                    'confidence': sig.confidence,
                    'reason': sig.reason or ''
                })
        
        # 执行策略逻辑
        self.engine.run_once(self.symbols)
        
        # 简要输出
        logger.info(f"价格={current_price} | 情绪={sentiment.get('sentiment_score', '?')} | 市场={market_state.get('regime', '?')}")
        logger.info(f"{'='*40}")
    
    def get_status(self) -> str:
        """状态摘要"""
        ws_status = self.ws.get_status()
        
        lines = [
            "⚡ 实时引擎状态:",
            f"   WebSocket: {'✅ 已连接' if ws_status['connected'] else '❌ 未连接'}",
            f"   交易对: {', '.join(self.symbols)}",
            f"   周期: {', '.join(self.intervals)}",
            f"   评估次数: {self.evaluation_count}",
            f"   上次评估: {self.last_evaluation or '无'}",
        ]
        
        # 实时价格
        for symbol in self.symbols:
            price = self.ws.get_price(symbol)
            if price > 0:
                lines.append(f"   {symbol}: ${price:.8f}")
        
        # K线缓存
        for symbol in self.symbols:
            for interval in self.intervals:
                count = len(self.ws.get_klines(symbol, interval))
                lines.append(f"   {symbol} {interval} K线: {count}根")
        
        return "\n".join(lines)
