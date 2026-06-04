"""
策略引擎 - 趋势跟踪策略
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Signal:
    """交易信号"""
    symbol: str
    signal_type: str  # 'buy', 'sell', 'hold'
    price: float
    stop_loss: float
    take_profit: float
    confidence: float  # 0-1
    reason: str
    timestamp: datetime


class TrendStrategy:
    """趋势跟踪策略"""
    
    def __init__(self, config: Dict = None):
        """初始化策略
        
        Args:
            config: 策略参数配置
        """
        self.config = config or {
            'ema_short': 20,
            'ema_long': 50,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'bb_period': 20,
            'bb_std': 2,
        }
        logger.info("趋势跟踪策略初始化完成")
    
    def calculate_indicators(self, klines: List) -> pd.DataFrame:
        """计算技术指标
        
        Args:
            klines: K线数据 [[timestamp, open, high, low, close, volume], ...]
            
        Returns:
            DataFrame with indicators
        """
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # EMA
        df['ema_short'] = df['close'].ewm(span=self.config['ema_short'], adjust=False).mean()
        df['ema_long'] = df['close'].ewm(span=self.config['ema_long'], adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config['rsi_period']).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(window=self.config['bb_period']).mean()
        bb_std = df['close'].rolling(window=self.config['bb_period']).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * self.config['bb_std'])
        df['bb_lower'] = df['bb_middle'] - (bb_std * self.config['bb_std'])
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 成交量MA
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    def generate_signal(self, klines: List, symbol: str) -> Signal:
        """生成交易信号
        
        Args:
            klines: K线数据
            symbol: 交易对
            
        Returns:
            Signal对象
        """
        df = self.calculate_indicators(klines)
        
        if len(df) < 50:
            return Signal(
                symbol=symbol,
                signal_type='hold',
                price=df['close'].iloc[-1],
                stop_loss=0,
                take_profit=0,
                confidence=0,
                reason='数据不足，无法计算指标',
                timestamp=datetime.now()
            )
        
        # 获取最新数据
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 当前价格
        price = current['close']
        
        # 信号条件
        signals = []
        
        # 条件1：EMA金叉/死叉
        ema_cross_up = prev['ema_short'] <= prev['ema_long'] and current['ema_short'] > current['ema_long']
        ema_cross_down = prev['ema_short'] >= prev['ema_long'] and current['ema_short'] < current['ema_long']
        
        # 条件2：RSI超买超卖
        rsi_oversold = current['rsi'] < self.config['rsi_oversold']
        rsi_overbought = current['rsi'] > self.config['rsi_overbought']
        
        # 条件3：布林带突破
        bb_break_up = current['close'] > current['bb_upper']
        bb_break_down = current['close'] < current['bb_lower']
        
        # 条件4：MACD金叉/死叉
        macd_cross_up = prev['macd'] <= prev['macd_signal'] and current['macd'] > current['macd_signal']
        macd_cross_down = prev['macd'] >= prev['macd_signal'] and current['macd'] < current['macd_signal']
        
        # 条件5：成交量放大
        volume_surge = current['volume'] > current['volume_ma'] * 1.5
        
        # 综合判断
        buy_signals = []
        sell_signals = []
        
        # 买入信号
        if ema_cross_up:
            buy_signals.append(('EMA金叉', 0.7))
        if rsi_oversold:
            buy_signals.append(('RSI超卖', 0.6))
        if bb_break_down:
            buy_signals.append(('布林带下轨突破', 0.5))
        if macd_cross_up:
            buy_signals.append(('MACD金叉', 0.6))
        if volume_surge and price > current['ema_short']:
            buy_signals.append(('放量上涨', 0.5))
        
        # 卖出信号
        if ema_cross_down:
            sell_signals.append(('EMA死叉', 0.7))
        if rsi_overbought:
            sell_signals.append(('RSI超买', 0.6))
        if bb_break_up:
            sell_signals.append(('布林带上轨突破', 0.5))
        if macd_cross_down:
            sell_signals.append(('MACD死叉', 0.6))
        if volume_surge and price < current['ema_short']:
            sell_signals.append(('放量下跌', 0.5))
        
        # 计算综合置信度
        buy_confidence = sum(c for _, c in buy_signals) / max(len(buy_signals), 1)
        sell_confidence = sum(c for _, c in sell_signals) / max(len(sell_signals), 1)
        
        # 生成信号
        if buy_confidence > 0.5 and buy_confidence > sell_confidence:
            # 买入信号
            stop_loss = price * 0.97  # 3%止损
            take_profit = price * 1.06  # 6%止盈
            reason = ' + '.join([r for r, _ in buy_signals])
            
            return Signal(
                symbol=symbol,
                signal_type='buy',
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=buy_confidence,
                reason=reason,
                timestamp=datetime.now()
            )
        
        elif sell_confidence > 0.5 and sell_confidence > buy_confidence:
            # 卖出信号
            stop_loss = price * 1.03  # 3%止损
            take_profit = price * 0.94  # 6%止盈
            reason = ' + '.join([r for r, _ in sell_signals])
            
            return Signal(
                symbol=symbol,
                signal_type='sell',
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=sell_confidence,
                reason=reason,
                timestamp=datetime.now()
            )
        
        else:
            # 观望
            return Signal(
                symbol=symbol,
                signal_type='hold',
                price=price,
                stop_loss=0,
                take_profit=0,
                confidence=0,
                reason='无明确信号',
                timestamp=datetime.now()
            )


class EventStrategy:
    """事件驱动策略"""
    
    def __init__(self, config: Dict = None):
        """初始化策略"""
        self.config = config or {
            'whale_threshold': 1000000,
            'social_multiplier': 3,
            'funding_rate_threshold': 0.001,
        }
        logger.info("事件驱动策略初始化完成")
    
    def check_whale_transfer(self, transfers: List[Dict]) -> Optional[Signal]:
        """检查大额转账"""
        for transfer in transfers:
            if transfer['amount'] >= self.config['whale_threshold']:
                # 大额转入交易所可能是抛压
                if transfer.get('is_exchange_inflow'):
                    return Signal(
                        symbol=transfer.get('token', 'UNKNOWN'),
                        signal_type='sell',
                        price=0,
                        stop_loss=0,
                        take_profit=0,
                        confidence=0.6,
                        reason=f"大额转入交易所: {transfer['amount']} USDT",
                        timestamp=datetime.now()
                    )
        return None
    
    def check_funding_rate(self, funding_rate: float, symbol: str) -> Optional[Signal]:
        """检查资金费率异常"""
        if abs(funding_rate) >= self.config['funding_rate_threshold']:
            if funding_rate > 0:
                # 正费率过高，可能见顶
                return Signal(
                    symbol=symbol,
                    signal_type='sell',
                    price=0,
                    stop_loss=0,
                    take_profit=0,
                    confidence=0.5,
                    reason=f"资金费率过高: {funding_rate:.4%}",
                    timestamp=datetime.now()
                )
            else:
                # 负费率过高，可能见底
                return Signal(
                    symbol=symbol,
                    signal_type='buy',
                    price=0,
                    stop_loss=0,
                    take_profit=0,
                    confidence=0.5,
                    reason=f"资金费率过低: {funding_rate:.4%}",
                    timestamp=datetime.now()
                )
        return None
    
    def check_social_sentiment(self, sentiment_data: Dict, symbol: str) -> Optional[Signal]:
        """检查社交情绪"""
        current_mentions = sentiment_data.get('mention_count', 0)
        avg_mentions = sentiment_data.get('avg_mentions', 0)
        
        if avg_mentions > 0 and current_mentions > avg_mentions * self.config['social_multiplier']:
            sentiment_score = sentiment_data.get('sentiment_score', 0)
            
            if sentiment_score > 0.5:
                return Signal(
                    symbol=symbol,
                    signal_type='buy',
                    price=0,
                    stop_loss=0,
                    take_profit=0,
                    confidence=0.4,
                    reason=f"社交热度飙升: {current_mentions} (均值: {avg_mentions})",
                    timestamp=datetime.now()
                )
        return None


class StrategyEngine:
    """策略引擎"""
    
    def __init__(self, config: Dict = None):
        """初始化策略引擎"""
        self.trend_strategy = TrendStrategy(config)
        self.event_strategy = EventStrategy(config)
        logger.info("策略引擎初始化完成")
    
    def analyze(self, symbol: str, klines: List, 
                funding_rate: float = None,
                whale_transfers: List[Dict] = None,
                social_sentiment: Dict = None) -> Signal:
        """综合分析
        
        Args:
            symbol: 交易对
            klines: K线数据
            funding_rate: 资金费率
            whale_transfers: 大额转账数据
            social_sentiment: 社交情绪数据
            
        Returns:
            综合信号
        """
        signals = []
        
        # 趋势策略信号
        trend_signal = self.trend_strategy.generate_signal(klines, symbol)
        if trend_signal.signal_type != 'hold':
            signals.append(trend_signal)
        
        # 事件策略信号
        if funding_rate is not None:
            event_signal = self.event_strategy.check_funding_rate(funding_rate, symbol)
            if event_signal:
                signals.append(event_signal)
        
        if whale_transfers:
            whale_signal = self.event_strategy.check_whale_transfer(whale_transfers)
            if whale_signal:
                signals.append(whale_signal)
        
        if social_sentiment:
            social_signal = self.event_strategy.check_social_sentiment(social_sentiment, symbol)
            if social_signal:
                signals.append(social_signal)
        
        # 综合判断
        if not signals:
            return Signal(
                symbol=symbol,
                signal_type='hold',
                price=klines[-1][4] if klines else 0,
                stop_loss=0,
                take_profit=0,
                confidence=0,
                reason='无信号',
                timestamp=datetime.now()
            )
        
        # 取置信度最高的信号
        best_signal = max(signals, key=lambda s: s.confidence)
        return best_signal


# 使用示例
if __name__ == '__main__':
    # 创建策略引擎
    engine = StrategyEngine()
    
    # 模拟K线数据
    import random
    klines = []
    base_price = 0.1
    for i in range(100):
        timestamp = 1717000000000 + i * 3600000
        open_price = base_price + random.uniform(-0.01, 0.01)
        high_price = open_price + random.uniform(0, 0.02)
        low_price = open_price - random.uniform(0, 0.02)
        close_price = open_price + random.uniform(-0.01, 0.01)
        volume = random.uniform(1000, 10000)
        klines.append([timestamp, open_price, high_price, low_price, close_price, volume])
        base_price = close_price
    
    # 生成信号
    signal = engine.analyze('DOGE/USDT', klines)
    print(f"信号: {signal.signal_type}")
    print(f"价格: {signal.price}")
    print(f"止损: {signal.stop_loss}")
    print(f"止盈: {signal.take_profit}")
    print(f"置信度: {signal.confidence}")
    print(f"原因: {signal.reason}")