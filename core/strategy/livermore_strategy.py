"""
利弗莫尔策略
============

核心思想：浮盈加仓 + 严格止损 + 趋势确认

策略逻辑：
1. 用20%资金建底仓
2. 浮盈>trigger_pct → 加仓20%
3. 再浮盈>trigger_pct → 加仓20%
4. 趋势确认 → 加仓40%（满仓）
5. 任何时候亏损>stop_pct → 全部清仓

参考：杰西·利弗莫尔《股票大作手操盘术》
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from core.strategy.base_types import Strategy, Signal


class LivermoreStage(Enum):
    """利弗莫尔仓位阶段"""
    EMPTY = "empty"           # 空仓
    BASE = "base"             # 底仓（20%）
    ADD1 = "add1"             # 第一次加仓（40%）
    ADD2 = "add2"             # 第二次加仓（60%）
    FULL = "full"             # 满仓（100%）


class LivermoreStrategy(Strategy):
    """利弗莫尔策略"""
    
    name = "livermore"
    description = "利弗莫尔浮盈加仓策略 - 趋势跟踪"
    version = "1.0.0"
    
    default_params = {
        'stop_loss_pct': 0.07,       # 止损 7%
        'take_profit_pct': 0.20,     # 止盈 20%
        'trigger_pct': 0.05,         # 加仓触发 5%
        'base_ratio': 0.20,          # 底仓比例 20%
        'add_ratio': 0.20,           # 每次加仓比例 20%
        'position_size': 0.20,       # 总仓位限制
        'ema_fast': 20,
        'ema_slow': 50,
        'trend_confirm': True        # 是否需要趋势确认
    }
    
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        # 持仓状态（用于跟踪加仓阶段）
        self.positions: Dict[str, Dict] = {}
    
    def generate_signal(self, symbol: str, klines: List, current_price: float) -> Optional[Signal]:
        """生成信号"""
        if len(klines) < 50:
            return None
        
        closes = [k[4] for k in klines]
        
        # 计算趋势
        ema_fast = self._calculate_ema(closes, self.params['ema_fast'])
        ema_slow = self._calculate_ema(closes, self.params['ema_slow'])
        trend_up = ema_fast > ema_slow
        
        # 计算 RSI（辅助判断）
        rsi = self._calculate_rsi(closes, 14)
        
        # 获取当前持仓状态
        position = self.positions.get(symbol, {'stage': 'empty', 'entry_price': 0, 'avg_price': 0})
        stage = position['stage']
        
        # 生成信号
        if stage == 'empty':
            # 空仓状态：寻找入场机会
            if trend_up and rsi < 40:
                return Signal(
                    action='buy',
                    symbol=symbol,
                    price=current_price,
                    score=70,
                    reason=f"利弗莫尔建仓: EMA多头, RSI={rsi:.1f}",
                    metadata={'stage': 'base', 'stage_name': '底仓'}
                )
        else:
            # 持仓状态：检查加仓或止损
            entry_price = position['entry_price']
            pnl_pct = (current_price - entry_price) / entry_price
            
            # 止损检查
            if pnl_pct < -self.params['stop_loss_pct']:
                # 清仓
                self.positions.pop(symbol, None)
                return Signal(
                    action='sell',
                    symbol=symbol,
                    price=current_price,
                    score=90,
                    reason=f"利弗莫尔止损: 亏损={pnl_pct*100:.1f}%",
                    metadata={'stage': 'stopped'}
                )
            
            # 止盈检查
            if pnl_pct > self.params['take_profit_pct']:
                self.positions.pop(symbol, None)
                return Signal(
                    action='sell',
                    symbol=symbol,
                    price=current_price,
                    score=90,
                    reason=f"利弗莫尔止盈: 盈利={pnl_pct*100:.1f}%",
                    metadata={'stage': 'profit'}
                )
            
            # 加仓检查
            trigger = self.params['trigger_pct']
            
            if stage == 'base' and pnl_pct > trigger:
                # 底仓盈利，加仓到40%
                if not self.params['trend_confirm'] or trend_up:
                    self.positions[symbol] = {'stage': 'add1', 'entry_price': entry_price, 'avg_price': current_price}
                    return Signal(
                        action='buy',
                        symbol=symbol,
                        price=current_price,
                        score=75,
                        reason=f"利弗莫尔加仓1: 盈利={pnl_pct*100:.1f}%, 加仓到40%",
                        metadata={'stage': 'add1', 'stage_name': '第一次加仓'}
                    )
            
            elif stage == 'add1' and pnl_pct > trigger * 2:
                # 第一次加仓盈利，加仓到60%
                if not self.params['trend_confirm'] or trend_up:
                    self.positions[symbol] = {'stage': 'add2', 'entry_price': entry_price, 'avg_price': current_price}
                    return Signal(
                        action='buy',
                        symbol=symbol,
                        price=current_price,
                        score=80,
                        reason=f"利弗莫尔加仓2: 盈利={pnl_pct*100:.1f}%, 加仓到60%",
                        metadata={'stage': 'add2', 'stage_name': '第二次加仓'}
                    )
            
            elif stage == 'add2' and pnl_pct > trigger * 3:
                # 第二次加仓盈利，满仓
                if trend_up:
                    self.positions[symbol] = {'stage': 'full', 'entry_price': entry_price, 'avg_price': current_price}
                    return Signal(
                        action='buy',
                        symbol=symbol,
                        price=current_price,
                        score=85,
                        reason=f"利弗莫尔满仓: 盈利={pnl_pct*100:.1f}%, 趋势确认",
                        metadata={'stage': 'full', 'stage_name': '满仓'}
                    )
        
        return None
    
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
    
    def update_position(self, symbol: str, stage: str, entry_price: float):
        """更新持仓状态（外部调用）"""
        self.positions[symbol] = {
            'stage': stage,
            'entry_price': entry_price,
            'avg_price': entry_price
        }
    
    def clear_position(self, symbol: str):
        """清除持仓状态"""
        self.positions.pop(symbol, None)
