"""
模拟交易引擎 v2
使用SQLite存储，Binance真实数据
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from loguru import logger

from core.data.binance_data import BinanceDataCollector
from core.strategy.engine import StrategyEngine
from core.storage.sqlite_storage import SQLiteStorage
from core.notify.feishu_notifier import notifier


class SimulationEngineV2:
    """模拟交易引擎 v2 - SQLite存储"""
    
    def __init__(self, initial_balance: float = 10.0, db_path: str = "data/trading.db"):
        """初始化模拟引擎
        
        Args:
            initial_balance: 初始资金（U）
            db_path: 数据库路径
        """
        self.collector = BinanceDataCollector()
        self.strategy = StrategyEngine()
        self.storage = SQLiteStorage(db_path)
        
        # 账户状态
        self.balance = initial_balance
        self.positions: Dict = {}
        self.total_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # 交易参数
        self.leverage = 20  # 杠杆倍数
        self.position_size = 0.5  # 每次使用50%资金
        self.stop_loss_pct = 0.03  # 3%止损
        self.take_profit_pct = 0.06  # 6%止盈
        
        # 加载账户状态
        self._load_account_state()
        
        logger.info(f"模拟引擎v2初始化完成，余额: {self.balance:.4f}U")
    
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
    
    def _save_notification(self, message: str):
        """保存通知消息到文件"""
        import os
        os.makedirs('data/notifications', exist_ok=True)
        
        # 写入待发送文件
        filename = f"data/notifications/pending_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(message)
        
        logger.info(f"通知已保存: {filename}")
    
    def format_price(self, price) -> str:
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
            
            # 保存K线到数据库
            self.storage.save_klines(symbol, '1h', klines)
            
            # 获取当前价格
            ticker = self.collector.collect_ticker(symbol)
            current_price = ticker['last']
            
            # 保存行情到数据库
            self.storage.save_ticker(symbol, ticker)
            
            # 转换为Gate.io格式（策略引擎使用）
            gate_symbol = symbol.replace('USDT', '/USDT')
            
            # 策略分析
            signal = self.strategy.analyze(gate_symbol, klines)
            
            # 保存信号到数据库
            self.storage.save_signal({
                'symbol': symbol,
                'signal_type': signal.signal_type,
                'price': current_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'confidence': signal.confidence,
                'reason': signal.reason
            })
            
            # 保存技术指标
            if symbol in [s.replace('/', '') for s in ['DOGE/USDT', 'PEPE/USDT']]:
                indicators = self.strategy.trend_strategy.calculate_indicators(klines)
                if len(indicators) > 0:
                    latest = indicators.iloc[-1]
                    self.storage.save_indicators(symbol, '1h', {
                        'ema_20': latest.get('ema_20'),
                        'ema_50': latest.get('ema_50'),
                        'ema_200': latest.get('ema_200'),
                        'rsi_14': latest.get('rsi'),
                        'macd': latest.get('macd'),
                        'macd_signal': latest.get('macd_signal'),
                        'macd_hist': latest.get('macd_hist'),
                        'bb_upper': latest.get('bb_upper'),
                        'bb_middle': latest.get('bb_middle'),
                        'bb_lower': latest.get('bb_lower'),
                        'volume_ma_20': latest.get('volume_ma'),
                        'volume_ratio': latest.get('volume', 0) / latest.get('volume_ma', 1) if latest.get('volume_ma', 0) > 0 else 1
                    })
            
            logger.info(f"分析 {symbol}: 价格={self.format_price(current_price)}, 信号={signal.signal_type}")
            
            # 检查是否有持仓需要平仓
            if symbol in self.positions:
                self._check_exit(symbol, current_price)
            
            # 检查是否需要开仓
            if signal.signal_type != 'hold' and symbol not in self.positions:
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
        if signal.signal_type == 'buy':
            stop_loss = current_price * (1 - self.stop_loss_pct)
            take_profit = current_price * (1 + self.take_profit_pct)
        else:
            stop_loss = current_price * (1 + self.stop_loss_pct)
            take_profit = current_price * (1 - self.take_profit_pct)
        
        # 保存交易记录到数据库
        entry_time = datetime.now().isoformat()
        self.storage.save_trade({
            'symbol': symbol,
            'side': signal.signal_type,
            'entry_price': current_price,
            'amount': amount,
            'leverage': self.leverage,
            'entry_time': entry_time,
            'status': 'open'
        })
        
        # 获取交易ID
        trades = self.storage.get_trades(symbol, status='open', limit=1)
        trade_id = trades[0]['id'] if trades else None
        
        # 记录持仓
        self.positions[symbol] = {
            'side': signal.signal_type,
            'entry_price': current_price,
            'amount': amount,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'entry_time': entry_time,
            'trade_id': trade_id
        }
        
        # 保存账户状态
        self._save_account_state()
        
        logger.info(f"开仓 {symbol}: {signal.signal_type} @ {self.format_price(current_price)}, "
                   f"止损={self.format_price(stop_loss)}, 止盈={self.format_price(take_profit)}")
    
    def _check_exit(self, symbol: str, current_price: float):
        """检查是否需要平仓"""
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
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
        pos = self.positions[symbol]
        
        # 计算盈亏
        entry_price = pos['entry_price']
        amount = pos['amount']
        margin = amount * entry_price / self.leverage
        
        if pos['side'] == 'buy':
            pnl = (exit_price - entry_price) * amount
        else:
            pnl = (entry_price - exit_price) * amount
        
        pnl_pct = pnl / margin * 100
        
        # 更新账户
        self.balance += pnl
        self.total_pnl += pnl
        self.total_trades += 1
        
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # 更新数据库交易记录
        if pos.get('trade_id'):
            self.storage.update_trade(pos['trade_id'], {
                'exit_price': exit_price,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'exit_time': datetime.now().isoformat(),
                'duration': str(datetime.now() - datetime.fromisoformat(pos['entry_time'])),
                'reason': reason,
                'status': 'closed'
            })
        
        # 删除持仓
        del self.positions[symbol]
        
        # 保存账户状态
        self._save_account_state()
        
        # 生成通知消息并写入文件
        trade_data = {
            'symbol': symbol,
            'side': pos['side'],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason,
            'exit_time': datetime.now().isoformat()
        }
        message = notifier.format_trade_message(trade_data)
        self._save_notification(message)
        
        logger.info(f"平仓 {symbol}: {reason}, 盈亏={pnl:+.4f}U ({pnl_pct:+.2f}%)")
    
    def get_status(self) -> Dict:
        """获取模拟状态"""
        return {
            'balance': self.balance,
            'total_pnl': self.total_pnl,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.winning_trades / max(self.total_trades, 1) * 100,
            'positions': self.positions,
            'db_info': self.storage.get_database_info()
        }
    
    def get_report(self) -> str:
        """生成报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("📊 模拟交易报告 v2 (SQLite)")
        lines.append("=" * 60)
        
        # 账户信息
        lines.append(f"\n💰 账户信息:")
        lines.append(f"   当前余额: {self.balance:.4f}U")
        lines.append(f"   总盈亏: {self.total_pnl:+.4f}U")
        lines.append(f"   收益率: {self.total_pnl / 10 * 100:+.2f}%")
        lines.append(f"   总交易: {self.total_trades} 笔")
        lines.append(f"   胜率: {self.winning_trades / max(self.total_trades, 1) * 100:.1f}%")
        
        # 持仓信息
        if self.positions:
            lines.append(f"\n📈 当前持仓:")
            for symbol, pos in self.positions.items():
                lines.append(f"   {symbol}:")
                lines.append(f"     方向: {pos['side']}")
                lines.append(f"     入场价: ${self.format_price(pos['entry_price'])}")
                lines.append(f"     数量: {pos['amount']:.2f}")
                lines.append(f"     止损: ${self.format_price(pos['stop_loss'])}")
                lines.append(f"     止盈: ${self.format_price(pos['take_profit'])}")
        
        # 最近交易
        recent_trades = self.storage.get_trades(limit=5)
        if recent_trades:
            lines.append(f"\n📝 最近交易:")
            for trade in recent_trades:
                pnl = trade.get('pnl', 0)
                pnl_sign = "+" if pnl and pnl > 0 else ""
                time_str = trade.get("exit_time") or trade.get("entry_time") or ""
                sym = trade["symbol"]
                lines.append(f"   [{time_str[:19]}] {sym}")
                ep = trade.get('entry_price') or 0
                xp = trade.get('exit_price') or 0
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
        
        return "\n".join(lines)
    
    def run_once(self):
        """运行一次分析"""
        symbols = ['DOGEUSDT', 'PEPEUSDT']
        
        for symbol in symbols:
            self.analyze_and_trade(symbol)
        
        # 打印报告
        print(self.get_report())


# 使用示例
if __name__ == '__main__':
    engine = SimulationEngineV2(initial_balance=10.0)
    engine.run_once()