"""
EMA + RSI 优化策略（乔布斯×孙宇晨版）
======================================

核心思想：
- 乔布斯：极简信号，只看关键指标
- 孙宇晨：浮盈加仓，让利润奔跑

优化要点：
1. 动态仓位：信号强度决定仓位大小
2. 浮盈加仓：盈利5%加10%仓位
3. 冷却期：平仓后等12小时再开仓
4. 杠杆：2-3x（适度激进）
5. 止损：5%（给波动空间）
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from . import Strategy, Signal


class EMARsiOptimizedStrategy(Strategy):
    """EMA + RSI 优化策略"""
    
    name = "ema_rsi_optimized"
    description = "EMA+RSI优化版 - 动态仓位+浮盈加仓"
    version = "2.0.0"
    
    default_params = {
        # 基础参数
        'ema_fast': 20,
        'ema_slow': 50,
        'rsi_period': 14,
        'rsi_oversold': 35,      # 放宽到35（原30）
        'rsi_overbought': 65,    # 放宽到65（原70）
        
        # 信号阈值
        'buy_threshold': 60,     # 降低买入门槛（原65）
        'sell_threshold': 45,    # 提高卖出门槛（原40）
        
        # 仓位管理（乔布斯式简化）
        'position_size_min': 0.15,   # 最小仓位15%
        'position_size_max': 0.40,   # 最大仓位40%
        
        # 杠杆（孙宇晨式适度激进）
        'leverage': 3,           # 3倍杠杆
        
        # 止损止盈
        'stop_loss_pct': 0.05,   # 5%止损
        'take_profit_pct': 0.12, # 12%止盈（让利润奔跑）
        
        # 浮盈加仓（利弗莫尔精华）
        'add_position_threshold': 0.05,  # 浮盈5%加仓
        'add_position_size': 0.10,       # 加仓10%
        
        # 冷却期
        'cooldown_hours': 12,    # 平仓后等12小时
    }
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.last_trade_time = {}  # 记录每个币种最后交易时间
    
    def generate_signal(self, symbol: str, klines: List, current_price: float, 
                       position: Dict = None) -> Optional[Signal]:
        """生成交易信号
        
        Args:
            symbol: 交易对
            klines: K线数据
            current_price: 当前价格
            position: 当前持仓信息 {'entry_price': float, 'size': float, 'entry_time': datetime}
        """
        if len(klines) < 50:
            return None
        
        # 检查冷却期
        if self._in_cooldown(symbol):
            return Signal(
                action='hold',
                symbol=symbol,
                price=current_price,
                score=50,
                reason=f"冷却期中，等待{self.params['cooldown_hours']}小时",
                metadata={'cooldown': True}
            )
        
        closes = [k[4] for k in klines]
        
        # 计算指标
        ema_fast = self._calculate_ema(closes, self.params['ema_fast'])
        ema_slow = self._calculate_ema(closes, self.params['ema_slow'])
        rsi = self._calculate_rsi(closes, self.params['rsi_period'])
        price_position = self._calc_price_position(closes, current_price)
        
        # 计算信号得分（乔布斯式：简单直接）
        score = 50
        
        # 1. EMA趋势（权重最高）
        if ema_fast > ema_slow:
            score += 15  # 多头排列
        else:
            score -= 15  # 空头排列
        
        # 2. RSI超买超卖
        if rsi < self.params['rsi_oversold']:
            score += 20  # 超卖，强烈看多
        elif rsi > self.params['rsi_overbought']:
            score -= 20  # 超买，强烈看空
        elif rsi < 45:
            score += 5   # 偏低
        elif rsi > 55:
            score -= 5   # 偏高
        
        # 3. 价格位置（均值回归）
        if price_position < 0.25:
            score += 10  # 低位
        elif price_position > 0.75:
            score -= 10  # 高位
        
        # 限制得分范围
        score = max(0, min(100, score))
        
        # 计算动态仓位（信号越强，仓位越大）
        position_size = self._calc_position_size(score)
        
        # 生成信号
        action = 'hold'
        reason = f"观望 score={score}"
        
        # 有持仓时的处理
        if position:
            entry_price = position.get('entry_price', current_price)
            pnl_pct = (current_price - entry_price) / entry_price
            
            # 浮盈加仓逻辑
            if (pnl_pct >= self.params['add_position_threshold'] and 
                score >= 65 and 
                position.get('added', False) == False):
                action = 'add_position'
                reason = f"浮盈{pnl_pct:.1%}，加仓！"
            
            # 止盈
            elif pnl_pct >= self.params['take_profit_pct']:
                action = 'sell'
                reason = f"止盈 {pnl_pct:.1%}"
            
            # 止损
            elif pnl_pct <= -self.params['stop_loss_pct']:
                action = 'sell'
                reason = f"止损 {pnl_pct:.1%}"
            
            # 趋势反转卖出
            elif score <= self.params['sell_threshold']:
                action = 'sell'
                reason = f"趋势反转 score={score}"
        
        # 无持仓时的买入逻辑
        else:
            if score >= self.params['buy_threshold']:
                action = 'buy'
                reason = f"EMA多头 RSI={rsi:.1f} 仓位={position_size:.0%}"
        
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
                'price_position': price_position,
                'position_size': position_size,
                'leverage': self.params['leverage'],
            }
        )
    
    def _calc_position_size(self, score: int) -> float:
        """根据信号强度计算动态仓位
        
        乔布斯式：简单线性映射
        - score 60 → 15%仓位
        - score 80 → 30%仓位
        - score 100 → 40%仓位
        """
        min_size = self.params['position_size_min']
        max_size = self.params['position_size_max']
        
        # 线性映射：score 60-100 → position 15%-40%
        if score <= 60:
            return 0
        elif score >= 100:
            return max_size
        else:
            ratio = (score - 60) / 40
            return min_size + ratio * (max_size - min_size)
    
    def _calc_price_position(self, closes: List[float], current_price: float) -> float:
        """计算价格在20日高低点中的位置"""
        high_20 = max(closes[-20:])
        low_20 = min(closes[-20:])
        if high_20 == low_20:
            return 0.5
        return (current_price - low_20) / (high_20 - low_20)
    
    def _in_cooldown(self, symbol: str) -> bool:
        """检查是否在冷却期"""
        if symbol not in self.last_trade_time:
            return False
        
        elapsed = datetime.now() - self.last_trade_time[symbol]
        cooldown = timedelta(hours=self.params['cooldown_hours'])
        return elapsed < cooldown
    
    def record_trade(self, symbol: str):
        """记录交易时间"""
        self.last_trade_time[symbol] = datetime.now()
    
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
