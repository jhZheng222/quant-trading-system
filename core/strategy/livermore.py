"""
利弗莫尔买入法 — 量化策略模块
==============================

核心思想：浮盈加仓 + 严格止损 + 趋势确认

策略逻辑：
1. 用20%资金建底仓
2. 浮盈>trigger_pct → 加仓20%
3. 再浮盈>trigger_pct → 加仓20%
4. 趋势确认 → 加仓40%（满仓）
5. 任何时候亏损>stop_pct → 全部清仓

适配加密货币合约的调整：
- 止损从10%调到7%（币圈波动更大）
- 加仓触发从10%调到5%（合约杠杆放大收益）
- 加入时间止损（持仓超时未达预期减仓）
- 加入趋势确认（EMA/MACD辅助判断）

参考：杰西·利弗莫尔《股票大作手操盘术》
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class LivermoreStage(Enum):
    """利弗莫尔仓位阶段"""
    EMPTY = "empty"           # 空仓
    BASE = "base"             # 底仓（20%）
    ADD1 = "add1"             # 第一次加仓（40%）
    ADD2 = "add2"             # 第二次加仓（60%）
    FULL = "full"             # 满仓（100%）
    STOPPED = "stopped"       # 已止损


@dataclass
class LivermorePosition:
    """利弗莫尔持仓状态"""
    symbol: str
    side: str                          # 'buy' or 'sell'
    stage: LivermoreStage = LivermoreStage.EMPTY
    entry_price: float = 0.0           # 底仓价格
    avg_price: float = 0.0             # 平均价（加权）
    total_amount: float = 0.0          # 总持仓数量
    total_cost: float = 0.0            # 总投入成本（保证金）
    stages: List[Dict] = field(default_factory=list)  # 各阶段记录
    entry_time: str = ""
    last_add_time: str = ""
    highest_pnl_pct: float = 0.0       # 最高浮盈%
    stop_loss: float = 0.0
    trailing_stop: float = 0.0         # 移动止损


@dataclass
class LivermoreConfig:
    """利弗莫尔策略配置"""
    # 仓位分配（占可用资金比例）
    base_ratio: float = 0.20       # 底仓：20%
    add1_ratio: float = 0.20       # 第一次加仓：20%
    add2_ratio: float = 0.20       # 第二次加仓：20%
    full_ratio: float = 0.40       # 满仓加仓：40%
    
    # 触发条件
    trigger_pct: float = 0.05      # 加仓触发：浮盈5%（原版10%，合约调低）
    stop_pct: float = 0.07         # 止损线：亏损7%（原版10%，合约调低）
    trailing_pct: float = 0.03     # 移动止损回撤：3%
    
    # 时间控制
    max_hold_hours: int = 48       # 最大持仓时间（小时）
    time_reduce_hours: int = 24    # 超时减仓时间（小时）
    time_reduce_ratio: float = 0.5 # 超时减仓比例
    
    # 趋势确认
    use_trend_confirm: bool = True # 是否使用趋势确认
    ema_fast: int = 12             # 快EMA
    ema_slow: int = 26             # 慢EMA
    
    # 杠杆
    leverage: int = 10             # 杠杆倍数


class LivermoreStrategy:
    """
    利弗莫尔买入法策略
    
    实现了杰西·利弗莫尔的经典金字塔加仓策略，
    针对加密货币合约市场做了适配优化。
    """
    
    def __init__(self, config: LivermoreConfig = None):
        self.config = config or LivermoreConfig()
        self.positions: Dict[str, LivermorePosition] = {}
        
        # 统计
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
        logger.info("📈 利弗莫尔策略初始化完成")
        logger.info(f"   加仓触发: {self.config.trigger_pct*100}%")
        logger.info(f"   止损线: {self.config.stop_pct*100}%")
        logger.info(f"   杠杆: {self.config.leverage}x")
    
    def evaluate(self, symbol: str, current_price: float,
                 klines: List = None, signal_score: float = 50) -> Dict:
        """
        评估当前情况，返回操作建议
        
        Args:
            symbol: 交易对
            current_price: 当前价格
            klines: K线数据（用于趋势确认）
            signal_score: 信号评分（0-100）
            
        Returns:
            {
                'action': 'open_base'|'add1'|'add2'|'add_full'|'stop'|'hold'|'none',
                'reason': str,
                'position_ratio': float,  # 建议仓位比例
                'position': LivermorePosition
            }
        """
        # 无持仓 → 考虑开底仓
        if symbol not in self.positions or self.positions[symbol].stage == LivermoreStage.EMPTY:
            if signal_score >= 60:  # 信号足够强才开仓
                return {
                    'action': 'open_base',
                    'reason': f'信号评分{signal_score}>=60，开底仓',
                    'position_ratio': self.config.base_ratio,
                    'position': None
                }
            return {'action': 'none', 'reason': f'信号评分{signal_score}<60，观望',
                    'position_ratio': 0, 'position': None}
        
        pos = self.positions[symbol]
        
        # 已止损 → 不操作
        if pos.stage == LivermoreStage.STOPPED:
            return {'action': 'none', 'reason': '已止损，等待下次机会',
                    'position_ratio': 0, 'position': pos}
        
        # 计算当前浮盈
        if pos.side == 'buy':
            pnl_pct = (current_price - pos.avg_price) / pos.avg_price
        else:
            pnl_pct = (pos.avg_price - current_price) / pos.avg_price
        
        # 更新最高浮盈
        pos.highest_pnl_pct = max(pos.highest_pnl_pct, pnl_pct)
        
        # === 止损检查 ===
        if pnl_pct <= -self.config.stop_pct:
            return {
                'action': 'stop',
                'reason': f'浮亏{pnl_pct*100:.1f}%触及止损线-{self.config.stop_pct*100}%',
                'position_ratio': 0,
                'position': pos
            }
        
        # === 移动止损检查（有浮盈后保护利润）===
        if pos.highest_pnl_pct > self.config.trigger_pct:
            drawdown = pos.highest_pnl_pct - pnl_pct
            if drawdown >= self.config.trailing_pct:
                return {
                    'action': 'stop',
                    'reason': f'移动止损：最高浮盈{pos.highest_pnl_pct*100:.1f}%，'
                              f'回撤{drawdown*100:.1f}%>=触发{self.config.trailing_pct*100}%',
                    'position_ratio': 0,
                    'position': pos
                }
        
        # === 时间止损检查 ===
        if pos.entry_time:
            try:
                entry_dt = datetime.fromisoformat(pos.entry_time)
                hold_hours = (datetime.now() - entry_dt).total_seconds() / 3600
                
                if hold_hours >= self.config.max_hold_hours:
                    return {
                        'action': 'stop',
                        'reason': f'持仓{hold_hours:.0f}h超过最大{self.config.max_hold_hours}h',
                        'position_ratio': 0,
                        'position': pos
                    }
                
                if hold_hours >= self.config.time_reduce_hours and pnl_pct < 0.01:
                    return {
                        'action': 'reduce',
                        'reason': f'持仓{hold_hours:.0f}h，浮盈仅{pnl_pct*100:.1f}%，减仓{self.config.time_reduce_ratio*100}%',
                        'position_ratio': -self.config.time_reduce_ratio,
                        'position': pos
                    }
            except:
                pass
        
        # === 加仓检查（浮盈加仓核心逻辑）===
        trend_ok = True
        if self.config.use_trend_confirm and klines:
            trend_ok = self._check_trend(pos.side, klines)
        
        if pos.stage == LivermoreStage.BASE and pnl_pct >= self.config.trigger_pct:
            if trend_ok:
                return {
                    'action': 'add1',
                    'reason': f'浮盈{pnl_pct*100:.1f}%>=触发{self.config.trigger_pct*100}%，第一次加仓',
                    'position_ratio': self.config.add1_ratio,
                    'position': pos
                }
            return {'action': 'hold', 'reason': f'浮盈达标但趋势未确认，等待',
                    'position_ratio': 0, 'position': pos}
        
        if pos.stage == LivermoreStage.ADD1 and pnl_pct >= self.config.trigger_pct * 2:
            if trend_ok:
                return {
                    'action': 'add2',
                    'reason': f'浮盈{pnl_pct*100:.1f}%>=触发{self.config.trigger_pct*200}%，第二次加仓',
                    'position_ratio': self.config.add2_ratio,
                    'position': pos
                }
            return {'action': 'hold', 'reason': f'浮盈达标但趋势未确认，等待',
                    'position_ratio': 0, 'position': pos}
        
        if pos.stage == LivermoreStage.ADD2 and pnl_pct >= self.config.trigger_pct * 3:
            if trend_ok:
                return {
                    'action': 'add_full',
                    'reason': f'趋势确认！浮盈{pnl_pct*100:.1f}%，全力出击',
                    'position_ratio': self.config.full_ratio,
                    'position': pos
                }
            return {'action': 'hold', 'reason': f'浮盈达标但趋势未确认，等待',
                    'position_ratio': 0, 'position': pos}
        
        # === 持仓中，无操作 ===
        return {
            'action': 'hold',
            'reason': f'持仓中，浮盈{pnl_pct*100:.1f}%，阶段={pos.stage.value}',
            'position_ratio': 0,
            'position': pos
        }
    
    def open_position(self, symbol: str, side: str, price: float,
                      amount: float, balance: float) -> LivermorePosition:
        """开底仓"""
        pos = LivermorePosition(
            symbol=symbol,
            side=side,
            stage=LivermoreStage.BASE,
            entry_price=price,
            avg_price=price,
            total_amount=amount,
            total_cost=balance * self.config.base_ratio,
            entry_time=datetime.now().isoformat(),
            stop_loss=price * (1 - self.config.stop_pct) if side == 'buy'
                      else price * (1 + self.config.stop_pct)
        )
        pos.stages.append({
            'stage': 'base',
            'price': price,
            'amount': amount,
            'time': pos.entry_time
        })
        
        self.positions[symbol] = pos
        self.total_trades += 1
        
        logger.info(f"📈 利弗莫尔开底仓 {symbol}: {side} @ {price}, "
                    f"数量={amount:.4f}, 止损={pos.stop_loss:.6f}")
        return pos
    
    def add_position(self, symbol: str, price: float, amount: float,
                     stage: LivermoreStage) -> Optional[LivermorePosition]:
        """加仓"""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        
        # 更新均价
        total_cost = pos.avg_price * pos.total_amount + price * amount
        pos.total_amount += amount
        pos.avg_price = total_cost / pos.total_amount
        pos.total_cost += amount * price / self.config.leverage
        pos.stage = stage
        pos.last_add_time = datetime.now().isoformat()
        
        # 更新止损（移动止损：止损上移到均价-止损%）
        if pos.side == 'buy':
            new_stop = pos.avg_price * (1 - self.config.stop_pct)
            pos.stop_loss = max(pos.stop_loss, new_stop)
        else:
            new_stop = pos.avg_price * (1 + self.config.stop_pct)
            pos.stop_loss = min(pos.stop_loss, new_stop)
        
        pos.stages.append({
            'stage': stage.value,
            'price': price,
            'amount': amount,
            'time': pos.last_add_time
        })
        
        logger.info(f"📈 利弗莫尔加仓 {symbol}: 阶段={stage.value}, "
                    f"价格={price}, 数量={amount:.4f}, 均价={pos.avg_price:.6f}")
        return pos
    
    def close_position(self, symbol: str, price: float, reason: str) -> Optional[Dict]:
        """平仓"""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        
        # 计算盈亏
        if pos.side == 'buy':
            pnl_pct = (price - pos.avg_price) / pos.avg_price
        else:
            pnl_pct = (pos.avg_price - price) / pos.avg_price
        
        pnl_amount = pos.total_cost * pnl_pct * self.config.leverage
        
        # 统计
        self.total_pnl += pnl_amount
        if pnl_amount > 0:
            self.winning_trades += 1
        
        result = {
            'symbol': symbol,
            'side': pos.side,
            'entry_price': pos.entry_price,
            'avg_price': pos.avg_price,
            'exit_price': price,
            'pnl_pct': pnl_pct * 100,
            'pnl_amount': pnl_amount,
            'stages': len(pos.stages),
            'reason': reason,
            'hold_time': pos.entry_time,
            'highest_pnl': pos.highest_pnl_pct * 100
        }
        
        # 标记为已止损或清除
        if reason == '止损' or reason == '移动止损':
            pos.stage = LivermoreStage.STOPPED
        else:
            pos.stage = LivermoreStage.EMPTY
        
        emoji = "✅" if pnl_amount > 0 else "❌"
        logger.info(f"{emoji} 利弗莫尔平仓 {symbol}: {reason}, "
                    f"盈亏={pnl_pct*100:.2f}% ({pnl_amount:+.4f}U), "
                    f"加仓次数={len(pos.stages)-1}")
        
        return result
    
    def _check_trend(self, side: str, klines: List) -> bool:
        """检查趋势是否支持加仓"""
        if len(klines) < self.config.ema_slow:
            return True  # 数据不足，默认通过
        
        closes = np.array([k[4] for k in klines])
        
        # 计算EMA
        ema_fast = self._ema(closes, self.config.ema_fast)
        ema_slow = self._ema(closes, self.config.ema_slow)
        
        if side == 'buy':
            # 多头：快EMA在慢EMA之上，且价格在快EMA之上
            return ema_fast[-1] > ema_slow[-1] and closes[-1] > ema_fast[-1]
        else:
            # 空头：快EMA在慢EMA之下，且价格在快EMA之下
            return ema_fast[-1] < ema_slow[-1] and closes[-1] < ema_fast[-1]
    
    @staticmethod
    def _ema(data: np.ndarray, period: int) -> np.ndarray:
        """计算EMA"""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        return ema
    
    def get_position_summary(self) -> str:
        """获取持仓摘要"""
        lines = ["📊 利弗莫尔策略持仓:"]
        
        for symbol, pos in self.positions.items():
            if pos.stage == LivermoreStage.EMPTY:
                continue
            
            stage_map = {
                LivermoreStage.BASE: "底仓(20%)",
                LivermoreStage.ADD1: "加仓1(40%)",
                LivermoreStage.ADD2: "加仓2(60%)",
                LivermoreStage.FULL: "满仓(100%)",
                LivermoreStage.STOPPED: "已止损"
            }
            
            lines.append(
                f"  {symbol}: {pos.side} | {stage_map[pos.stage]} | "
                f"均价={pos.avg_price:.6f} | 止损={pos.stop_loss:.6f}"
            )
        
        if len(lines) == 1:
            lines.append("  (无持仓)")
        
        lines.append(f"  总交易: {self.total_trades} | "
                    f"胜率: {self.winning_trades/max(1,self.total_trades)*100:.0f}% | "
                    f"总盈亏: {self.total_pnl:+.4f}U")
        
        return "\n".join(lines)
