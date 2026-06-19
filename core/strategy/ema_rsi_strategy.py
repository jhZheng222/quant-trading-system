"""
EMA + RSI 策略
==============

使用 EMA 均线和 RSI 指标生成交易信号。

信号逻辑：
- EMA20 > EMA50：多头排列，得分+10
- EMA20 < EMA50：空头排列，得分-10
- RSI < 30：超卖，得分+15
- RSI > 70：超买，得分-15
- 价格在低位：得分+10
- 价格在高位：得分-10
"""

from typing import List, Optional, Dict, Any
from core.strategy.base_types import Strategy, Signal


class EMARsiStrategy(Strategy):
    """EMA + RSI 策略"""
    
    name = "ema_rsi"
    description = "EMA均线 + RSI指标策略"
    version = "1.0.0"
    
    default_params = {
        'stop_loss_pct': 0.05,
        'take_profit_pct': 0.08,
        'buy_threshold': 65,
        'sell_threshold': 40,
        'position_size': 0.2,
        'ema_fast': 20,
        'ema_slow': 50,
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70
    }
    
    def generate_signal(self, symbol: str, klines: List, current_price: float) -> Optional[Signal]:
        """生成信号"""
        if len(klines) < 50:
            return None
        
        closes = [k[4] for k in klines]
        
        # 计算 EMA
        ema_fast = self._calculate_ema(closes, self.params['ema_fast'])
        ema_slow = self._calculate_ema(closes, self.params['ema_slow'])
        
        # 计算 RSI
        rsi = self._calculate_rsi(closes, self.params['rsi_period'])
        
        # 计算价格位置
        high_20 = max(closes[-20:])
        low_20 = min(closes[-20:])
        price_position = (current_price - low_20) / (high_20 - low_20) if high_20 != low_20 else 0.5
        
        # 计算得分
        score = 50
        
        # EMA 信号
        if ema_fast > ema_slow:
            score += 10  # 多头排列
        else:
            score -= 10  # 空头排列
        
        # RSI 信号
        if rsi < self.params['rsi_oversold']:
            score += 15  # 超卖
        elif rsi > self.params['rsi_overbought']:
            score -= 15  # 超买
        
        # 价格位置信号
        if price_position < 0.2:
            score += 10  # 低位
        elif price_position > 0.8:
            score -= 10  # 高位
        
        # 限制在 0-100
        score = max(0, min(100, score))
        
        # 生成信号
        if score >= self.params['buy_threshold']:
            action = 'buy'
            reason = f"EMA多头, RSI={rsi:.1f}"
        elif score <= self.params['sell_threshold']:
            action = 'sell'
            reason = f"EMA空头, RSI={rsi:.1f}"
        else:
            action = 'hold'
            reason = f"观望, score={score}"
        
        return Signal(
            action=action,
            symbol=symbol,
            price=current_price,
            score=score,
            reason=reason,
            metadata={
                'ema_fast': ema_fast,
                'ema_slow': ema_slow,
                'rsi': rsi,
                'price_position': price_position
            }
        )
    
    def _calculate_ema(self, data: List[float], period: int) -> float:
        """计算 EMA"""
        if len(data) < period:
            return data[-1]
        
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_rsi(self, data: List[float], period: int = 14) -> float:
        """计算 RSI"""
        if len(data) < period + 1:
            return 50
        
        deltas = [data[i] - data[i-1] for i in range(1, len(data))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
