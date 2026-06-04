"""
利弗莫尔策略模拟引擎 v2 — 自适应版
====================================

集成自适应优化引擎，根据市场状态自动调整参数。
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

from core.data.binance_data import BinanceDataCollector
from core.signal.signal_generator_v3 import SignalGeneratorV3
from core.strategy.livermore import (
    LivermoreStrategy, LivermoreConfig, LivermoreStage
)
from core.strategy.adaptive_optimizer import (
    AdaptiveOptimizer, MarketState, PerformanceMetrics
)
from core.storage.sqlite_storage import SQLiteStorage


class LivermoreEngineV2:
    """利弗莫尔策略引擎 v2 — 自适应优化版"""
    
    def __init__(self, initial_balance: float = 10.0,
                 db_path: str = "data/trading.db"):
        self.collector = BinanceDataCollector()
        self.signal_gen = SignalGeneratorV3()
        self.storage = SQLiteStorage(db_path)
        self.optimizer = AdaptiveOptimizer()
        
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.strategy: Optional[LivermoreStrategy] = None
        self.current_config: Optional[LivermoreConfig] = None
        
        # 交易历史（用于计算表现）
        self.trade_history: List[Dict] = []
        
        # 加载状态
        self._load_state()
        
        logger.info(f"📈 利弗莫尔引擎v2(自适应)初始化完成，余额: {self.balance:.4f}U")
    
    def _load_state(self):
        """加载状态"""
        snapshot = self.storage.get_latest_snapshot()
        if snapshot:
            self.balance = snapshot['balance']
            logger.info(f"加载余额: {self.balance:.4f}U")
    
    def _save_state(self):
        """保存状态"""
        open_pos = 0
        if self.strategy:
            open_pos = len([p for p in self.strategy.positions.values()
                           if p.stage not in [LivermoreStage.EMPTY, LivermoreStage.STOPPED]])
        
        self.storage.save_account_snapshot({
            'balance': self.balance,
            'total_pnl': self.strategy.total_pnl if self.strategy else 0,
            'total_trades': self.strategy.total_trades if self.strategy else 0,
            'winning_trades': self.strategy.winning_trades if self.strategy else 0,
            'losing_trades': (self.strategy.total_trades - self.strategy.winning_trades) if self.strategy else 0,
            'open_positions': open_pos
        })
    
    def run_once(self, symbols: List[str] = None):
        """运行一次分析（自适应）"""
        symbols = symbols or ['DOGEUSDT', 'PEPEUSDT']
        
        # 第一步：采集K线数据
        kline_data = {}
        for symbol in symbols:
            klines = self.collector.collect_klines(symbol, '1h', 100)
            if klines:
                kline_data[symbol] = klines
        
        if not kline_data:
            logger.warning("无法获取任何K线数据")
            return
        
        # 第二步：检测市场状态（用第一个交易对的数据）
        first_symbol = list(kline_data.keys())[0]
        market_state = self.optimizer.detect_market_state(kline_data[first_symbol])
        
        # 第三步：计算策略表现
        perf = self.optimizer.calc_performance(self.trade_history)
        
        # 第四步：生成优化配置
        config = self.optimizer.get_optimized_config(market_state, perf)
        self.current_config = config
        
        # 第五步：用新配置创建/更新策略
        self.strategy = LivermoreStrategy(config)
        
        # 恢复持仓状态
        self._restore_positions()
        
        # 第六步：对每个交易对执行分析
        for symbol in symbols:
            if symbol in kline_data:
                self._analyze(symbol, kline_data[symbol], market_state)
        
        self._save_state()
        
        # 输出报告
        print(self.optimizer.format_report(market_state, config, perf))
        print()
        print(self.get_report())
    
    def _restore_positions(self):
        """从旧策略恢复持仓"""
        # 这里从数据库加载未平仓交易
        open_trades = self.storage.get_open_trades()
        for trade in open_trades:
            symbol = trade['symbol']
            if symbol not in self.strategy.positions:
                from core.strategy.livermore import LivermorePosition
                pos = LivermorePosition(
                    symbol=symbol,
                    side=trade['side'],
                    stage=LivermoreStage.BASE,
                    entry_price=trade['entry_price'],
                    avg_price=trade['entry_price'],
                    total_amount=trade['amount'],
                    total_cost=trade['amount'] * trade['entry_price'] / self.strategy.config.leverage,
                    entry_time=trade['entry_time'],
                    stop_loss=trade.get('stop_loss', 0)
                )
                pos.stages.append({
                    'stage': 'base',
                    'price': trade['entry_price'],
                    'amount': trade['amount'],
                    'time': trade['entry_time']
                })
                self.strategy.positions[symbol] = pos
    
    def _analyze(self, symbol: str, klines: List, market_state: MarketState):
        """分析单个交易对"""
        try:
            current_price = float(klines[-1][4])
            
            # 生成信号
            signal = self.signal_gen.generate_signal(symbol)
            if not signal:
                return
            
            # 保存信号
            self.storage.save_signal({
                'symbol': symbol,
                'signal_type': signal['signal'],
                'price': current_price,
                'stop_loss': 0,
                'take_profit': 0,
                'confidence': signal['confidence'],
                'reason': f"市场={market_state.regime.value}, {signal.get('details', '')}"
            })
            
            # 利弗莫尔评估
            result = self.strategy.evaluate(
                symbol, current_price, klines, signal['score']
            )
            
            action = result['action']
            ratio = result['position_ratio']
            
            logger.info(f"📊 {symbol}: 价格={self._fmt(current_price)}, "
                       f"信号={signal['signal']}({signal['score']}), "
                       f"市场={market_state.regime.value}, "
                       f"利弗莫尔={action}: {result['reason']}")
            
            # 执行操作
            if action == 'open_base':
                self._execute_open(symbol, 'buy', current_price, ratio)
            elif action in ['add1', 'add2', 'add_full']:
                self._execute_add(symbol, current_price, ratio, action)
            elif action == 'stop':
                self._execute_close(symbol, current_price, result['reason'])
            elif action == 'reduce':
                self._execute_reduce(symbol, current_price, ratio)
            
        except Exception as e:
            logger.error(f"分析失败 {symbol}: {e}")
    
    def _execute_open(self, symbol: str, side: str, price: float, ratio: float):
        """执行开仓"""
        margin = self.balance * ratio
        if margin < 0.1:  # 最小保证金
            logger.warning(f"保证金不足: {margin:.4f}U")
            return
        
        leverage_amount = margin * self.strategy.config.leverage
        amount = leverage_amount / price
        
        pos = self.strategy.open_position(symbol, side, price, amount, self.balance)
        self.balance -= margin
        
        self.storage.save_trade({
            'symbol': symbol,
            'side': side,
            'entry_price': price,
            'amount': amount,
            'stop_loss': pos.stop_loss,
            'take_profit': price * 1.5,
            'entry_time': pos.entry_time,
            'status': 'open'
        })
    
    def _execute_add(self, symbol: str, price: float, ratio: float, action: str):
        """执行加仓"""
        margin = self.balance * ratio
        if margin < 0.05:
            return
        
        leverage_amount = margin * self.strategy.config.leverage
        amount = leverage_amount / price
        
        stage_map = {
            'add1': LivermoreStage.ADD1,
            'add2': LivermoreStage.ADD2,
            'add_full': LivermoreStage.FULL
        }
        
        self.strategy.add_position(symbol, price, amount, stage_map[action])
        self.balance -= margin
    
    def _execute_close(self, symbol: str, price: float, reason: str):
        """执行平仓"""
        result = self.strategy.close_position(symbol, price, reason)
        if result:
            pos = self.strategy.positions.get(symbol)
            if pos:
                self.balance += pos.total_cost + result['pnl_amount']
            
            # 记录到历史
            self.trade_history.append(result)
            
            self.storage.save_trade({
                'symbol': symbol,
                'side': result['side'],
                'entry_price': result['entry_price'],
                'amount': 0,
                'stop_loss': 0,
                'take_profit': 0,
                'entry_time': result['hold_time'],
                'exit_time': datetime.now().isoformat(),
                'exit_price': price,
                'pnl': result['pnl_amount'],
                'pnl_pct': result['pnl_pct'],
                'status': 'closed',
                'close_reason': reason
            })
    
    def _execute_reduce(self, symbol: str, price: float, ratio: float):
        """减仓"""
        pos = self.strategy.positions.get(symbol)
        if not pos:
            return
        
        reduce_amount = pos.total_amount * abs(ratio)
        pos.total_amount -= reduce_amount
        released = reduce_amount * price / self.strategy.config.leverage
        self.balance += released * 0.9
        
        logger.info(f"📉 减仓 {symbol}: 减少{reduce_amount:.4f}, 剩余{pos.total_amount:.4f}")
    
    def get_report(self) -> str:
        """生成报告"""
        total_value = self.balance
        if self.strategy:
            for pos in self.strategy.positions.values():
                if pos.stage not in [LivermoreStage.EMPTY, LivermoreStage.STOPPED]:
                    total_value += pos.total_cost
        
        pnl = total_value - self.initial_balance
        pnl_pct = pnl / self.initial_balance * 100
        
        lines = [
            "=" * 50,
            "📈 利弗莫尔策略报告 (自适应版)",
            "=" * 50,
            f"初始资金: {self.initial_balance:.4f} U",
            f"当前余额: {self.balance:.4f} U",
            f"总价值:   {total_value:.4f} U",
            f"总盈亏:   {pnl:+.4f} U ({pnl_pct:+.2f}%)",
        ]
        
        if self.strategy:
            lines.extend([
                f"总交易:   {self.strategy.total_trades}",
                f"盈利交易: {self.strategy.winning_trades}",
                "",
                self.strategy.get_position_summary(),
            ])
        
        lines.append("=" * 50)
        return "\n".join(lines)
    
    @staticmethod
    def _fmt(price: float) -> str:
        if price < 0.001:
            return f"{price:.8f}"
        elif price < 1:
            return f"{price:.6f}"
        else:
            return f"{price:.4f}"
