"""
MACD 策略
=========

使用 MACD 指标生成交易信号。

信号逻辑：
- MACD 金叉：买入信号
- MACD 死叉：卖出信号
- MACD 柱状图：确认趋势强度
"""

from typing import List, Optional, Dict, Any
from core.strategy.base_types import Strategy, Signal


class MACDStrategy(Strategy):
    """MACD 策略"""
    
    name = "macd"
    description = "MACD 指标策略"
    version = "1.0.0"
    
    default_params = {
        'stop_loss_pct': 0.05,
        'take_profit_pct': 0.10,
        'buy_threshold': 60,
        'sell_threshold': 40,
        'position_size': 0.2,
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9
    }
    
    def generate_signal(self, symbol: str, klines: List, current_price: float) -> Optional[Signal]:
        """生成信号"""
        if len(klines) < 30:
            return None
        
        closes = [k[4] for k in klines]
        
        # 计算 MACD
        macd_line, signal_line, histogram = self._calculate_macd(closes)
        
        # 计算得分
        score = 50
        
        # MACD 金叉/死叉
        if macd_line > signal_line:
            score += 15  # 金叉
        else:
            score -= 15  # 死叉
        
        # MACD 柱状图
        if histogram > 0:
            score += 10  # 正柱
        else:
            score -= 10  # 负柱
        
        # MACD 趋势
        if macd_line > 0:
            score += 5   # 多头区域
        else:
            score -= 5   # 空头区域
        
        # 限制在 0-100
        score = max(0, min(100, score))
        
        # 生成信号
        if score >= self.params['buy_threshold']:
            action = 'buy'
            reason = f"MACD金叉, histogram={histogram:.4f}"
        elif score <= self.params['sell_threshold']:
            action = 'sell'
            reason = f"MACD死叉, histogram={histogram:.4f}"
        else:
            action = 'hold'
            reason = f"观望, MACD={macd_line:.4f}"
        
        return Signal(
            action=action,
            symbol=symbol,
            price=current_price,
            score=score,
            reason=reason,
            metadata={
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
        )
    
    def _calculate_macd(self, data: List[float]) -> tuple:
        """计算 MACD"""
        fast = self.params['fast_period']
        slow = self.params['slow_period']
        signal = self.params['signal_period']
        
        # 计算快速和慢速 EMA
        ema_fast = self._calculate_ema(data, fast)
        ema_slow = self._calculate_ema(data, slow)
        
        # MACD 线
        macd_line = ema_fast - ema_slow
        
        # 信号线（MACD 的 EMA）
        # 简化处理：使用最后几个值
        macd_values = []
        for i in range(min(30, len(data))):
            idx = len(data) - 30 + i
            if idx >= 0:
                ef = self._calculate_ema(data[:idx+1], fast)
                es = self._calculate_ema(data[:idx+1], slow)
                macd_values.append(ef - es)
        
        signal_line = self._calculate_ema(macd_values, signal) if len(macd_values) >= signal else macd_line
        
        # 柱状图
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_ema(self, data: List[float], period: int) -> float:
        """计算 EMA"""
        if len(data) < period:
            return data[-1]
        
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
