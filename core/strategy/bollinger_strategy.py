"""
布林带策略
==========

使用布林带指标生成交易信号。

信号逻辑：
- 价格触及下轨：超卖，买入信号
- 价格触及上轨：超买，卖出信号
- 布林带收窄：可能突破
"""

from typing import List, Optional, Dict, Any
from core.strategy.base_types import Strategy, Signal


class BollingerStrategy(Strategy):
    """布林带策略"""
    
    name = "bollinger"
    description = "布林带指标策略"
    version = "1.0.0"
    
    default_params = {
        'stop_loss_pct': 0.05,
        'take_profit_pct': 0.08,
        'buy_threshold': 65,
        'sell_threshold': 35,
        'position_size': 0.2,
        'bb_period': 20,
        'bb_std': 2.0
    }
    
    def generate_signal(self, symbol: str, klines: List, current_price: float) -> Optional[Signal]:
        """生成信号"""
        if len(klines) < 20:
            return None
        
        closes = [k[4] for k in klines]
        
        # 计算布林带
        middle, upper, lower = self._calculate_bollinger(closes)
        
        # 计算价格在布林带中的位置
        bb_width = upper - lower
        if bb_width == 0:
            bb_position = 0.5
        else:
            bb_position = (current_price - lower) / bb_width
        
        # 计算带宽（波动性）
        bb_bandwidth = bb_width / middle if middle > 0 else 0
        
        # 计算得分
        score = 50
        
        # 价格位置信号
        if bb_position < 0.2:
            score += 20  # 接近下轨，超卖
        elif bb_position > 0.8:
            score -= 20  # 接近上轨，超买
        
        # 布林带宽度信号
        if bb_bandwidth < 0.05:
            # 带宽收窄，可能突破
            if current_price > middle:
                score += 5  # 向上突破概率
            else:
                score -= 5  # 向下突破概率
        
        # 限制在 0-100
        score = max(0, min(100, score))
        
        # 生成信号
        if score >= self.params['buy_threshold']:
            action = 'buy'
            reason = f"触及下轨, bb_position={bb_position:.2f}"
        elif score <= self.params['sell_threshold']:
            action = 'sell'
            reason = f"触及上轨, bb_position={bb_position:.2f}"
        else:
            action = 'hold'
            reason = f"带内运行, bb_position={bb_position:.2f}"
        
        return Signal(
            action=action,
            symbol=symbol,
            price=current_price,
            score=score,
            reason=reason,
            metadata={
                'bb_middle': middle,
                'bb_upper': upper,
                'bb_lower': lower,
                'bb_position': bb_position,
                'bb_bandwidth': bb_bandwidth
            }
        )
    
    def _calculate_bollinger(self, data: List[float]) -> tuple:
        """计算布林带"""
        period = self.params['bb_period']
        std_dev = self.params['bb_std']
        
        if len(data) < period:
            return data[-1], data[-1], data[-1]
        
        # 中轨（SMA）
        recent = data[-period:]
        middle = sum(recent) / period
        
        # 标准差
        variance = sum((x - middle) ** 2 for x in recent) / period
        std = variance ** 0.5
        
        # 上下轨
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        
        return middle, upper, lower
