"""
利弗莫尔策略模拟引擎
====================

集成利弗莫尔金字塔加仓策略的模拟交易引擎。
与engine_v3并列，可独立运行或对比测试。
"""

import json
from datetime import datetime
from typing import Dict, Optional
from loguru import logger

from core.data.binance_data import BinanceDataCollector
from core.signal.signal_generator_v3 import SignalGeneratorV3
from core.strategy.livermore import (
    LivermoreStrategy, LivermoreConfig, LivermoreStage
)
from core.storage.sqlite_storage import SQLiteStorage


class LivermoreEngine:
    """利弗莫尔策略模拟引擎"""
    
    def __init__(self, initial_balance: float = 10.0,
                 config: LivermoreConfig = None,
                 db_path: str = "data/trading.db"):
        self.collector = BinanceDataCollector()
        self.signal_gen = SignalGeneratorV3()
        self.storage = SQLiteStorage(db_path)
        self.strategy = LivermoreStrategy(config)
        
        self.balance = initial_balance
        self.initial_balance = initial_balance
        
        # 加载状态
        self._load_state()
        
        logger.info(f"📈 利弗莫尔引擎初始化完成，余额: {self.balance:.4f}U")
    
    def _load_state(self):
        """从数据库加载状态"""
        snapshot = self.storage.get_latest_snapshot()
        if snapshot:
            self.balance = snapshot['balance']
            logger.info(f"加载余额: {self.balance:.4f}U")
    
    def _save_state(self):
        """保存状态"""
        self.storage.save_account_snapshot({
            'balance': self.balance,
            'total_pnl': self.strategy.total_pnl,
            'total_trades': self.strategy.total_trades,
            'winning_trades': self.strategy.winning_trades,
            'losing_trades': self.strategy.total_trades - self.strategy.winning_trades,
            'open_positions': len([p for p in self.strategy.positions.values()
                                   if p.stage not in [LivermoreStage.EMPTY, LivermoreStage.STOPPED]])
        })
    
    def run_once(self, symbols: list = None):
        """运行一次分析"""
        symbols = symbols or ['DOGEUSDT', 'PEPEUSDT']
        
        for symbol in symbols:
            self._analyze(symbol)
        
        self._save_state()
        print(self.get_report())
    
    def _analyze(self, symbol: str):
        """分析单个交易对"""
        try:
            # 获取数据
            klines = self.collector.collect_klines(symbol, '1h', 100)
            if not klines:
                logger.warning(f"无法获取 {symbol} K线数据")
                return
            
            current_price = float(klines[-1][4])
            
            # 生成信号
            signal = self.signal_gen.generate_signal(symbol)
            if not signal:
                logger.warning(f"无法生成 {symbol} 信号")
                return
            
            # 保存信号
            self.storage.save_signal({
                'symbol': symbol,
                'signal_type': signal['signal'],
                'price': current_price,
                'stop_loss': 0,
                'take_profit': 0,
                'confidence': signal['confidence'],
                'reason': str(signal.get('details', ''))
            })
            
            # 利弗莫尔评估
            result = self.strategy.evaluate(
                symbol, current_price, klines, signal['score']
            )
            
            action = result['action']
            ratio = result['position_ratio']
            
            logger.info(f"📊 {symbol}: 价格={self._fmt(current_price)}, "
                       f"信号={signal['signal']}({signal['score']}), "
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
        leverage_amount = margin * self.strategy.config.leverage
        amount = leverage_amount / price
        
        pos = self.strategy.open_position(symbol, side, price, amount, self.balance)
        self.balance -= margin
        
        # 保存交易
        self.storage.save_trade({
            'symbol': symbol,
            'side': side,
            'entry_price': price,
            'amount': amount,
            'stop_loss': pos.stop_loss,
            'take_profit': price * 1.5,  # 150%作为最大止盈
            'entry_time': pos.entry_time,
            'status': 'open'
        })
    
    def _execute_add(self, symbol: str, price: float, ratio: float, action: str):
        """执行加仓"""
        margin = self.balance * ratio
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
            # 恢复保证金+盈亏
            pos = self.strategy.positions.get(symbol)
            if pos:
                self.balance += pos.total_cost + result['pnl_amount']
            
            # 更新交易记录
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
        
        # 释放部分保证金
        released = reduce_amount * price / self.strategy.config.leverage
        self.balance += released * 0.9  # 留10%作为手续费缓冲
        
        logger.info(f"📉 减仓 {symbol}: 减少{reduce_amount:.4f}, "
                    f"剩余{pos.total_amount:.4f}")
    
    def get_report(self) -> str:
        """生成报告"""
        total_value = self.balance
        for pos in self.strategy.positions.values():
            if pos.stage not in [LivermoreStage.EMPTY, LivermoreStage.STOPPED]:
                total_value += pos.total_cost
        
        pnl = total_value - self.initial_balance
        pnl_pct = pnl / self.initial_balance * 100
        
        lines = [
            "=" * 50,
            "📈 利弗莫尔策略报告",
            "=" * 50,
            f"初始资金: {self.initial_balance:.4f} U",
            f"当前余额: {self.balance:.4f} U",
            f"总价值:   {total_value:.4f} U",
            f"总盈亏:   {pnl:+.4f} U ({pnl_pct:+.2f}%)",
            f"总交易:   {self.strategy.total_trades}",
            f"盈利交易: {self.strategy.winning_trades}",
            f"胜率:     {self.strategy.winning_trades/max(1,self.strategy.total_trades)*100:.0f}%",
            "",
            self.strategy.get_position_summary(),
            "=" * 50
        ]
        
        return "\n".join(lines)
    
    @staticmethod
    def _fmt(price: float) -> str:
        if price < 0.001:
            return f"{price:.8f}"
        elif price < 1:
            return f"{price:.6f}"
        else:
            return f"{price:.4f}"
