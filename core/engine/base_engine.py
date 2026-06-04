"""
交易引擎基类
============

所有策略共用的基础设施：
- 市场情绪分析
- 多策略信号融合
- 风控管理
- 持仓管理
- 报告生成

具体策略只需继承并实现 evaluate() 方法。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from loguru import logger

from core.analysis.market_sentiment import MarketSentiment
from core.strategy.multi_strategy import MultiStrategyEngine, StrategySignal
from core.risk.risk_manager import RiskManager
from core.data.binance_data import BinanceDataCollector
from core.storage.sqlite_storage import SQLiteStorage


class Position:
    """通用持仓"""
    def __init__(self, symbol: str, side: str, entry_price: float,
                 amount: float, cost: float, strategy: str = ""):
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.avg_price = entry_price
        self.amount = amount
        self.cost = cost           # 保证金
        self.strategy = strategy   # 来自哪个策略
        self.stage = "open"
        self.entry_time = datetime.now().isoformat()
        self.stop_loss = 0.0
        self.take_profit = 0.0
        self.highest_pnl_pct = 0.0
        self.stages = []

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol, 'side': self.side,
            'entry_price': self.entry_price, 'avg_price': self.avg_price,
            'amount': self.amount, 'cost': self.cost,
            'strategy': self.strategy, 'stage': self.stage,
            'entry_time': self.entry_time, 'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'highest_pnl_pct': self.highest_pnl_pct,
        }


class BaseEngine(ABC):
    """
    交易引擎基类
    
    生命周期：
    1. 初始化（加载配置、模块）
    2. 采集数据（K线、情绪）
    3. 分析市场（趋势、波动率）
    4. 生成信号（多策略融合）
    5. 风控检查（仓位、黑天鹅）
    6. 执行交易（开仓/加仓/平仓）
    7. 保存状态
    """

    def __init__(self, initial_balance: float = 10.0,
                 db_path: str = "data/trading.db",
                 config: Dict = None):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.config = config or {}
        self.leverage = self.config.get('leverage', 10)

        # === 公共模块（所有策略共用）===
        self.data_collector = BinanceDataCollector()
        self.sentiment = MarketSentiment()
        self.multi_strategy = MultiStrategyEngine()
        self.risk_manager = RiskManager(initial_balance)
        self.storage = SQLiteStorage(db_path)

        # 持仓
        self.positions: Dict[str, Position] = {}

        # 统计
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.trade_history: List[Dict] = []

        # 加载状态
        self._load_state()

        logger.info(f"⚙️ 引擎初始化完成 | 余额: {self.balance:.4f}U | 杠杆: {self.leverage}x")

    # ========== 公共流程 ==========

    def run_once(self, symbols: List[str] = None):
        """
        运行一次完整分析周期（模板方法）
        
        子类不需要重写此方法，只需实现各步骤的具体逻辑。
        """
        symbols = symbols or self.config.get('symbols', ['DOGEUSDT', 'PEPEUSDT'])

        # 1. 采集数据
        kline_data = {}
        for symbol in symbols:
            klines = self.data_collector.collect_klines(symbol, '1h', 100)
            if klines:
                kline_data[symbol] = klines

        if not kline_data:
            logger.warning("无法获取K线数据")
            return

        # 2. 市场情绪（全局，所有策略共用）
        sentiment_data = self.sentiment.get_full_sentiment(symbols)

        # 3. 市场状态分析（子类可重写）
        market_state = self.analyze_market(kline_data, sentiment_data)

        # 4. 调整多策略权重
        regime = market_state.get('regime', 'ranging')
        self.multi_strategy.adjust_weights(regime, sentiment_data.get('sentiment_score', 50))

        # 5. 对每个交易对执行分析
        for symbol in symbols:
            if symbol not in kline_data:
                continue

            klines = kline_data[symbol]
            current_price = float(klines[-1][4])

            # 5a. 获取策略信号（多策略融合 + 子类信号）
            signals = self.generate_signals(symbol, klines, market_state, sentiment_data)

            # 5b. 风控检查（如果有持仓）
            if symbol in self.positions:
                risk_result = self.risk_manager.check_force_close(
                    symbol, self.positions[symbol].to_dict(), current_price, klines
                )
                if risk_result['should_close']:
                    self._close_position(symbol, current_price, risk_result['reason'])
                    continue

                # 检查子类的平仓逻辑
                exit_action = self.check_exit(symbol, current_price, klines, signals)
                if exit_action:
                    self._close_position(symbol, current_price, exit_action['reason'])
                    continue

                # 检查加仓逻辑
                add_action = self.check_add(symbol, current_price, klines, signals)
                if add_action:
                    self._add_position(symbol, current_price, add_action)

            else:
                # 5c. 开仓逻辑（子类实现）
                open_action = self.check_open(symbol, current_price, klines, signals, sentiment_data)
                if open_action:
                    # 风控调整仓位
                    risk_check = self.risk_manager.check_open_allowed(
                        symbol, open_action.get('side', 'buy'),
                        open_action.get('amount', 0), current_price,
                        self.balance, {s: p.to_dict() for s, p in self.positions.items()},
                        self.leverage, klines
                    )

                    if risk_check['allowed']:
                        adjusted_amount = risk_check['adjusted_amount']
                        if adjusted_amount > 0:
                            self._open_position(
                                symbol, open_action.get('side', 'buy'),
                                current_price, adjusted_amount,
                                open_action.get('strategy', 'unknown'),
                                open_action.get('stop_loss', 0),
                                open_action.get('take_profit', 0)
                            )
                            if risk_check['warnings']:
                                logger.info(f"⚠️ 风控调整: {risk_check['warnings']}")
                    else:
                        logger.debug(f"风控拒绝开仓 {symbol}: {risk_check['reason']}")

        # 6. 保存状态
        self._save_state()

        # 7. 输出报告
        self.print_report(sentiment_data, market_state)

    # ========== 子类必须实现 ==========

    @abstractmethod
    def analyze_market(self, kline_data: Dict, sentiment: Dict) -> Dict:
        """
        分析市场状态
        
        Returns:
            {'regime': 'trending_up'|'ranging'|'volatile'|'trending_down', ...}
        """
        pass

    @abstractmethod
    def check_open(self, symbol: str, price: float, klines: List,
                   signals: List[StrategySignal], sentiment: Dict) -> Optional[Dict]:
        """
        检查是否开仓
        
        Returns:
            None 或 {'side': 'buy'|'sell', 'amount': float, 'strategy': str,
                     'stop_loss': float, 'take_profit': float, 'reason': str}
        """
        pass

    @abstractmethod
    def check_exit(self, symbol: str, price: float, klines: List,
                   signals: List[StrategySignal]) -> Optional[Dict]:
        """
        检查是否平仓
        
        Returns:
            None 或 {'reason': str}
        """
        pass

    @abstractmethod
    def check_add(self, symbol: str, price: float, klines: List,
                  signals: List[StrategySignal]) -> Optional[Dict]:
        """
        检查是否加仓
        
        Returns:
            None 或 {'amount': float, 'reason': str}
        """
        pass

    # ========== 可选重写 ==========

    def generate_signals(self, symbol: str, klines: List,
                         market_state: Dict, sentiment: Dict) -> List[StrategySignal]:
        """
        生成交易信号（默认使用多策略引擎，子类可重写）
        """
        return self.multi_strategy.evaluate_all(symbol, klines, market_state, sentiment)

    def print_report(self, sentiment: Dict = None, market_state: Dict = None):
        """输出报告（子类可重写扩展）"""
        total_value = self.balance
        for pos in self.positions.values():
            if pos.stage not in ['empty', 'stopped']:
                total_value += pos.cost

        pnl = total_value - self.initial_balance
        pnl_pct = pnl / self.initial_balance * 100

        print("=" * 50)
        print(f"💰 余额: {self.balance:.4f}U | 总价值: {total_value:.4f}U | 盈亏: {pnl:+.4f}U ({pnl_pct:+.1f}%)")
        print(f"📊 交易: {self.total_trades} | 胜率: {self.winning_trades/max(1,self.total_trades)*100:.0f}%")

        if sentiment:
            print(self.sentiment.format_report(sentiment))

        if market_state:
            print(f"📈 市场: {market_state.get('regime', '?')}")

        # 持仓
        if self.positions:
            print("📋 持仓:")
            for sym, pos in self.positions.items():
                if pos.stage not in ['empty', 'stopped']:
                    print(f"   {sym}: {pos.side} | {pos.strategy} | 均价={pos.avg_price:.6f} | 止损={pos.stop_loss:.6f}")
        else:
            print("📋 持仓: 无")

        # 风控状态
        print(self.risk_manager.get_status())

        # 多策略信号
        print(self.multi_strategy.get_report([]))

        print("=" * 50)

    # ========== 通用交易操作 ==========

    def _open_position(self, symbol: str, side: str, price: float,
                       amount: float, strategy: str,
                       stop_loss: float = 0, take_profit: float = 0):
        """开仓"""
        cost = amount * price / self.leverage

        pos = Position(symbol, side, price, amount, cost, strategy)
        pos.stop_loss = stop_loss
        pos.take_profit = take_profit
        pos.stages.append({
            'stage': 'open', 'price': price, 'amount': amount,
            'time': pos.entry_time, 'strategy': strategy
        })

        self.positions[symbol] = pos
        self.balance -= cost
        self.total_trades += 1

        # 保存到数据库
        self.storage.save_trade({
            'symbol': symbol, 'side': side, 'entry_price': price,
            'amount': amount, 'stop_loss': stop_loss, 'take_profit': take_profit,
            'entry_time': pos.entry_time, 'status': 'open'
        })
        
        # 保存到positions表
        self.storage.save_position(symbol, side, amount, price, self.leverage)

        logger.info(f"📈 开仓 {symbol}: {side} @ {price:.6f} | 策略={strategy} | "
                    f"数量={amount:.4f} | 止损={stop_loss:.6f}")

    def _add_position(self, symbol: str, price: float, action: Dict):
        """加仓"""
        pos = self.positions.get(symbol)
        if not pos:
            return

        add_amount = action.get('amount', 0)
        if add_amount <= 0:
            return

        # 更新均价
        total_cost_val = pos.avg_price * pos.amount + price * add_amount
        pos.amount += add_amount
        pos.avg_price = total_cost_val / pos.amount

        add_cost = add_amount * price / self.leverage
        pos.cost += add_cost
        self.balance -= add_cost

        # 更新止损价（基于新的均价）
        stop_pct = getattr(self, 'stop_pct', 0.07)  # 默认7%
        if pos.side == 'buy':
            pos.stop_loss = pos.avg_price * (1 - stop_pct)
        else:
            pos.stop_loss = pos.avg_price * (1 + stop_pct)
        
        # 更新take_profit
        trigger_pct = getattr(self, 'trigger_pct', 0.05)  # 默认5%
        if pos.side == 'buy':
            pos.take_profit = pos.avg_price * (1 + trigger_pct * 4)
        else:
            pos.take_profit = pos.avg_price * (1 - trigger_pct * 4)

        pos.stages.append({
            'stage': 'add', 'price': price, 'amount': add_amount,
            'time': datetime.now().isoformat(), 'reason': action.get('reason', '')
        })

        logger.info(f"📈 加仓 {symbol}: {price:.6f} | +{add_amount:.4f} | "
                    f"均价={pos.avg_price:.6f} | 止损={pos.stop_loss:.6f} | {action.get('reason', '')}")

    def _close_position(self, symbol: str, price: float, reason: str):
        """平仓"""
        pos = self.positions.get(symbol)
        if not pos:
            return

        # 计算盈亏
        if pos.side == 'buy':
            pnl_pct = (price - pos.avg_price) / pos.avg_price
        else:
            pnl_pct = (pos.avg_price - price) / pos.avg_price

        pnl_amount = pos.cost * pnl_pct * self.leverage

        # 更新统计
        self.total_pnl += pnl_amount
        if pnl_amount > 0:
            self.winning_trades += 1

        # 恢复保证金
        self.balance += pos.cost + pnl_amount

        # 记录
        result = {
            'symbol': symbol, 'side': pos.side, 'strategy': pos.strategy,
            'entry_price': pos.entry_price, 'avg_price': pos.avg_price,
            'exit_price': price, 'pnl_pct': pnl_pct * 100,
            'pnl_amount': pnl_amount, 'reason': reason,
            'stages': len(pos.stages), 'hold_time': pos.entry_time
        }
        self.trade_history.append(result)

        # 更新数据库中的交易记录
        from datetime import datetime
        self.storage.update_trade_by_symbol_time(
            symbol=symbol,
            entry_time=pos.entry_time,
            updates={
                'exit_price': price,
                'pnl': pnl_amount,
                'pnl_pct': pnl_pct * 100,
                'exit_time': datetime.now().isoformat(),
                'reason': reason,
                'status': 'closed'
            }
        )
        
        # 从positions表删除
        self.storage.remove_position(symbol)

        # 通知风控
        self.risk_manager.record_trade_result(pnl_amount)

        # 标记
        pos.stage = 'stopped'

        emoji = "✅" if pnl_amount > 0 else "❌"
        logger.info(f"{emoji} 平仓 {symbol}: {reason} | 盈亏={pnl_pct*100:.2f}% ({pnl_amount:+.4f}U) | 策略={pos.strategy}")

    # ========== 状态管理 ==========

    def _load_state(self):
        """加载状态"""
        snapshot = self.storage.get_latest_snapshot()
        if snapshot:
            self.balance = snapshot['balance']
            self.total_pnl = snapshot.get('total_pnl', 0)
            self.total_trades = snapshot.get('total_trades', 0)
            self.winning_trades = snapshot.get('winning_trades', 0)
        
        # 从positions表加载持仓
        open_positions = self.storage.get_open_positions()
        for pos_data in open_positions:
            symbol = pos_data['symbol']
            # 只加载trades表中状态为open的持仓
            open_trades = self.storage.get_trades(symbol=symbol, status='open')
            if open_trades:
                trade = open_trades[0]
                pos = Position(
                    symbol=symbol,
                    side=trade['side'],
                    entry_price=trade['entry_price'],
                    amount=trade['amount'],
                    cost=trade['amount'] * trade['entry_price'] / self.leverage,
                    strategy='livermore'
                )
                pos.entry_time = trade['entry_time']
                # 恢复stages信息（根据open trades数量）
                for i, t in enumerate(open_trades):
                    pos.stages.append({
                        'stage': 'open' if i == 0 else 'add',
                        'price': t['entry_price'],
                        'amount': t['amount'],
                        'time': t['entry_time']
                    })
                # 恢复highest_pnl_pct
                pos.highest_pnl_pct = pos_data.get('highest_pnl_pct', 0)
                self.positions[symbol] = pos

    def _save_state(self):
        """保存状态"""
        open_pos = len([p for p in self.positions.values() if p.stage not in ['empty', 'stopped']])
        self.storage.save_account_snapshot({
            'balance': self.balance, 'total_pnl': self.total_pnl,
            'total_trades': self.total_trades, 'winning_trades': self.winning_trades,
            'losing_trades': self.total_trades - self.winning_trades,
            'open_positions': open_pos
        })
