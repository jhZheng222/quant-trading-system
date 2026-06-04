"""
多策略引擎
==========

集成多个子策略，根据市场状态自动选择最优策略。

策略组合：
1. 利弗莫尔（趋势跟踪）- 趋势行情
2. 资金费率套利 - 震荡市
3. 波动率突破 - 盘整末期
4. 反向收割 - 极端情绪
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from . import Strategy, Signal


class MarketRegime(Enum):
    """市场状态"""
    TRENDING_UP = "trending_up"     # 上升趋势
    TRENDING_DOWN = "trending_down" # 下降趋势
    RANGING = "ranging"             # 震荡盘整
    VOLATILE = "volatile"           # 高波动


class MultiStrategy(Strategy):
    """多策略引擎"""
    
    name = "multi"
    description = "多策略自适应引擎 - 根据市场状态切换策略"
    version = "1.0.0"
    
    default_params = {
        'stop_loss_pct': 0.05,
        'take_profit_pct': 0.15,
        'buy_threshold': 60,
        'sell_threshold': 40,
        'position_size': 0.20,
        'ema_fast': 20,
        'ema_slow': 50,
        'atr_period': 14,
        'adx_period': 14,
        'adx_trend_threshold': 25,   # ADX>25 认为趋势
        'volatility_threshold': 0.02 # 波动率阈值
    }
    
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        # 子策略权重
        self.strategy_weights = {
            MarketRegime.TRENDING_UP: {'trend': 0.6, 'breakout': 0.2, 'contrarian': 0.2},
            MarketRegime.TRENDING_DOWN: {'trend': 0.6, 'breakout': 0.2, 'contrarian': 0.2},
            MarketRegime.RANGING: {'trend': 0.2, 'breakout': 0.3, 'contrarian': 0.5},
            MarketRegime.VOLATILE: {'trend': 0.3, 'breakout': 0.5, 'contrarian': 0.2}
        }
    
    def generate_signal(self, symbol: str, klines: List, current_price: float) -> Optional[Signal]:
        """生成信号"""
        if len(klines) < 50:
            return None
        
        closes = [k[4] for k in klines]
        highs = [k[2] for k in klines]
        lows = [k[3] for k in klines]
        
        # 1. 判断市场状态
        regime = self._detect_regime(closes, highs, lows)
        
        # 2. 获取各子策略信号
        trend_signal = self._trend_strategy(closes, current_price)
        breakout_signal = self._breakout_strategy(closes, highs, lows, current_price)
        contrarian_signal = self._contrarian_strategy(closes, current_price)
        
        # 3. 根据市场状态加权
        weights = self.strategy_weights[regime]
        
        score = 50
        reasons = []
        
        if trend_signal:
            score += trend_signal * weights['trend'] * 30
            if abs(trend_signal) > 0.3:
                reasons.append(f"趋势{'多' if trend_signal > 0 else '空'}")
        
        if breakout_signal:
            score += breakout_signal * weights['breakout'] * 25
            if abs(breakout_signal) > 0.3:
                reasons.append("突破")
        
        if contrarian_signal:
            score += contrarian_signal * weights['contrarian'] * 20
            if abs(contrarian_signal) > 0.3:
                reasons.append("反转")
        
        # 限制在 0-100
        score = max(0, min(100, score))
        
        # 生成信号
        if score >= self.params['buy_threshold']:
            action = 'buy'
        elif score <= self.params['sell_threshold']:
            action = 'sell'
        else:
            action = 'hold'
        
        reason = f"{regime.value}: {', '.join(reasons) if reasons else '观望'}"
        
        return Signal(
            action=action,
            symbol=symbol,
            price=current_price,
            score=score,
            reason=reason,
            metadata={
                'regime': regime.value,
                'trend_signal': trend_signal,
                'breakout_signal': breakout_signal,
                'contrarian_signal': contrarian_signal
            }
        )
    
    def _detect_regime(self, closes: List[float], highs: List[float], lows: List[float]) -> MarketRegime:
        """检测市场状态"""
        # 计算 ADX（趋势强度）
        adx = self._calculate_adx(highs, lows, closes)
        
        # 计算 ATR（波动率）
        atr = self._calculate_atr(highs, lows, closes)
        atr_pct = atr / closes[-1] if closes[-1] > 0 else 0
        
        # 计算趋势方向
        ema_fast = self._calculate_ema(closes, self.params['ema_fast'])
        ema_slow = self._calculate_ema(closes, self.params['ema_slow'])
        
        # 判断状态
        if atr_pct > self.params['volatility_threshold']:
            return MarketRegime.VOLATILE
        elif adx > self.params['adx_trend_threshold']:
            if ema_fast > ema_slow:
                return MarketRegime.TRENDING_UP
            else:
                return MarketRegime.TRENDING_DOWN
        else:
            return MarketRegime.RANGING
    
    def _trend_strategy(self, closes: List[float], current_price: float) -> float:
        """趋势策略信号 [-1, 1]"""
        ema_fast = self._calculate_ema(closes, self.params['ema_fast'])
        ema_slow = self._calculate_ema(closes, self.params['ema_slow'])
        
        # 趋势强度
        trend_strength = (ema_fast - ema_slow) / ema_slow if ema_slow > 0 else 0
        
        # 归一化到 [-1, 1]
        return max(-1, min(1, trend_strength * 10))
    
    def _breakout_strategy(self, closes: List[float], highs: List[float], lows: List[float], 
                           current_price: float) -> float:
        """突破策略信号 [-1, 1]"""
        # 计算布林带
        period = 20
        if len(closes) < period:
            return 0
        
        recent = closes[-period:]
        middle = sum(recent) / period
        std = (sum((x - middle) ** 2 for x in recent) / period) ** 0.5
        
        upper = middle + 2 * std
        lower = middle - 2 * std
        
        # 突破信号
        if current_price > upper:
            return 0.8  # 突破上轨
        elif current_price < lower:
            return -0.8  # 突破下轨
        elif current_price > middle:
            return 0.3  # 中轨上方
        else:
            return -0.3  # 中轨下方
    
    def _contrarian_strategy(self, closes: List[float], current_price: float) -> float:
        """反向策略信号 [-1, 1]"""
        # RSI 超买超卖
        rsi = self._calculate_rsi(closes, 14)
        
        if rsi < 30:
            return 0.7  # 超卖，看涨
        elif rsi > 70:
            return -0.7  # 超买，看跌
        elif rsi < 40:
            return 0.3
        elif rsi > 60:
            return -0.3
        else:
            return 0
    
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
    
    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], 
                       period: int = 14) -> float:
        """计算 ATR"""
        if len(highs) < period + 1:
            return 0
        
        tr_list = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
        
        return sum(tr_list[-period:]) / period
    
    def _calculate_adx(self, highs: List[float], lows: List[float], closes: List[float], 
                       period: int = 14) -> float:
        """计算 ADX（简化版）"""
        if len(highs) < period + 1:
            return 0
        
        # 计算方向运动
        plus_dm = []
        minus_dm = []
        
        for i in range(1, len(highs)):
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            
            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
            else:
                plus_dm.append(0)
            
            if down_move > up_move and down_move > 0:
                minus_dm.append(down_move)
            else:
                minus_dm.append(0)
        
        # 计算 ATR
        atr = self._calculate_atr(highs, lows, closes, period)
        if atr == 0:
            return 0
        
        # 计算 +DI 和 -DI
        plus_di = (sum(plus_dm[-period:]) / period) / atr * 100
        minus_di = (sum(minus_dm[-period:]) / period) / atr * 100
        
        # 计算 DX
        if plus_di + minus_di == 0:
            return 0
        
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
        
        return dx
