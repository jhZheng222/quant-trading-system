"""
模拟交易引擎 v3
集成庄家行为分析信号系统
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

from core.data.binance_data import BinanceDataCollector
from core.signal.signal_generator_v2 import SignalGeneratorV2
from core.storage.sqlite_storage import SQLiteStorage


class SimulationEngineV3:
    """模拟交易引擎 v3 - 庄家行为分析"""
    
    def __init__(self, initial_balance: float = 10.0, db_path: str = "data/trading.db"):
        """初始化模拟引擎"""
        self.collector = BinanceDataCollector()
        self.signal_generator = SignalGeneratorV2()
        self.storage = SQLiteStorage(db_path)
        
        # 账户状态
        self.balance = initial_balance
        self.positions: Dict = {}
        self.total_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # 交易参数（优化后保守策略）
        self.leverage = 10  # 杠杆倍数（从20降到10）
        self.position_size = 0.15  # 每次使用15%资金（从30%降到15%）
        self.stop_loss_pct = 0.03  # 3%止损
        self.take_profit_pct = 0.10  # 10%止盈
        
        # 信号阈值（优化后）
        self.buy_threshold = 55    # 买入阈值（降低，更多入场机会）
        self.sell_threshold = 35   # 卖出阈值（降低）
        
        # 加载账户状态
        self._load_account_state()
        
        logger.info(f"模拟引擎v3初始化完成，余额: {self.balance:.4f}U")
    
    def _load_account_state(self):
        """从数据库加载账户状态"""
        snapshot = self.storage.get_latest_snapshot()
        if snapshot:
            self.balance = snapshot['balance']
            self.total_pnl = snapshot['total_pnl']
            self.total_trades = snapshot['total_trades']
            self.winning_trades = snapshot['winning_trades']
            self.losing_trades = snapshot['losing_trades']
            logger.info(f"加载账户状态: 余额={self.balance:.4f}U")
        
        # 加载未平仓交易
        open_trades = self.storage.get_open_trades()
        for trade in open_trades:
            self.positions[trade['symbol']] = {
                'side': trade['side'],
                'entry_price': trade['entry_price'],
                'amount': trade['amount'],
                'stop_loss': trade.get('stop_loss', 0),
                'take_profit': trade.get('take_profit', 0),
                'entry_time': trade['entry_time'],
                'trade_id': trade['id']
            }
    
    def _save_account_state(self):
        """保存账户状态到数据库"""
        self.storage.save_account_snapshot({
            'balance': self.balance,
            'total_pnl': self.total_pnl,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'open_positions': len(self.positions)
        })
    
    def run_once(self):
        """运行一次分析"""
        symbols = ['DOGEUSDT', 'PEPEUSDT']
        
        for symbol in symbols:
            self.analyze_and_trade(symbol)
        
        # 打印报告
        print(self.get_report())
    
    def analyze_and_trade(self, symbol: str):
        """分析并模拟交易"""
        try:
            # 生成综合信号
            signal = self.signal_generator.generate_signal(symbol)
            if not signal:
                logger.warning(f"无法生成 {symbol} 的信号")
                return
            
            current_price = signal.current_price
            
            # 保存信号到数据库
            self.storage.save_signal({
                'symbol': symbol,
                'signal_type': signal.signal,
                'price': current_price,
                'stop_loss': 0,
                'take_profit': 0,
                'confidence': signal.confidence,
                'reason': ', '.join(signal.reasons)
            })
            
            logger.info(f"分析 {symbol}: 价格={self.format_price(current_price)}, "
                       f"信号={signal.signal}, 评分={signal.score}")
            
            # 检查是否有持仓需要平仓
            if symbol in self.positions:
                self._check_exit(symbol, current_price, signal)
            
            # 检查是否需要开仓
            if signal.signal in ['buy', 'strong_buy'] and symbol not in self.positions:
                if signal.score >= self.buy_threshold:
                    self._open_position(symbol, signal, current_price)
            
        except Exception as e:
            logger.error(f"分析失败 {symbol}: {e}")
    
    def _open_position(self, symbol: str, signal, current_price: float):
        """开仓"""
        # 计算仓位
        available = self.balance * self.position_size
        leverage_amount = available * self.leverage
        amount = leverage_amount / current_price
        
        # 计算止损止盈
        if signal.signal in ['buy', 'strong_buy']:
            stop_loss = current_price * (1 - self.stop_loss_pct)
            take_profit = current_price * (1 + self.take_profit_pct)
            side = 'buy'
        else:
            stop_loss = current_price * (1 + self.stop_loss_pct)
            take_profit = current_price * (1 - self.take_profit_pct)
            side = 'sell'
        
        # 保存交易记录到数据库
        entry_time = datetime.now().isoformat()
        trade_id = self.storage.save_trade({
            'symbol': symbol,
            'side': side,
            'entry_price': current_price,
            'amount': amount,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'entry_time': entry_time,
            'status': 'open'
        })
        
        # 更新内存状态
        self.positions[symbol] = {
            'side': side,
            'entry_price': current_price,
            'amount': amount,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'entry_time': entry_time,
            'trade_id': trade_id
        }
        
        # 扣除保证金
        self.balance -= available
        
        logger.info(f"开仓 {symbol}: {side} @ {self.format_price(current_price)}, "
                   f"数量={amount:.2f}, 止损={self.format_price(stop_loss)}, "
                   f"止盈={self.format_price(take_profit)}")
    
    def _check_exit(self, symbol: str, current_price: float, signal):
        """检查是否需要平仓"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        entry_price = position['entry_price']
        stop_loss = position['stop_loss']
        take_profit = position['take_profit']
        
        # 检查止损
        if position['side'] == 'buy':
            if current_price <= stop_loss:
                self._close_position(symbol, current_price, '止损')
                return
            if current_price >= take_profit:
                self._close_position(symbol, current_price, '止盈')
                return
            # 反向信号
            if signal.signal in ['sell', 'strong_sell']:
                self._close_position(symbol, current_price, '反向信号')
                return
        else:  # sell
            if current_price >= stop_loss:
                self._close_position(symbol, current_price, '止损')
                return
            if current_price <= take_profit:
                self._close_position(symbol, current_price, '止盈')
                return
            # 反向信号
            if signal.signal in ['buy', 'strong_buy']:
                self._close_position(symbol, current_price, '反向信号')
                return
    
    def _close_position(self, symbol: str, current_price: float, reason: str):
        """平仓"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        entry_price = position['entry_price']
        amount = position['amount']
        
        # 计算盈亏
        if position['side'] == 'buy':
            pnl = (current_price - entry_price) * amount
        else:
            pnl = (entry_price - current_price) * amount
        
        pnl_pct = (pnl / (entry_price * amount)) * 100
        
        # 更新账户状态
        self.balance += pnl
        self.total_pnl += pnl
        self.total_trades += 1
        
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # 更新数据库
        self.storage.update_trade(position['trade_id'], {
            'exit_price': current_price,
            'exit_time': datetime.now().isoformat(),
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason,
            'status': 'closed'
        })
        
        # 删除持仓
        del self.positions[symbol]
        
        # 保存账户状态
        self._save_account_state()
        
        logger.info(f"平仓 {symbol}: {reason}, 盈亏={pnl:.4f}U ({pnl_pct:.2f}%)")
    
    def format_price(self, price: float) -> str:
        """格式化价格显示"""
        if price is None:
            return "0"
        price = float(price)
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
        lines = [
            "=" * 60,
            "📊 模拟交易报告 v3（庄家行为分析）",
            "=" * 60,
            f"\n💰 账户信息:",
            f"   余额: {self.balance:.4f}U",
            f"   总盈亏: {self.total_pnl:.4f}U",
            f"   总交易: {self.total_trades}",
            f"   胜率: {(self.winning_trades/self.total_trades*100) if self.total_trades > 0 else 0:.1f}%",
        ]
        
        # 持仓信息
        if self.positions:
            lines.append(f"\n📈 当前持仓:")
            for symbol, pos in self.positions.items():
                lines.append(f"   {symbol}:")
                lines.append(f"     方向: {pos['side']}")
                lines.append(f"     入场价: ${self.format_price(pos['entry_price'])}")
                lines.append(f"     数量: {pos['amount']:.2f}")
        else:
            lines.append(f"\n📈 当前持仓: 无")
        
        # 最近交易
        recent_trades = self.storage.get_trades(limit=5)
        if recent_trades:
            lines.append(f"\n📝 最近交易:")
            for trade in recent_trades:
                pnl = trade.get('pnl', 0)
                pnl_sign = "+" if pnl and pnl > 0 else ""
                time_str = trade.get("exit_time") or trade.get("entry_time") or ""
                sym = trade.get("symbol", "unknown")
                ep = trade.get('entry_price') or 0
                xp = trade.get('exit_price') or 0
                lines.append(f"   [{time_str[:19]}] {sym}")
                lines.append(f"     {trade.get('side','?')} ${self.format_price(ep)} -> ${self.format_price(xp)}")
                if pnl:
                    pct = trade.get('pnl_pct') or 0
                    lines.append(f"     盈亏: {pnl_sign}{pnl:.4f}U ({pnl_sign}{pct:.2f}%)")
                lines.append(f"     原因: {trade.get('reason', '开仓中')}")
        
        # 数据库信息
        db_info = self.storage.get_database_info()
        lines.append(f"\n💾 数据库信息:")
        lines.append(f"   行情记录: {db_info.get('tickers', 0)} 条")
        lines.append(f"   K线数据: {db_info.get('klines', 0)} 条")
        lines.append(f"   交易信号: {db_info.get('signals', 0)} 条")
        lines.append(f"   交易记录: {db_info.get('trades', 0)} 条")
        lines.append(f"   数据库大小: {db_info.get('db_size', '0 KB')}")
        
        lines.append(f"\n⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        
        return '\n'.join(lines)


# 测试
if __name__ == '__main__':
    engine = SimulationEngineV3(initial_balance=10.0)
    engine.run_once()
