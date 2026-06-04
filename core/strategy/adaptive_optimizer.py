"""
自适应优化引擎
==============

根据市场状态自动调整利弗莫尔策略参数。

市场状态分为4种：
1. TRENDING_UP   — 上涨趋势：放大加仓，放宽止损
2. TRENDING_DOWN — 下跌趋势：不开仓或做空
3. RANGING       — 震荡盘整：缩小仓位，收紧止损
4. VOLATILE      — 高波动：缩小仓位，收紧止损，加快节奏

核心指标：
- ATR（平均真实波幅）→ 波动率
- ADX（平均趋向指数）→ 趋势强度
- 成交量变化 → 市场活跃度
- 近期盈亏 → 策略适应性
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from core.strategy.livermore import LivermoreConfig


class MarketRegime(Enum):
    """市场状态"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"


@dataclass
class MarketState:
    """市场状态快照"""
    regime: MarketRegime
    adx: float              # 趋势强度 (0-100)
    atr_pct: float          # ATR占价格百分比
    volume_ratio: float     # 成交量相对均值比
    ema_trend: str          # EMA趋势方向
    confidence: float       # 状态判断置信度


@dataclass
class PerformanceMetrics:
    """策略表现指标"""
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    recent_trades: int = 0
    consecutive_losses: int = 0


class AdaptiveOptimizer:
    """
    自适应优化引擎
    
    根据市场状态和策略表现，自动调整利弗莫尔参数。
    """
    
    def __init__(self):
        # 历史状态
        self.state_history: List[Tuple[str, MarketRegime]] = []
        self.param_history: List[Dict] = []
        
        # 市场状态参数表（不同市场→不同参数）
        self.regime_params = {
            MarketRegime.TRENDING_UP: {
                'trigger_pct': 0.04,      # 4%就加仓（趋势明确，早加）
                'stop_pct': 0.08,         # 8%止损（给更多空间）
                'trailing_pct': 0.04,     # 4%移动止损（让利润跑）
                'base_ratio': 0.25,       # 25%底仓（更大胆）
                'add_ratio': 0.25,        # 25%加仓
                'full_ratio': 0.50,       # 50%满仓
                'max_hold_hours': 72,     # 持仓更久
                'use_trend_confirm': True,
                'buy_threshold': 55,      # 买入门槛降低
            },
            MarketRegime.RANGING: {
                'trigger_pct': 0.06,      # 6%才加仓（震荡中谨慎）
                'stop_pct': 0.05,         # 5%止损（快速止损）
                'trailing_pct': 0.025,    # 2.5%移动止损（保护利润）
                'base_ratio': 0.15,       # 15%底仓（小仓试探）
                'add_ratio': 0.15,        # 15%加仓
                'full_ratio': 0.30,       # 30%满仓（不满仓）
                'max_hold_hours': 24,     # 缩短持仓
                'use_trend_confirm': True,
                'buy_threshold': 65,      # 买入门槛提高
            },
            MarketRegime.VOLATILE: {
                'trigger_pct': 0.08,      # 8%才加仓（波动大，等确认）
                'stop_pct': 0.04,         # 4%止损（严格止损）
                'trailing_pct': 0.02,     # 2%移动止损（快速锁定）
                'base_ratio': 0.10,       # 10%底仓（最小仓位）
                'add_ratio': 0.10,        # 10%加仓
                'full_ratio': 0.20,       # 20%满仓（极度保守）
                'max_hold_hours': 12,     # 超短持仓
                'use_trend_confirm': True,
                'buy_threshold': 70,      # 买入门槛最高
            },
            MarketRegime.TRENDING_DOWN: {
                'trigger_pct': 0.05,
                'stop_pct': 0.05,
                'trailing_pct': 0.03,
                'base_ratio': 0.10,       # 最小仓位
                'add_ratio': 0.10,
                'full_ratio': 0.20,
                'max_hold_hours': 12,
                'use_trend_confirm': True,
                'buy_threshold': 75,      # 极高门槛（逆势不开）
            },
        }
        
        logger.info("🧠 自适应优化引擎初始化完成")
    
    def detect_market_state(self, klines: List) -> MarketState:
        """
        检测当前市场状态
        
        Args:
            klines: K线数据 [[ts, open, high, low, close, vol], ...]
            
        Returns:
            MarketState
        """
        if len(klines) < 30:
            return MarketState(
                regime=MarketRegime.RANGING,
                adx=25, atr_pct=0.02, volume_ratio=1.0,
                ema_trend='sideways', confidence=0.3
            )
        
        closes = np.array([k[4] for k in klines], dtype=float)
        highs = np.array([k[2] for k in klines], dtype=float)
        lows = np.array([k[3] for k in klines], dtype=float)
        volumes = np.array([k[5] for k in klines], dtype=float)
        
        # 1. 计算ADX（趋势强度）
        adx = self._calc_adx(highs, lows, closes, 14)
        
        # 2. 计算ATR（波动率）
        atr = self._calc_atr(highs, lows, closes, 14)
        atr_pct = atr / closes[-1] if closes[-1] > 0 else 0
        
        # 3. 成交量变化
        vol_ma20 = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        volume_ratio = volumes[-1] / vol_ma20 if vol_ma20 > 0 else 1.0
        
        # 4. EMA趋势
        ema_fast = self._ema(closes, 12)
        ema_slow = self._ema(closes, 26)
        if ema_fast[-1] > ema_slow[-1] * 1.01:
            ema_trend = 'up'
        elif ema_fast[-1] < ema_slow[-1] * 0.99:
            ema_trend = 'down'
        else:
            ema_trend = 'sideways'
        
        # 5. 判断市场状态
        regime, confidence = self._classify_regime(
            adx, atr_pct, volume_ratio, ema_trend
        )
        
        state = MarketState(
            regime=regime,
            adx=round(adx, 1),
            atr_pct=round(atr_pct, 4),
            volume_ratio=round(volume_ratio, 2),
            ema_trend=ema_trend,
            confidence=round(confidence, 2)
        )
        
        return state
    
    def _classify_regime(self, adx: float, atr_pct: float,
                         volume_ratio: float, ema_trend: str) -> Tuple[MarketRegime, float]:
        """分类市场状态"""
        
        # 高波动判断（ATR > 3% 或 成交量暴增）
        if atr_pct > 0.03 or volume_ratio > 2.5:
            return MarketRegime.VOLATILE, 0.8
        
        # 强趋势判断（ADX > 25 且 EMA方向一致）
        if adx > 25:
            if ema_trend == 'up':
                return MarketRegime.TRENDING_UP, min(0.95, adx / 50)
            elif ema_trend == 'down':
                return MarketRegime.TRENDING_DOWN, min(0.95, adx / 50)
        
        # 弱趋势
        if adx > 20:
            if ema_trend == 'up':
                return MarketRegime.TRENDING_UP, 0.6
            elif ema_trend == 'down':
                return MarketRegime.TRENDING_DOWN, 0.6
        
        # 默认：震荡
        return MarketRegime.RANGING, 0.7
    
    def get_optimized_config(self, market_state: MarketState,
                             perf: PerformanceMetrics = None) -> LivermoreConfig:
        """
        根据市场状态和表现指标，生成优化后的配置
        
        Args:
            market_state: 市场状态
            perf: 策略表现（可选，用于微调）
            
        Returns:
            优化后的 LivermoreConfig
        """
        # 基础参数（按市场状态）
        base = self.regime_params[market_state.regime].copy()
        
        # 根据表现微调
        if perf:
            base = self._adjust_by_performance(base, perf)
        
        # 根据置信度微调（置信度低→更保守）
        if market_state.confidence < 0.5:
            base['base_ratio'] *= 0.7
            base['add_ratio'] *= 0.7
            base['full_ratio'] *= 0.7
            base['stop_pct'] *= 0.8
            logger.info(f"⚠️ 置信度低({market_state.confidence})，仓位缩减30%")
        
        config = LivermoreConfig(
            trigger_pct=base['trigger_pct'],
            stop_pct=base['stop_pct'],
            trailing_pct=base['trailing_pct'],
            base_ratio=base['base_ratio'],
            add1_ratio=base['add_ratio'],
            add2_ratio=base['add_ratio'],
            full_ratio=base['full_ratio'],
            max_hold_hours=base['max_hold_hours'],
            use_trend_confirm=base['use_trend_confirm'],
            leverage=10
        )
        
        # 记录
        self.param_history.append({
            'time': datetime.now().isoformat(),
            'regime': market_state.regime.value,
            'params': base.copy()
        })
        
        return config
    
    def _adjust_by_performance(self, params: Dict, perf: PerformanceMetrics) -> Dict:
        """根据策略表现微调参数"""
        p = params.copy()
        
        # 连续亏损→缩小仓位，收紧止损
        if perf.consecutive_losses >= 3:
            factor = max(0.5, 1 - perf.consecutive_losses * 0.1)
            p['base_ratio'] *= factor
            p['add_ratio'] *= factor
            p['full_ratio'] *= factor
            p['stop_pct'] *= 0.8
            logger.info(f"📉 连续亏损{perf.consecutive_losses}次，仓位缩至{factor*100:.0f}%")
        
        # 胜率低→提高买入门槛
        if perf.win_rate < 0.4 and perf.recent_trades >= 5:
            p['buy_threshold'] = min(75, p.get('buy_threshold', 60) + 5)
            logger.info(f"📉 胜率{perf.win_rate*100:.0f}%，买入门槛提高到{p['buy_threshold']}")
        
        # 胜率高→可以适当放宽
        if perf.win_rate > 0.6 and perf.recent_trades >= 10:
            p['buy_threshold'] = max(50, p.get('buy_threshold', 60) - 3)
            logger.info(f"📈 胜率{perf.win_rate*100:.0f}%，买入门槛放宽到{p['buy_threshold']}")
        
        # 利润因子高→放大仓位
        if perf.profit_factor > 2.0 and perf.recent_trades >= 10:
            factor = min(1.3, 1 + (perf.profit_factor - 2) * 0.1)
            p['base_ratio'] = min(0.30, p['base_ratio'] * factor)
            p['add_ratio'] = min(0.30, p['add_ratio'] * factor)
            logger.info(f"📈 利润因子{perf.profit_factor:.1f}，仓位放大{factor*100:.0f}%")
        
        # 最大回撤大→全面收缩
        if perf.max_drawdown > 0.15:
            p['base_ratio'] *= 0.6
            p['add_ratio'] *= 0.6
            p['full_ratio'] *= 0.6
            p['stop_pct'] *= 0.7
            logger.info(f"⚠️ 最大回撤{perf.max_drawdown*100:.0f}%，全面收缩仓位")
        
        return p
    
    def calc_performance(self, trades: List[Dict]) -> PerformanceMetrics:
        """从交易记录计算表现指标"""
        if not trades:
            return PerformanceMetrics()
        
        wins = [t for t in trades if t.get('pnl', 0) > 0]
        losses = [t for t in trades if t.get('pnl', 0) <= 0]
        
        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
        avg_loss = abs(np.mean([t['pnl'] for t in losses])) if losses else 0
        
        total_win = sum(t['pnl'] for t in wins) if wins else 0
        total_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0
        profit_factor = total_win / total_loss if total_loss > 0 else 0
        
        # 连续亏损
        consecutive_losses = 0
        for t in reversed(trades):
            if t.get('pnl', 0) <= 0:
                consecutive_losses += 1
            else:
                break
        
        # 最大回撤
        cumulative = np.cumsum([t.get('pnl', 0) for t in trades])
        peak = np.maximum.accumulate(cumulative) if len(cumulative) > 0 else np.array([0])
        drawdown = peak - cumulative
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        # 归一化
        initial = 10.0  # 假设初始资金
        max_drawdown_pct = max_drawdown / initial if initial > 0 else 0
        
        return PerformanceMetrics(
            win_rate=round(win_rate, 3),
            avg_win=round(avg_win, 4),
            avg_loss=round(avg_loss, 4),
            profit_factor=round(profit_factor, 2),
            max_drawdown=round(max_drawdown_pct, 3),
            recent_trades=len(trades),
            consecutive_losses=consecutive_losses
        )
    
    def format_report(self, market_state: MarketState,
                      config: LivermoreConfig,
                      perf: PerformanceMetrics) -> str:
        """生成优化报告"""
        regime_emoji = {
            MarketRegime.TRENDING_UP: "🟢📈",
            MarketRegime.TRENDING_DOWN: "🔴📉",
            MarketRegime.RANGING: "🟡↔️",
            MarketRegime.VOLATILE: "🟠⚡",
        }
        regime_name = {
            MarketRegime.TRENDING_UP: "上涨趋势",
            MarketRegime.TRENDING_DOWN: "下跌趋势",
            MarketRegime.RANGING: "震荡盘整",
            MarketRegime.VOLATILE: "高波动",
        }
        
        lines = [
            "=" * 50,
            "🧠 自适应优化报告",
            "=" * 50,
            "",
            f"📊 市场状态: {regime_emoji[market_state.regime]} {regime_name[market_state.regime]}",
            f"   ADX={market_state.adx} | ATR={market_state.atr_pct*100:.2f}% | "
            f"成交量比={market_state.volume_ratio}x | 置信度={market_state.confidence}",
            "",
            "⚙️ 优化后参数:",
            f"   加仓触发: {config.trigger_pct*100:.1f}%",
            f"   止损线:   {config.stop_pct*100:.1f}%",
            f"   移动止损: {config.trailing_pct*100:.1f}%",
            f"   底仓比例: {config.base_ratio*100:.0f}%",
            f"   加仓比例: {config.add1_ratio*100:.0f}%",
            f"   满仓比例: {config.full_ratio*100:.0f}%",
            f"   最大持仓: {config.max_hold_hours}h",
        ]
        
        if perf.recent_trades > 0:
            lines.extend([
                "",
                "📈 策略表现:",
                f"   胜率:     {perf.win_rate*100:.0f}%",
                f"   平均盈利: {perf.avg_win:+.4f}U",
                f"   平均亏损: {perf.avg_loss:.4f}U",
                f"   利润因子: {perf.profit_factor:.2f}",
                f"   最大回撤: {perf.max_drawdown*100:.1f}%",
                f"   连续亏损: {perf.consecutive_losses}次",
            ])
        
        lines.append("=" * 50)
        return "\n".join(lines)
    
    # === 技术指标计算 ===
    
    @staticmethod
    def _ema(data: np.ndarray, period: int) -> np.ndarray:
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        return ema
    
    @staticmethod
    def _calc_atr(highs: np.ndarray, lows: np.ndarray,
                  closes: np.ndarray, period: int = 14) -> float:
        """计算ATR"""
        if len(highs) < period + 1:
            return 0
        
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
        )
        
        atr = np.mean(tr[-period:])
        return atr
    
    @staticmethod
    def _calc_adx(highs: np.ndarray, lows: np.ndarray,
                  closes: np.ndarray, period: int = 14) -> float:
        """计算ADX（简化版）"""
        if len(highs) < period * 2:
            return 25  # 默认中性
        
        # 计算+DM和-DM
        up_move = highs[1:] - highs[:-1]
        down_move = lows[:-1] - lows[1:]
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # 计算TR
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
        )
        
        # 平滑
        atr = np.mean(tr[-period:])
        if atr == 0:
            return 25
        
        plus_di = (np.mean(plus_dm[-period:]) / atr) * 100
        minus_di = (np.mean(minus_dm[-period:]) / atr) * 100
        
        di_sum = plus_di + minus_di
        if di_sum == 0:
            return 25
        
        dx = abs(plus_di - minus_di) / di_sum * 100
        
        # 简化：直接返回DX作为ADX近似
        return dx
