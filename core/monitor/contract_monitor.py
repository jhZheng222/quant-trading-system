"""
合约数据监控服务
实时监控DOGE、PEPE合约数据
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from loguru import logger
import pandas as pd

from core.data.binance_data import BinanceDataCollector


@dataclass
class MarketSnapshot:
    """市场快照"""
    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    high_24h: float
    low_24h: float
    bid: float
    ask: float
    timestamp: datetime
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'price': self.price,
            'change_24h': self.change_24h,
            'volume_24h': self.volume_24h,
            'high_24h': self.high_24h,
            'low_24h': self.low_24h,
            'bid': self.bid,
            'ask': self.ask,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class TechnicalIndicators:
    """技术指标"""
    symbol: str
    timeframe: str
    
    # 移动平均线
    ema_20: float
    ema_50: float
    ema_200: float
    
    # RSI
    rsi_14: float
    
    # MACD
    macd: float
    macd_signal: float
    macd_hist: float
    
    # 布林带
    bb_upper: float
    bb_middle: float
    bb_lower: float
    
    # 成交量
    volume_ma_20: float
    current_volume: float
    volume_ratio: float
    
    timestamp: datetime
    
    def to_dict(self):
        return asdict(self)


@dataclass
class AlertRule:
    """报警规则"""
    name: str
    symbol: str
    condition: str  # 'price_above', 'price_below', 'volume_spike', 'rsi_overbought', etc.
    threshold: float
    enabled: bool = True
    triggered: bool = False
    last_triggered: Optional[datetime] = None


class ContractMonitor:
    """合约数据监控器"""
    
    def __init__(self):
        """初始化监控器"""
        self.collector = BinanceDataCollector()
        self.symbols = ['DOGEUSDT', 'PEPEUSDT']
        
        # 数据存储
        self.snapshots: Dict[str, MarketSnapshot] = {}
        self.indicators: Dict[str, TechnicalIndicators] = {}
        self.klines_cache: Dict[str, List] = {}
        self.alert_rules: List[AlertRule] = []
        self.alert_history: List[Dict] = []
        
        # 监控状态
        self.running = False
        self.update_interval = 60  # 60秒更新一次
        
        # 初始化默认报警规则
        self._init_default_alerts()
        
        logger.info("合约数据监控器初始化完成")
    
    def _init_default_alerts(self):
        """初始化默认报警规则"""
        for symbol in self.symbols:
            # 价格突破报警
            self.alert_rules.extend([
                AlertRule(
                    name=f"{symbol} 价格突破0.11",
                    symbol=symbol,
                    condition='price_above',
                    threshold=0.11 if 'DOGE' in symbol else 0.000004,
                    enabled=True
                ),
                AlertRule(
                    name=f"{symbol} 价格跌破0.09",
                    symbol=symbol,
                    condition='price_below',
                    threshold=0.09 if 'DOGE' in symbol else 0.000003,
                    enabled=True
                ),
                AlertRule(
                    name=f"{symbol} RSI超买(>70)",
                    symbol=symbol,
                    condition='rsi_above',
                    threshold=70,
                    enabled=True
                ),
                AlertRule(
                    name=f"{symbol} RSI超卖(<30)",
                    symbol=symbol,
                    condition='rsi_below',
                    threshold=30,
                    enabled=True
                ),
                AlertRule(
                    name=f"{symbol} 成交量飙升(>3倍)",
                    symbol=symbol,
                    condition='volume_ratio_above',
                    threshold=3.0,
                    enabled=True
                ),
            ])
    
    def calculate_indicators(self, klines: List, symbol: str, timeframe: str = '1h') -> TechnicalIndicators:
        """计算技术指标"""
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # EMA
        ema_20 = df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema_50 = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        ema_200 = df['close'].ewm(span=200, adjust=False).mean().iloc[-1] if len(df) >= 200 else ema_50
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        macd = (exp1 - exp2).iloc[-1]
        macd_signal = (exp1 - exp2).ewm(span=9, adjust=False).mean().iloc[-1]
        macd_hist = macd - macd_signal
        
        # 布林带
        bb_middle = df['close'].rolling(window=20).mean().iloc[-1]
        bb_std = df['close'].rolling(window=20).std().iloc[-1]
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)
        
        # 成交量
        volume_ma_20 = df['volume'].rolling(window=20).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        volume_ratio = current_volume / volume_ma_20 if volume_ma_20 > 0 else 1.0
        
        return TechnicalIndicators(
            symbol=symbol,
            timeframe=timeframe,
            ema_20=ema_20,
            ema_50=ema_50,
            ema_200=ema_200,
            rsi_14=rsi,
            macd=macd,
            macd_signal=macd_signal,
            macd_hist=macd_hist,
            bb_upper=bb_upper,
            bb_middle=bb_middle,
            bb_lower=bb_lower,
            volume_ma_20=volume_ma_20,
            current_volume=current_volume,
            volume_ratio=volume_ratio,
            timestamp=datetime.now()
        )
    
    def check_alerts(self, snapshot: MarketSnapshot, indicators: TechnicalIndicators):
        """检查报警规则"""
        for rule in self.alert_rules:
            if not rule.enabled or rule.symbol != snapshot.symbol:
                continue
            
            triggered = False
            
            if rule.condition == 'price_above':
                triggered = snapshot.price > rule.threshold
            elif rule.condition == 'price_below':
                triggered = snapshot.price < rule.threshold
            elif rule.condition == 'rsi_above':
                triggered = indicators.rsi_14 > rule.threshold
            elif rule.condition == 'rsi_below':
                triggered = indicators.rsi_14 < rule.threshold
            elif rule.condition == 'volume_ratio_above':
                triggered = indicators.volume_ratio > rule.threshold
            
            if triggered and not rule.triggered:
                rule.triggered = True
                rule.last_triggered = datetime.now()
                
                alert = {
                    'rule': rule.name,
                    'symbol': rule.symbol,
                    'condition': rule.condition,
                    'threshold': rule.threshold,
                    'current_value': self._get_current_value(rule, snapshot, indicators),
                    'timestamp': datetime.now().isoformat()
                }
                self.alert_history.append(alert)
                logger.warning(f"🚨 报警触发: {rule.name}")
            
            elif not triggered:
                rule.triggered = False
    
    def _get_current_value(self, rule: AlertRule, snapshot: MarketSnapshot, 
                           indicators: TechnicalIndicators) -> float:
        """获取当前值"""
        if 'price' in rule.condition:
            return snapshot.price
        elif 'rsi' in rule.condition:
            return indicators.rsi_14
        elif 'volume' in rule.condition:
            return indicators.volume_ratio
        return 0
    
    def update(self):
        """更新监控数据"""
        for symbol in self.symbols:
            try:
                # 获取行情
                ticker = self.collector.collect_ticker(symbol)
                self.snapshots[symbol] = MarketSnapshot(
                    symbol=symbol,
                    price=ticker['last'],
                    change_24h=ticker['change'],
                    volume_24h=ticker['volume'],
                    high_24h=ticker['high'],
                    low_24h=ticker['low'],
                    bid=ticker['bid'],
                    ask=ticker['ask'],
                    timestamp=datetime.now()
                )
                
                # 获取K线
                klines = self.collector.collect_klines(symbol, '1h', 100)
                self.klines_cache[symbol] = klines
                
                # 计算指标
                if klines:
                    self.indicators[symbol] = self.calculate_indicators(klines, symbol, '1h')
                
                # 检查报警
                if symbol in self.snapshots and symbol in self.indicators:
                    self.check_alerts(self.snapshots[symbol], self.indicators[symbol])
                
                logger.info(f"更新 {symbol}: 价格={ticker['last']}, 涨跌={ticker['change']}%")
                
            except Exception as e:
                logger.error(f"更新 {symbol} 失败: {e}")
    
    def get_status(self) -> Dict:
        """获取监控状态"""
        return {
            'running': self.running,
            'symbols': self.symbols,
            'snapshots': {k: v.to_dict() for k, v in self.snapshots.items()},
            'indicators': {k: v.to_dict() for k, v in self.indicators.items()},
            'alert_rules': len(self.alert_rules),
            'alert_history': len(self.alert_history),
            'last_update': datetime.now().isoformat()
        }
    
    def get_market_overview(self) -> str:
        """获取市场概览（文本格式）"""
        lines = []
        lines.append("=" * 50)
        lines.append("📊 合约数据监控 - 市场概览")
        lines.append("=" * 50)
        
        for symbol in self.symbols:
            if symbol not in self.snapshots:
                continue
            
            snap = self.snapshots[symbol]
            ind = self.indicators.get(symbol)
            
            lines.append(f"\n🪙 {symbol}")
            lines.append(f"   价格: ${snap.price:.6f}")
            lines.append(f"   24h涨跌: {snap.change_24h:+.2f}%")
            lines.append(f"   24h高/低: ${snap.high_24h:.6f} / ${snap.low_24h:.6f}")
            lines.append(f"   买一/卖一: ${snap.bid:.6f} / ${snap.ask:.6f}")
            
            if ind:
                lines.append(f"   --- 技术指标 ---")
                lines.append(f"   EMA20: ${ind.ema_20:.6f}")
                lines.append(f"   EMA50: ${ind.ema_50:.6f}")
                lines.append(f"   RSI(14): {ind.rsi_14:.1f}")
                lines.append(f"   MACD: {ind.macd:.8f}")
                lines.append(f"   布林带: ${ind.bb_upper:.6f} / ${ind.bb_middle:.6f} / ${ind.bb_lower:.6f}")
                lines.append(f"   成交量比: {ind.volume_ratio:.2f}x")
                
                # 信号提示
                signals = []
                if ind.rsi_14 > 70:
                    signals.append("⚠️ RSI超买")
                elif ind.rsi_14 < 30:
                    signals.append("⚠️ RSI超卖")
                
                if snap.price > ind.bb_upper:
                    signals.append("📈 突破布林上轨")
                elif snap.price < ind.bb_lower:
                    signals.append("📉 跌破布林下轨")
                
                if ind.macd_hist > 0 and ind.macd > ind.macd_signal:
                    signals.append("🟢 MACD金叉")
                elif ind.macd_hist < 0 and ind.macd < ind.macd_signal:
                    signals.append("🔴 MACD死叉")
                
                if signals:
                    lines.append(f"   信号: {' | '.join(signals)}")
        
        # 报警历史
        if self.alert_history:
            lines.append(f"\n🚨 最近报警 (共{len(self.alert_history)}条)")
            for alert in self.alert_history[-5:]:
                lines.append(f"   [{alert['timestamp'][:19]}] {alert['rule']}")
        
        lines.append(f"\n⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 50)
        
        return "\n".join(lines)
    
    async def start(self, interval: int = 60):
        """启动监控"""
        self.running = True
        self.update_interval = interval
        
        logger.info(f"启动合约数据监控，更新间隔: {interval}秒")
        
        while self.running:
            try:
                self.update()
                logger.info(f"等待 {interval} 秒后更新...")
            except Exception as e:
                logger.error(f"监控更新失败: {e}")
            
            await asyncio.sleep(interval)
    
    def stop(self):
        """停止监控"""
        self.running = False
        logger.info("监控已停止")


# 使用示例
if __name__ == '__main__':
    async def main():
        monitor = ContractMonitor()
        
        # 更新一次数据
        monitor.update()
        
        # 打印市场概览
        print(monitor.get_market_overview())
        
        # 打印状态
        print("\n监控状态:")
        print(json.dumps(monitor.get_status(), indent=2, default=str))
    
    asyncio.run(main())