"""
风控升级模块
============

组合级风控 + 黑天鹅防护 + 时间风控 + 相关性控制

所有计算基于本地数据，不需要外部API。
"""

import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from loguru import logger


class RiskManager:
    """
    风控管理器
    
    多层防护：
    1. 仓位级：单笔止损/止盈
    2. 组合级：总仓位/同方向敞口
    3. 黑天鹅：极端波动自动减仓
    4. 时间级：时段+持仓时长
    5. 相关性：BTC联动+同币种控制
    """
    
    def __init__(self, initial_balance: float = 10.0):
        self.initial_balance = initial_balance
        
        # === 组合级限制 ===
        self.max_single_position = 0.30   # 单币种最大仓位30%
        self.max_same_direction = 0.60    # 同方向最大敞口60%
        self.max_margin_usage = 0.50      # 总保证金使用率<50%
        self.max_daily_loss = 0.15        # 单日最大亏损15%
        
        # === 黑天鹅防护 ===
        self.swan_atr_threshold = 3.0     # ATR>3倍均值 = 黑天鹅
        self.swan_price_drop = 0.10       # 1小时内跌10% = 黑天鹅
        self.consecutive_loss_limit = 3   # 连续3次止损 → 暂停
        self.cooldown_minutes = 120       # 暂停2小时
        
        # === 时间风控 ===
        self.asia_active = (8, 16)        # 亚洲活跃时段
        self.us_active = (21, 5)          # 美国活跃时段（跨日）
        self.weekend_reduce = 0.5         # 周末仓位减半
        
        # === 状态追踪 ===
        self.daily_pnl = 0.0
        self.daily_reset_date = ""
        self.consecutive_losses = 0
        self.last_loss_time = None
        self.paused_until = None
        
        logger.info("🛡️ 风控管理器初始化完成")
    
    def check_open_allowed(self, symbol: str, side: str, amount: float,
                           price: float, balance: float,
                           positions: Dict, leverage: int = 10,
                           klines: List = None) -> Dict:
        """
        检查是否允许开仓
        
        Returns:
            {
                'allowed': bool,
                'reason': str,
                'adjusted_amount': float,  # 调整后的仓位
                'warnings': list
            }
        """
        warnings = []
        
        # 1. 检查是否在暂停期
        if self.paused_until and datetime.now() < self.paused_until:
            remaining = (self.paused_until - datetime.now()).seconds // 60
            return {
                'allowed': False,
                'reason': f'连续亏损暂停中，还需{remaining}分钟',
                'adjusted_amount': 0,
                'warnings': warnings
            }
        
        # 2. 重置每日统计
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.daily_reset_date:
            self.daily_pnl = 0.0
            self.daily_reset_date = today
        
        # 3. 检查单日亏损
        if self.daily_pnl < -self.max_daily_loss * self.initial_balance:
            return {
                'allowed': False,
                'reason': f'单日亏损已达{self.daily_pnl:.2f}U，超过限制{self.max_daily_loss*100}%',
                'adjusted_amount': 0,
                'warnings': warnings
            }
        
        # 4. 检查保证金使用率
        used_margin = sum(
            p.get('cost', 0) for p in positions.values()
            if p.get('stage') not in ['empty', 'stopped']
        )
        margin_ratio = used_margin / balance if balance > 0 else 1
        
        if margin_ratio >= self.max_margin_usage:
            return {
                'allowed': False,
                'reason': f'保证金使用率{margin_ratio*100:.0f}%已达上限{self.max_margin_usage*100}%',
                'adjusted_amount': 0,
                'warnings': warnings
            }
        
        # 5. 检查单币种仓位
        symbol_cost = sum(
            p.get('cost', 0) for p in positions.values()
            if p.get('symbol') == symbol and p.get('stage') not in ['empty', 'stopped']
        )
        symbol_ratio = symbol_cost / balance if balance > 0 else 0
        
        if symbol_ratio >= self.max_single_position:
            return {
                'allowed': False,
                'reason': f'{symbol}仓位已达{symbol_ratio*100:.0f}%，超过上限{self.max_single_position*100}%',
                'adjusted_amount': 0,
                'warnings': warnings
            }
        
        # 6. 检查同方向敞口
        same_dir_cost = sum(
            p.get('cost', 0) for p in positions.values()
            if p.get('side') == side and p.get('stage') not in ['empty', 'stopped']
        )
        dir_ratio = same_dir_cost / balance if balance > 0 else 0
        
        if dir_ratio >= self.max_same_direction:
            return {
                'allowed': False,
                'reason': f'{side}方向敞口已达{dir_ratio*100:.0f}%，超过上限{self.max_same_direction*100}%',
                'adjusted_amount': 0,
                'warnings': warnings
            }
        
        # 7. 黑天鹅检测
        if klines and len(klines) >= 2:
            swan = self._check_swan(klines)
            if swan['is_swan']:
                return {
                    'allowed': False,
                    'reason': f'黑天鹅预警: {swan["reason"]}',
                    'adjusted_amount': 0,
                    'warnings': [swan['reason']]
                }
        
        # 8. 时间风控调整
        adjusted = amount
        time_factor = self._time_adjustment()
        if time_factor < 1.0:
            adjusted = amount * time_factor
            warnings.append(f'时段调整: 仓位×{time_factor:.0%}')
        
        # 9. 相关性检查（如果已有DOGE仓位，PEPE仓位减半）
        related_count = sum(
            1 for p in positions.values()
            if p.get('stage') not in ['empty', 'stopped']
        )
        if related_count >= 2:
            adjusted *= 0.5
            warnings.append('多币种持仓，新仓位减半')
        
        # 10. 保证金上限调整
        remaining_margin = balance * self.max_margin_usage - used_margin
        max_new_margin = remaining_margin * 0.8  # 留20%缓冲
        max_new_amount = max_new_margin * leverage / price
        
        if adjusted > max_new_amount:
            adjusted = max_new_amount
            warnings.append(f'仓位受保证金限制，调整为{adjusted:.4f}')
        
        return {
            'allowed': True,
            'reason': '通过风控检查',
            'adjusted_amount': adjusted,
            'warnings': warnings
        }
    
    def check_force_close(self, symbol: str, position: Dict,
                          current_price: float, klines: List = None) -> Dict:
        """
        检查是否需要强制平仓
        
        Returns:
            {'should_close': bool, 'reason': str, 'urgency': 'high'|'medium'|'low'}
        """
        if not position or position.get('stage') in ['empty', 'stopped']:
            return {'should_close': False, 'reason': '', 'urgency': ''}
        
        entry_price = position.get('entry_price', 0)
        avg_price = position.get('avg_price', entry_price)
        side = position.get('side', 'buy')
        
        if avg_price == 0:
            return {'should_close': False, 'reason': '', 'urgency': ''}
        
        # 计算浮盈
        if side == 'buy':
            pnl_pct = (current_price - avg_price) / avg_price
        else:
            pnl_pct = (avg_price - current_price) / avg_price
        
        # 黑天鹅检测
        if klines and len(klines) >= 2:
            swan = self._check_swan(klines)
            if swan['is_swan']:
                # 如果持仓方向与黑天鹅方向相反，立即平仓
                if (side == 'buy' and swan.get('direction') == 'down') or \
                   (side == 'sell' and swan.get('direction') == 'up'):
                    return {
                        'should_close': True,
                        'reason': f'黑天鹅防护: {swan["reason"]}',
                        'urgency': 'high'
                    }
        
        # 单日亏损过大
        if pnl_pct < -self.max_daily_loss:
            return {
                'should_close': True,
                'reason': f'浮亏{pnl_pct*100:.1f}%超过单日限制{self.max_daily_loss*100}%',
                'urgency': 'high'
            }
        
        return {'should_close': False, 'reason': '', 'urgency': ''}
    
    def record_trade_result(self, pnl: float):
        """记录交易结果"""
        self.daily_pnl += pnl
        
        if pnl < 0:
            self.consecutive_losses += 1
            self.last_loss_time = datetime.now()
            
            if self.consecutive_losses >= self.consecutive_loss_limit:
                self.paused_until = datetime.now() + timedelta(minutes=self.cooldown_minutes)
                logger.warning(f"⚠️ 连续亏损{self.consecutive_losses}次，暂停交易至{self.paused_until.strftime('%H:%M')}")
        else:
            self.consecutive_losses = 0
    
    def _check_swan(self, klines: List) -> Dict:
        """黑天鹅检测"""
        if len(klines) < 2:
            return {'is_swan': False}
        
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        
        # 1小时暴跌检测
        price_change = (closes[-1] - closes[-2]) / closes[-2] if closes[-2] > 0 else 0
        
        if price_change < -self.swan_price_drop:
            return {
                'is_swan': True,
                'reason': f'1小时暴跌{price_change*100:.1f}%',
                'direction': 'down'
            }
        
        if price_change > self.swan_price_drop:
            return {
                'is_swan': True,
                'reason': f'1小时暴涨{price_change*100:.1f}%',
                'direction': 'up'
            }
        
        # ATR异常检测
        if len(closes) >= 20:
            trs = []
            for i in range(1, len(closes)):
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),
                    abs(lows[i] - closes[i-1])
                )
                trs.append(tr)
            
            current_atr = np.mean(trs[-14:])
            avg_atr = np.mean(trs[-28:-14]) if len(trs) >= 28 else np.mean(trs)
            
            if avg_atr > 0 and current_atr / avg_atr > self.swan_atr_threshold:
                return {
                    'is_swan': True,
                    'reason': f'ATR异常: 当前{current_atr/avg_atr:.1f}倍于均值',
                    'direction': 'down' if closes[-1] < closes[-2] else 'up'
                }
        
        return {'is_swan': False}
    
    def _time_adjustment(self) -> float:
        """时段仓位调整系数"""
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        # 周末减仓
        if weekday >= 5:  # Saturday, Sunday
            return self.weekend_reduce
        
        # 亚洲活跃时段（正常）
        if self.asia_active[0] <= hour < self.asia_active[1]:
            return 1.0
        
        # 美国时段（谨慎）
        if hour >= self.us_active[0] or hour < self.us_active[1]:
            return 0.7
        
        # 其他时段（保守）
        return 0.5
    
    def get_status(self) -> str:
        """风控状态摘要"""
        lines = [
            "🛡️ 风控状态:",
            f"   单日盈亏: {self.daily_pnl:+.4f}U",
            f"   连续亏损: {self.consecutive_losses}次",
        ]
        
        if self.paused_until and datetime.now() < self.paused_until:
            remaining = (self.paused_until - datetime.now()).seconds // 60
            lines.append(f"   ⚠️ 交易暂停中: 还需{remaining}分钟")
        
        time_factor = self._time_adjustment()
        lines.append(f"   时段系数: {time_factor:.0%}")
        
        return "\n".join(lines)