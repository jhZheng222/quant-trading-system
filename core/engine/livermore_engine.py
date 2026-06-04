"""
利弗莫尔策略引擎 — 基于通用基类
================================

继承 BaseEngine，只实现策略特有逻辑：
- analyze_market: 市场状态检测
- check_open: 开仓条件（利弗莫尔规则）
- check_exit: 平仓条件（止损/移动止损/时间止损）
- check_add: 加仓条件（浮盈加仓）

所有基础设施（情绪、多策略、风控、持仓管理）由基类提供。
"""

import numpy as np
from typing import Dict, List, Optional
from loguru import logger

from core.engine.base_engine import BaseEngine
from core.strategy.adaptive_optimizer import AdaptiveOptimizer, MarketState
from core.strategy.multi_strategy import StrategySignal, StrategyType


class LivermoreEngine(BaseEngine):
    """利弗莫尔策略引擎（基于通用基类）"""

    def __init__(self, initial_balance: float = 10.0, db_path: str = "data/trading.db",
                 config: Dict = None):
        super().__init__(initial_balance, db_path, config)

        self.optimizer = AdaptiveOptimizer()
        self.current_config = None
        self.market_state: Optional[MarketState] = None

        # 利弗莫尔参数（会被自适应优化器覆盖）
        self.trigger_pct = 0.05
        self.stop_pct = 0.07
        self.trailing_pct = 0.03
        self.base_ratio = 0.20
        self.add_ratio = 0.20
        self.full_ratio = 0.40
        self.buy_threshold = 60

        logger.info("📈 利弗莫尔引擎(通用基类版)初始化完成")

    def analyze_market(self, kline_data: Dict, sentiment: Dict) -> Dict:
        """市场状态分析 + 自适应参数调整"""
        first_symbol = list(kline_data.keys())[0]
        klines = kline_data[first_symbol]

        # 检测市场状态
        self.market_state = self.optimizer.detect_market_state(klines)

        # 获取优化后配置
        perf = self.optimizer.calc_performance(self.trade_history)
        config = self.optimizer.get_optimized_config(self.market_state, perf)
        self.current_config = config

        # 应用自适应参数
        self.trigger_pct = config.trigger_pct
        self.stop_pct = config.stop_pct
        self.trailing_pct = config.trailing_pct
        self.base_ratio = config.base_ratio
        self.add_ratio = config.add1_ratio
        self.full_ratio = config.full_ratio

        # 情绪调整（孙宇晨式反向）
        sentiment_score = sentiment.get('sentiment_score', 50)
        if sentiment_score <= 25:
            self.buy_threshold = max(45, self.buy_threshold - 10)
            logger.info(f"😱 极度恐惧，降低买入门槛至{self.buy_threshold}")
        elif sentiment_score >= 75:
            self.buy_threshold = min(80, self.buy_threshold + 10)
            logger.info(f"🤑 极度贪婪，提高买入门槛至{self.buy_threshold}")

        return {
            'regime': self.market_state.regime.value,
            'adx': self.market_state.adx,
            'atr_pct': self.market_state.atr_pct,
            'sentiment_score': sentiment_score,
            'contrarian': sentiment.get('contrarian_signal', 'hold'),
        }

    def check_open(self, symbol: str, price: float, klines: List,
                   signals: List[StrategySignal], sentiment: Dict) -> Optional[Dict]:
        """
        利弗莫尔开仓条件：
        1. 信号评分 >= 买入阈值
        2. 多策略引擎没有强烈反向信号
        3. 情绪不是极度贪婪
        4. 冷却期检查（30分钟内不重复开仓）
        5. 持仓笔数限制（最多3笔）
        """
        from datetime import datetime, timedelta
        
        # 0. 冷却期检查：30分钟内不重复开仓
        last_open_time = self.storage.get_last_open_time(symbol)
        if last_open_time:
            try:
                last_dt = datetime.fromisoformat(last_open_time)
                cooldown_minutes = 30
                if datetime.now() - last_dt < timedelta(minutes=cooldown_minutes):
                    remaining = cooldown_minutes - (datetime.now() - last_dt).seconds // 60
                    logger.debug(f"{symbol} 冷却期中，还需{remaining}分钟")
                    return None
            except:
                pass
        
        # 0.1 持仓笔数限制：最多3笔
        open_count = self.storage.get_open_trade_count(symbol)
        max_positions = 3
        if open_count >= max_positions:
            logger.debug(f"{symbol} 已有{open_count}笔持仓，达到上限{max_positions}")
            return None
        
        # 获取信号评分（从数据库最近信号）
        # 注意：confidence是0-1范围，需要乘以100映射到0-100与buy_threshold比较
        recent_signals = self.storage.get_signals(symbol, limit=1)
        raw_confidence = recent_signals[0].get('confidence', 0.5) if recent_signals else 0.5
        score = raw_confidence * 100  # 映射到0-100范围

        # 多策略检查：有没有强烈反向信号（阈值从0.6降到0.55）
        contra_sell = [s for s in signals if s.strategy == StrategyType.CONTRARIAN and s.action == 'sell']
        if contra_sell and contra_sell[0].confidence > 0.55:
            logger.debug(f"多策略反向卖出信号，不开仓")
            return None

        # 情绪检查
        sentiment_score = sentiment.get('sentiment_score', 50)
        if sentiment_score >= 80:
            logger.debug(f"情绪过于贪婪({sentiment_score})，不开仓")
            return None

        # 利弗莫尔核心：信号够强才开仓
        if score >= self.buy_threshold:
            # 确定方向
            side = 'buy'
            for s in signals:
                if s.action == 'sell' and s.confidence > 0.6:
                    side = 'sell'
                    break

            # 计算仓位和止损
            amount = self.balance * self.base_ratio * self.leverage / price
            if side == 'buy':
                stop_loss = price * (1 - self.stop_pct)
                take_profit = price * (1 + self.trigger_pct * 4)
            else:
                stop_loss = price * (1 + self.stop_pct)
                take_profit = price * (1 - self.trigger_pct * 4)

            return {
                'side': side,
                'amount': amount,
                'strategy': 'livermore',
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': f'信号评分{score}>=阈值{self.buy_threshold}'
            }

        return None

    def check_exit(self, symbol: str, price: float, klines: List,
                   signals: List[StrategySignal]) -> Optional[Dict]:
        """
        利弗莫尔平仓条件：
        1. 触及止损线
        2. 移动止损（有浮盈后回撤）
        3. 时间止损
        4. 多策略强烈反向信号
        """
        pos = self.positions.get(symbol)
        if not pos or pos.stage in ['empty', 'stopped']:
            return None

        # 计算浮盈
        if pos.side == 'buy':
            pnl_pct = (price - pos.avg_price) / pos.avg_price
        else:
            pnl_pct = (pos.avg_price - price) / pos.avg_price

        # 更新highest_pnl_pct并持久化
        if pnl_pct > pos.highest_pnl_pct:
            pos.highest_pnl_pct = pnl_pct
            self.storage.update_position_pnl(symbol, pnl_pct)

        # 1. 固定止损
        if pnl_pct <= -self.stop_pct:
            return {'reason': f'止损: 浮亏{pnl_pct*100:.1f}%<=-{self.stop_pct*100}%'}

        # 2. 移动止损（有浮盈后保护）
        if pos.highest_pnl_pct > self.trigger_pct:
            drawdown = pos.highest_pnl_pct - pnl_pct
            if drawdown >= self.trailing_pct:
                return {'reason': f'移动止损: 最高浮盈{pos.highest_pnl_pct*100:.1f}%，回撤{drawdown*100:.1f}%'}

        # 3. 时间止损（从最后一次加仓时间计算，避免加仓后立即触发）
        try:
            from datetime import datetime, timedelta
            # 获取最后一次操作时间（stages中最后一条记录）
            last_stage_time = pos.stages[-1]['time'] if pos.stages else pos.entry_time
            last_dt = datetime.fromisoformat(last_stage_time)
            hold_hours = (datetime.now() - last_dt).total_seconds() / 3600
            if hold_hours >= 48:
                return {'reason': f'时间止损: 持仓{hold_hours:.0f}h>=48h'}
            if hold_hours >= 24 and pnl_pct < 0.01:
                return {'reason': f'超时减仓: 持仓{hold_hours:.0f}h，浮盈仅{pnl_pct*100:.1f}%'}
        except:
            pass

        # 4. 多策略强烈反向信号（阈值从0.7降到0.55，匹配实际信号范围）
        contra_signals = [s for s in signals
                         if s.strategy == StrategyType.CONTRARIAN
                         and s.action != 'hold'
                         and s.confidence > 0.55]
        if contra_signals:
            sig = contra_signals[0]
            if (pos.side == 'buy' and sig.action == 'sell') or \
               (pos.side == 'sell' and sig.action == 'buy'):
                return {'reason': f'多策略反向: {sig.reason}'}

        return None

    def check_add(self, symbol: str, price: float, klines: List,
                  signals: List[StrategySignal]) -> Optional[Dict]:
        """
        利弗莫尔加仓条件：
        浮盈达到触发线 + 趋势确认
        """
        pos = self.positions.get(symbol)
        if not pos or pos.stage in ['empty', 'stopped']:
            return None

        # 计算浮盈
        if pos.side == 'buy':
            pnl_pct = (price - pos.avg_price) / pos.avg_price
        else:
            pnl_pct = (pos.avg_price - price) / pos.avg_price

        # 趋势确认
        trend_ok = True
        if len(klines) >= 26:
            closes = np.array([k[4] for k in klines], dtype=float)
            ema12 = self._ema(closes, 12)
            ema26 = self._ema(closes, 26)
            if pos.side == 'buy':
                trend_ok = ema12[-1] > ema26[-1]
            else:
                trend_ok = ema12[-1] < ema26[-1]

        # 加仓阶段判断
        stage_count = len(pos.stages)

        if stage_count == 1 and pnl_pct >= self.trigger_pct:
            if trend_ok:
                amount = self.balance * self.add_ratio * self.leverage / price
                return {'amount': amount, 'reason': f'浮盈{pnl_pct*100:.1f}%>=触发{self.trigger_pct*100}%，第一次加仓'}

        elif stage_count == 2 and pnl_pct >= self.trigger_pct * 2:
            if trend_ok:
                amount = self.balance * self.add_ratio * self.leverage / price
                return {'amount': amount, 'reason': f'浮盈{pnl_pct*100:.1f}%>=触发{self.trigger_pct*200}%，第二次加仓'}

        elif stage_count == 3 and pnl_pct >= self.trigger_pct * 3:
            if trend_ok:
                amount = self.balance * self.full_ratio * self.leverage / price
                return {'amount': amount, 'reason': f'趋势确认！浮盈{pnl_pct*100:.1f}%，全力出击'}

        return None

    @staticmethod
    def _ema(data, period):
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        return ema
