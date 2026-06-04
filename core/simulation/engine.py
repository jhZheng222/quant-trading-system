"""
模拟交易引擎
使用Binance真实数据，虚拟账户模拟交易
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from loguru import logger
import os

from core.data.binance_data import BinanceDataCollector
from core.strategy.engine import StrategyEngine


@dataclass
class VirtualAccount:
    """虚拟账户"""
    balance: float = 10.0  # 初始资金10U
    positions: Dict = field(default_factory=dict)  # 持仓
    total_pnl: float = 0.0  # 总盈亏
    total_trades: int = 0  # 总交易次数
    winning_trades: int = 0  # 盈利次数
    losing_trades: int = 0  # 亏损次数
    
    def to_dict(self):
        return {
            'balance': self.balance,
            'positions': self.positions,
            'total_pnl': self.total_pnl,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.winning_trades / max(self.total_trades, 1) * 100
        }


@dataclass
class TradeRecord:
    """交易记录"""
    id: int
    symbol: str
    side: str  # 'buy' or 'sell'
    entry_price: float
    exit_price: float
    amount: float
    pnl: float
    pnl_pct: float
    entry_time: str
    exit_time: str
    duration: str
    reason: str
    
    def to_dict(self):
        return asdict(self)


class SimulationEngine:
    """模拟交易引擎"""
    
    def __init__(self, initial_balance: float = 10.0):
        """初始化模拟引擎
        
        Args:
            initial_balance: 初始资金（U）
        """
        self.collector = BinanceDataCollector()
        self.strategy = StrategyEngine()
        self.account = VirtualAccount(balance=initial_balance)
        self.trades: List[TradeRecord] = []
        self.trade_id = 0
        
        # 交易参数
        self.leverage = 20  # 杠杆倍数
        self.position_size = 0.5  # 每次使用50%资金
        self.stop_loss_pct = 0.03  # 3%止损
        self.take_profit_pct = 0.06  # 6%止盈
        
        # 数据文件
        self.data_file = "data/simulation_history.json"
        self.load_history()
        
        logger.info(f"模拟引擎初始化完成，初始资金: {initial_balance}U")
    
    def load_history(self):
        """加载历史数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.account = VirtualAccount(**data.get('account', {}))
                    self.trades = [TradeRecord(**t) for t in data.get('trades', [])]
                    self.trade_id = len(self.trades)
                    logger.info(f"加载历史数据: {len(self.trades)} 笔交易")
            except Exception as e:
                logger.error(f"加载历史数据失败: {e}")
    
    def save_history(self):
        """保存历史数据"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        data = {
            'account': self.account.to_dict(),
            'trades': [t.to_dict() for t in self.trades],
            'last_update': datetime.now().isoformat()
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def analyze_and_trade(self, symbol: str):
        """分析并模拟交易
        
        Args:
            symbol: Binance交易对格式，如 'DOGEUSDT'
        """
        try:
            # 获取K线数据
            klines = self.collector.collect_klines(symbol, '1h', 100)
            if not klines:
                return
            
            # 获取当前价格
            ticker = self.collector.collect_ticker(symbol)
            current_price = ticker['last']
            
            # 转换为Gate.io格式（策略引擎使用）
            gate_symbol = symbol.replace('USDT', '/USDT')
            
            # 策略分析
            signal = self.strategy.analyze(gate_symbol, klines)
            
            logger.info(f"分析 {symbol}: 价格={current_price}, 信号={signal.signal_type}")
            
            # 检查是否有持仓需要平仓
            if symbol in self.account.positions:
                self._check_exit(symbol, current_price)
            
            # 检查是否需要开仓
            if signal.signal_type != 'hold' and symbol not in self.account.positions:
                self._open_position(symbol, signal, current_price)
            
        except Exception as e:
            logger.error(f"分析失败 {symbol}: {e}")
    
    def _open_position(self, symbol: str, signal, current_price: float):
        """开仓"""
        # 计算仓位
        available = self.account.balance * self.position_size
        leverage_amount = available * self.leverage
        amount = leverage_amount / current_price
        
        # 计算止损止盈
        if signal.signal_type == 'buy':
            stop_loss = current_price * (1 - self.stop_loss_pct)
            take_profit = current_price * (1 + self.take_profit_pct)
        else:
            stop_loss = current_price * (1 + self.stop_loss_pct)
            take_profit = current_price * (1 - self.take_profit_pct)
        
        # 记录持仓
        self.account.positions[symbol] = {
            'side': signal.signal_type,
            'entry_price': current_price,
            'amount': amount,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'entry_time': datetime.now().isoformat(),
            'margin': available
        }
        
        logger.info(f"开仓 {symbol}: {signal.signal_type} @ {current_price}, "
                   f"止损={stop_loss}, 止盈={take_profit}")
    
    def _check_exit(self, symbol: str, current_price: float):
        """检查是否需要平仓"""
        if symbol not in self.account.positions:
            return
        
        pos = self.account.positions[symbol]
        entry_price = pos['entry_price']
        side = pos['side']
        
        # 计算盈亏百分比
        if side == 'buy':
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price
        
        # 检查止损止盈
        should_exit = False
        reason = ""
        
        if pnl_pct <= -self.stop_loss_pct:
            should_exit = True
            reason = "止损"
        elif pnl_pct >= self.take_profit_pct:
            should_exit = True
            reason = "止盈"
        
        if should_exit:
            self._close_position(symbol, current_price, reason)
    
    def _close_position(self, symbol: str, exit_price: float, reason: str):
        """平仓"""
        pos = self.account.positions[symbol]
        
        # 计算盈亏
        entry_price = pos['entry_price']
        amount = pos['amount']
        margin = pos['margin']
        
        if pos['side'] == 'buy':
            pnl = (exit_price - entry_price) * amount
        else:
            pnl = (entry_price - exit_price) * amount
        
        pnl_pct = pnl / margin * 100
        
        # 更新账户
        self.account.balance += pnl
        self.account.total_pnl += pnl
        self.account.total_trades += 1
        
        if pnl > 0:
            self.account.winning_trades += 1
        else:
            self.account.losing_trades += 1
        
        # 记录交易
        self.trade_id += 1
        trade = TradeRecord(
            id=self.trade_id,
            symbol=symbol,
            side=pos['side'],
            entry_price=entry_price,
            exit_price=exit_price,
            amount=amount,
            pnl=pnl,
            pnl_pct=pnl_pct,
            entry_time=pos['entry_time'],
            exit_time=datetime.now().isoformat(),
            duration=str(datetime.now() - datetime.fromisoformat(pos['entry_time'])),
            reason=reason
        )
        self.trades.append(trade)
        
        # 删除持仓
        del self.account.positions[symbol]
        
        # 保存历史
        self.save_history()
        
        logger.info(f"平仓 {symbol}: {reason}, 盈亏={pnl:.4f}U ({pnl_pct:.2f}%)")
    
    def get_status(self) -> Dict:
        """获取模拟状态"""
        return {
            'account': self.account.to_dict(),
            'positions': self.account.positions,
            'recent_trades': [t.to_dict() for t in self.trades[-10:]],
            'total_trades': len(self.trades)
        }
    
    def format_price(self, price: float, symbol: str = '') -> str:
        """格式化价格显示"""
        if price < 0.0001:
            return f"{price:.10f}"
        elif price < 0.01:
            return f"{price:.8f}"
        elif price < 1:
            return f"{price:.6f}"
        else:
            return f"{price:.4f}"
    
    def get_report(self) -> str:
        """生成报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("📊 模拟交易报告")
        lines.append("=" * 60)
        
        # 账户信息
        lines.append(f"\n💰 账户信息:")
        lines.append(f"   当前余额: {self.account.balance:.4f}U")
        lines.append(f"   总盈亏: {self.account.total_pnl:+.4f}U")
        lines.append(f"   收益率: {self.account.total_pnl / 10 * 100:+.2f}%")
        lines.append(f"   总交易: {self.account.total_trades} 笔")
        lines.append(f"   胜率: {self.account.winning_trades / max(self.account.total_trades, 1) * 100:.1f}%")
        
        # 持仓信息
        if self.account.positions:
            lines.append(f"\n📈 当前持仓:")
            for symbol, pos in self.account.positions.items():
                lines.append(f"   {symbol}:")
                lines.append(f"     方向: {pos['side']}")
                lines.append(f"     入场价: ${self.format_price(pos['entry_price'], symbol)}")
                lines.append(f"     数量: {pos['amount']:.2f}")
                lines.append(f"     止损: ${self.format_price(pos['stop_loss'], symbol)}")
                lines.append(f"     止盈: ${self.format_price(pos['take_profit'], symbol)}")
        
        # 最近交易
        if self.trades:
            lines.append(f"\n📝 最近交易:")
            for trade in self.trades[-5:]:
                pnl_sign = "+" if trade.pnl > 0 else ""
                lines.append(f"   [{trade.exit_time[:19]}] {trade.symbol}")
                lines.append(f"     {trade.side} ${self.format_price(trade.entry_price)} -> ${self.format_price(trade.exit_price)}")
                lines.append(f"     盈亏: {pnl_sign}{trade.pnl:.4f}U ({pnl_sign}{trade.pnl_pct:.2f}%)")
                lines.append(f"     原因: {trade.reason}")
        
        lines.append(f"\n⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def run_once(self):
        """运行一次分析"""
        symbols = ['DOGEUSDT', 'PEPEUSDT']
        
        for symbol in symbols:
            self.analyze_and_trade(symbol)
        
        # 打印报告
        print(self.get_report())
        
        # 保存历史
        self.save_history()


# 使用示例
if __name__ == '__main__':
    engine = SimulationEngine(initial_balance=10.0)
    engine.run_once()