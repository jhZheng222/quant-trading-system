"""
多策略引擎
==========

集成多个独立策略，根据市场状态自动选择最优策略组合。

策略列表：
1. 利弗莫尔（趋势跟踪）— 已有
2. 资金费率套利 — 震荡市稳赚
3. 波动率突破 — 盘整后爆发
4. 反向收割 — 极端情绪反转
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class StrategyType(Enum):
    """策略类型"""
    LIVERMORE = "livermore"           # 趋势跟踪
    FUNDING_ARB = "funding_arb"       # 资金费率套利
    VOLATILITY = "volatility"         # 波动率突破
    CONTRARIAN = "contrarian"         # 反向收割


@dataclass
class StrategySignal:
    """策略信号"""
    strategy: StrategyType
    symbol: str
    action: str           # 'buy'|'sell'|'hold'|'close'
    confidence: float     # 0-1
    reason: str
    params: Dict = field(default_factory=dict)


class MultiStrategyEngine:
    """
    多策略引擎
    
    根据市场状态选择最优策略组合：
    - 趋势行情 → 利弗莫尔为主
    - 震荡行情 → 费率套利为主
    - 盘整末期 → 波动率突破
    - 极端情绪 → 反向收割
    """
    
    def __init__(self):
        # 各策略权重（按市场状态动态调整）
        self.strategy_weights = {
            StrategyType.LIVERMORE: 0.4,
            StrategyType.FUNDING_ARB: 0.3,
            StrategyType.VOLATILITY: 0.2,
            StrategyType.CONTRARIAN: 0.1,
        }
        
        # 资金费率阈值
        self.fr_high = 0.0005      # 0.05% = 多头拥挤
        self.fr_low = -0.0005      # -0.05% = 空头拥挤
        self.fr_extreme = 0.001    # 0.1% = 极端
        
        # 波动率参数
        self.vol_squeeze_threshold = 0.5   # ATR/MA(ATR) < 0.5 = 盘整
        self.vol_expansion_threshold = 2.0 # ATR/MA(ATR) > 2.0 = 爆发
        
        # 反向参数
        self.contrarian_fng_low = 25     # 恐惧贪婪<25 = 反向买入
        self.contrarian_fng_high = 75    # 恐惧贪婪>75 = 反向卖出
        
        logger.info("🎯 多策略引擎初始化完成")
    
    def evaluate_all(self, symbol: str, klines: List,
                     market_state: Dict = None,
                     sentiment: Dict = None) -> List[StrategySignal]:
        """
        评估所有策略，返回信号列表
        
        Args:
            symbol: 交易对
            klines: K线数据
            market_state: 市场状态（ADX/ATR等）
            sentiment: 情绪数据
        """
        signals = []
        
        # 1. 资金费率套利信号
        fr_signal = self._eval_funding_arb(symbol, klines, sentiment)
        if fr_signal:
            signals.append(fr_signal)
        
        # 2. 波动率突破信号
        vol_signal = self._eval_volatility(symbol, klines)
        if vol_signal:
            signals.append(vol_signal)
        
        # 3. 反向收割信号
        contra_signal = self._eval_contrarian(symbol, klines, sentiment)
        if contra_signal:
            signals.append(contra_signal)
        
        return signals
    
    def adjust_weights(self, market_regime: str, sentiment_score: float):
        """
        根据市场状态调整策略权重
        
        Args:
            market_regime: trending_up/ranging/volatile/trending_down
            sentiment_score: 0-100
        """
        if market_regime == 'trending_up':
            self.strategy_weights = {
                StrategyType.LIVERMORE: 0.6,
                StrategyType.FUNDING_ARB: 0.1,
                StrategyType.VOLATILITY: 0.2,
                StrategyType.CONTRARIAN: 0.1,
            }
        elif market_regime == 'ranging':
            self.strategy_weights = {
                StrategyType.LIVERMORE: 0.2,
                StrategyType.FUNDING_ARB: 0.5,
                StrategyType.VOLATILITY: 0.2,
                StrategyType.CONTRARIAN: 0.1,
            }
        elif market_regime == 'volatile':
            self.strategy_weights = {
                StrategyType.LIVERMORE: 0.1,
                StrategyType.FUNDING_ARB: 0.2,
                StrategyType.VOLATILITY: 0.5,
                StrategyType.CONTRARIAN: 0.2,
            }
        elif market_regime == 'trending_down':
            self.strategy_weights = {
                StrategyType.LIVERMORE: 0.1,
                StrategyType.FUNDING_ARB: 0.3,
                StrategyType.VOLATILITY: 0.1,
                StrategyType.CONTRARIAN: 0.5,
            }
        
        # 情绪极端时增加反向策略权重
        if sentiment_score <= 25 or sentiment_score >= 75:
            self.strategy_weights[StrategyType.CONTRARIAN] += 0.2
            # 归一化
            total = sum(self.strategy_weights.values())
            for k in self.strategy_weights:
                self.strategy_weights[k] /= total
        
        logger.info(f"策略权重: {', '.join(f'{k.value}={v:.0%}' for k, v in self.strategy_weights.items())}")
    
    # === 策略1: 资金费率套利 ===
    
    def _eval_funding_arb(self, symbol: str, klines: List,
                          sentiment: Dict = None) -> Optional[StrategySignal]:
        """
        资金费率套利策略
        
        原理：
        - 费率>0.05% → 多头拥挤 → 做空（收多头的费率）
        - 费率<-0.05% → 空头拥挤 → 做多（收空头的费率）
        - 每8小时结算一次费率
        """
        if not sentiment:
            return None
        
        frs = sentiment.get('funding_rates', {})
        fr = frs.get(symbol)
        if fr is None:
            return None
        
        current_price = float(klines[-1][4]) if klines else 0
        
        # 极端费率 → 强信号
        if abs(fr) >= self.fr_extreme:
            if fr > 0:
                return StrategySignal(
                    strategy=StrategyType.FUNDING_ARB,
                    symbol=symbol,
                    action='sell',
                    confidence=min(0.9, abs(fr) / self.fr_extreme * 0.5),
                    reason=f'费率{fr*100:.3f}%极端偏高，多头拥挤，做空收费率',
                    params={'funding_rate': fr, 'expected_8h_income': abs(fr) * 100}
                )
            else:
                return StrategySignal(
                    strategy=StrategyType.FUNDING_ARB,
                    symbol=symbol,
                    action='buy',
                    confidence=min(0.9, abs(fr) / self.fr_extreme * 0.5),
                    reason=f'费率{fr*100:.3f}%极端偏低，空头拥挤，做多收费率',
                    params={'funding_rate': fr, 'expected_8h_income': abs(fr) * 100}
                )
        
        # 一般费率 → 弱信号
        elif abs(fr) >= self.fr_high:
            direction = 'sell' if fr > 0 else 'buy'
            return StrategySignal(
                strategy=StrategyType.FUNDING_ARB,
                symbol=symbol,
                action=direction,
                confidence=0.3,
                reason=f'费率{fr*100:.3f}%偏{"高" if fr > 0 else "低"}，轻仓反向',
                params={'funding_rate': fr}
            )
        
        return None
    
    # === 策略2: 波动率突破 ===
    
    def _eval_volatility(self, symbol: str, klines: List) -> Optional[StrategySignal]:
        """
        波动率突破策略
        
        原理：
        - ATR收缩到极低 → 盘整蓄力 → 即将突破
        - ATR突然扩张 → 突破确认 → 顺势开仓
        """
        if len(klines) < 30:
            return None
        
        closes = np.array([k[4] for k in klines], dtype=float)
        highs = np.array([k[2] for k in klines], dtype=float)
        lows = np.array([k[3] for k in klines], dtype=float)
        
        # 计算ATR
        atr = self._calc_atr(highs, lows, closes, 14)
        atr_ma = np.mean(atr) if len(atr) > 0 else 0
        
        if atr_ma == 0:
            return None
        
        current_atr = atr[-1]
        atr_ratio = current_atr / atr_ma
        
        # 检查布林带收缩
        bb_upper, bb_middle, bb_lower = self._calc_bollinger(closes, 20, 2)
        bb_width = (bb_upper[-1] - bb_lower[-1]) / bb_middle[-1] if bb_middle[-1] > 0 else 0
        
        current_price = closes[-1]
        
        # 盘整蓄力 → 等待突破
        if atr_ratio < self.vol_squeeze_threshold:
            # 检查是否开始突破
            if current_price > bb_upper[-1]:
                return StrategySignal(
                    strategy=StrategyType.VOLATILITY,
                    symbol=symbol,
                    action='buy',
                    confidence=0.7,
                    reason=f'波动率压缩后向上突破布林上轨，ATR比={atr_ratio:.2f}',
                    params={'atr_ratio': atr_ratio, 'bb_width': bb_width}
                )
            elif current_price < bb_lower[-1]:
                return StrategySignal(
                    strategy=StrategyType.VOLATILITY,
                    symbol=symbol,
                    action='sell',
                    confidence=0.7,
                    reason=f'波动率压缩后向下突破布林下轨，ATR比={atr_ratio:.2f}',
                    params={'atr_ratio': atr_ratio, 'bb_width': bb_width}
                )
            else:
                return StrategySignal(
                    strategy=StrategyType.VOLATILITY,
                    symbol=symbol,
                    action='hold',
                    confidence=0.5,
                    reason=f'波动率极度压缩(ATR比={atr_ratio:.2f})，等待突破方向',
                    params={'atr_ratio': atr_ratio, 'bb_width': bb_width}
                )
        
        # 波动率扩张 → 趋势确认
        elif atr_ratio > self.vol_expansion_threshold:
            # 看方向
            ema12 = self._ema(closes, 12)
            ema26 = self._ema(closes, 26)
            
            if ema12[-1] > ema26[-1]:
                return StrategySignal(
                    strategy=StrategyType.VOLATILITY,
                    symbol=symbol,
                    action='buy',
                    confidence=0.6,
                    reason=f'波动率扩张+EMA多头排列，趋势向上',
                    params={'atr_ratio': atr_ratio}
                )
            else:
                return StrategySignal(
                    strategy=StrategyType.VOLATILITY,
                    symbol=symbol,
                    action='sell',
                    confidence=0.6,
                    reason=f'波动率扩张+EMA空头排列，趋势向下',
                    params={'atr_ratio': atr_ratio}
                )
        
        return None
    
    # === 策略3: 反向收割 ===
    
    def _eval_contrarian(self, symbol: str, klines: List,
                         sentiment: Dict = None) -> Optional[StrategySignal]:
        """
        反向收割策略（孙宇晨式）
        
        原理：
        - 恐惧贪婪指数<25 + 资金费率极端负 → 恐慌底部，做多
        - 恐惧贪婪指数>75 + 资金费率极端正 → 贪婪顶部，做空
        """
        if not sentiment:
            return None
        
        fng = sentiment.get('fear_greed', {}).get('value', 50)
        frs = sentiment.get('funding_rates', {})
        fr = frs.get(symbol, 0)
        
        contrarian = sentiment.get('contrarian_signal', 'hold')
        
        current_price = float(klines[-1][4]) if klines else 0
        
        # 极度恐惧 + 负费率 → 做多
        if fng <= self.contrarian_fng_low and fr < -0.0003:
            return StrategySignal(
                strategy=StrategyType.CONTRARIAN,
                symbol=symbol,
                action='buy',
                confidence=min(0.8, (self.contrarian_fng_low - fng) / 25 * 0.5 + abs(fr) / 0.001 * 0.3),
                reason=f'极度恐惧(FNG={fng})+负费率({fr*100:.3f}%)，反向做多',
                params={'fng': fng, 'funding_rate': fr}
            )
        
        # 极度贪婪 + 正费率 → 做空
        if fng >= self.contrarian_fng_high and fr > 0.0003:
            return StrategySignal(
                strategy=StrategyType.CONTRARIAN,
                symbol=symbol,
                action='sell',
                confidence=min(0.8, (fng - self.contrarian_fng_high) / 25 * 0.5 + fr / 0.001 * 0.3),
                reason=f'极度贪婪(FNG={fng})+正费率({fr*100:.3f}%)，反向做空',
                params={'fng': fng, 'funding_rate': fr}
            )
        
        return None
    
    # === 辅助计算 ===
    
    @staticmethod
    def _calc_atr(highs, lows, closes, period=14):
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
        )
        atr = np.zeros(len(tr))
        atr[period-1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        return atr[period-1:]
    
    @staticmethod
    def _calc_bollinger(closes, period=20, std_dev=2):
        if len(closes) < period:
            return closes, closes, closes
        
        middle = np.convolve(closes, np.ones(period)/period, mode='valid')
        std = np.array([np.std(closes[i:i+period]) for i in range(len(closes)-period+1)])
        
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        
        # 补齐长度
        pad = len(closes) - len(middle)
        upper = np.pad(upper, (pad, 0), 'edge')
        middle = np.pad(middle, (pad, 0), 'edge')
        lower = np.pad(lower, (pad, 0), 'edge')
        
        return upper, middle, lower
    
    @staticmethod
    def _ema(data, period):
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        return ema
    
    def get_report(self, signals: List[StrategySignal]) -> str:
        """格式化多策略报告"""
        if not signals:
            return "🎯 多策略: 无信号"
        
        lines = ["🎯 多策略信号:"]
        for sig in signals:
            emoji = {'buy': '🟢', 'sell': '🔴', 'hold': '⚪', 'close': '🟡'}
            lines.append(
                f"   {emoji.get(sig.action, '❓')} [{sig.strategy.value}] "
                f"{sig.symbol}: {sig.action} (置信度{sig.confidence:.0%}) — {sig.reason}"
            )
        
        return "\n".join(lines)
