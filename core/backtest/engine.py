"""
回测引擎（Backtest Engine）
使用历史数据验证策略有效性
数据来源：统一数据服务（DataService）
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass, asdict

from core.data.service import DataService
from core.signal.signal_generator_v2 import SignalGeneratorV2


@dataclass
class BacktestTrade:
    """回测交易记录"""
    symbol: str
    side: str                 # buy/sell
    entry_price: float
    exit_price: float
    entry_time: str
    exit_time: str
    amount: float
    pnl: float                # 盈亏（USDT）
    pnl_pct: float            # 盈亏百分比
    reason: str               # 平仓原因
    signal_score: int         # 入场信号评分


@dataclass
class BacktestResult:
    """回测结果"""
    symbol: str
    start_date: str
    end_date: str
    initial_balance: float
    final_balance: float
    total_return: float       # 总收益率
    total_return_pct: float   # 总收益率百分比
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float           # 胜率
    avg_win: float            # 平均盈利
    avg_loss: float           # 平均亏损
    profit_factor: float      # 盈亏比
    max_drawdown: float       # 最大回撤
    max_drawdown_pct: float   # 最大回撤百分比
    sharpe_ratio: float       # 夏普比率
    trades: List[BacktestTrade]


class BacktestEngine:
    """回测引擎
    
    使用历史数据验证策略有效性
    """
    
    def __init__(self, initial_balance: float = 1000.0):
        self.data_service = DataService.get_instance()
        self.signal_generator = SignalGeneratorV2()
        
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: Dict = {}
        self.trades: List[BacktestTrade] = []
        
        # 交易参数
        self.leverage = 20
        self.position_size = 0.3  # 30%资金
        self.stop_loss_pct = 0.03  # 3%止损
        self.take_profit_pct = 0.10  # 10%止盈
        
        # 信号阈值
        self.buy_threshold = 55
        self.sell_threshold = 45
        
        logger.info(f"回测引擎初始化完成，初始资金: {initial_balance}U")
    
    def run_backtest(self, symbol: str, days: int = 30) -> Optional[BacktestResult]:
        """运行回测
        
        Args:
            symbol: 交易对，如 'DOGEUSDT'
            days: 回测天数
            
        Returns:
            BacktestResult 对象或 None
        """
        try:
            # 获取历史K线数据（从统一数据服务）
            # 先确保有数据
            self.data_service.collect_all_klines('1h', days * 24)
            klines = self.data_service.get_latest_klines(symbol, '1h')
            
            if not klines or len(klines) < 48:
                logger.warning(f"无法获取足够的历史数据")
                return None
            
            logger.info(f"开始回测 {symbol}，数据量: {len(klines)} 根K线")
            
            # 重置状态
            self.balance = self.initial_balance
            self.positions = {}
            self.trades = []
            
            # 模拟交易
            for i in range(24, len(klines)):
                # 获取当前K线
                current_kline = klines[i]
                current_time = datetime.fromtimestamp(current_kline[0] / 1000)
                current_price = current_kline[4]  # close price
                
                # 获取历史数据（用于计算指标）
                history_klines = klines[:i+1]
                
                # 生成信号
                signal = self._generate_signal_from_klines(symbol, history_klines, current_price)
                if not signal:
                    continue
                
                # 检查持仓
                if symbol in self.positions:
                    self._check_exit(symbol, current_price, current_time.isoformat(), signal)
                
                # 检查开仓
                if signal['signal'] in ['buy', 'strong_buy'] and symbol not in self.positions:
                    if signal['score'] >= self.buy_threshold:
                        self._open_position(symbol, 'buy', current_price, current_time.isoformat(), signal['score'])
                elif signal['signal'] in ['sell', 'strong_sell'] and symbol not in self.positions:
                    if signal['score'] <= self.sell_threshold:
                        self._open_position(symbol, 'sell', current_price, current_time.isoformat(), signal['score'])
            
            # 平仓所有持仓
            final_price = klines[-1][4]
            final_time = datetime.fromtimestamp(klines[-1][0] / 1000)
            for symbol in list(self.positions.keys()):
                self._close_position(symbol, final_price, final_time.isoformat(), '回测结束')
            
            # 计算结果
            result = self._calculate_result(symbol, klines)
            
            logger.info(f"回测完成: 总收益={result.total_return_pct:.2f}%, "
                       f"胜率={result.win_rate:.1f}%, 最大回撤={result.max_drawdown_pct:.2f}%")
            
            return result
            
        except Exception as e:
            logger.error(f"回测失败 {symbol}: {e}")
            return None
    
    def _generate_signal_from_klines(self, symbol: str, klines: List, current_price: float) -> Optional[Dict]:
        """从K线数据生成信号（简化版）
        
        不调用外部API，仅基于价格数据计算
        """
        try:
            if len(klines) < 24:
                return None
            
            # 计算简单指标
            closes = [k[4] for k in klines]
            volumes = [k[5] for k in klines]
            
            # EMA计算
            ema_20 = self._calculate_ema(closes, 20)
            ema_50 = self._calculate_ema(closes, 50)
            
            # RSI计算
            rsi = self._calculate_rsi(closes, 14)
            
            # 成交量变化
            avg_volume = sum(volumes[-24:]) / 24
            current_volume = volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # 价格位置
            high_24 = max(closes[-24:])
            low_24 = min(closes[-24:])
            price_position = (current_price - low_24) / (high_24 - low_24) if high_24 != low_24 else 0.5
            
            # 生成信号
            score = 50
            
            # EMA信号
            if ema_20 > ema_50:
                score += 10  # 多头排列
            else:
                score -= 10  # 空头排列
            
            # RSI信号
            if rsi < 30:
                score += 15  # 超卖
            elif rsi > 70:
                score -= 15  # 超买
            
            # 成交量信号
            if volume_ratio > 1.5:
                if price_position < 0.3:
                    score += 10  # 低位放量
                elif price_position > 0.7:
                    score -= 10  # 高位放量
            
            # 价格位置信号
            if price_position < 0.2:
                score += 10  # 低位
            elif price_position > 0.8:
                score -= 10  # 高位
            
            # 限制在0-100
            score = max(0, min(100, score))
            
            # 生成信号
            if score >= 70:
                signal = 'strong_buy'
            elif score >= 55:
                signal = 'buy'
            elif score >= 45:
                signal = 'hold'
            elif score >= 30:
                signal = 'sell'
            else:
                signal = 'strong_sell'
            
            return {
                'signal': signal,
                'score': score,
                'ema_20': ema_20,
                'ema_50': ema_50,
                'rsi': rsi,
                'volume_ratio': volume_ratio,
                'price_position': price_position
            }
            
        except Exception as e:
            logger.warning(f"信号生成失败: {e}")
            return None
    
    def _calculate_ema(self, data: List[float], period: int) -> float:
        """计算EMA"""
        if len(data) < period:
            return data[-1]
        
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_rsi(self, data: List[float], period: int = 14) -> float:
        """计算RSI"""
        if len(data) < period + 1:
            return 50
        
        deltas = [data[i] - data[i-1] for i in range(1, len(data))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _open_position(self, symbol: str, side: str, price: float, time: str, score: int):
        """开仓"""
        # 计算仓位
        available = self.balance * self.position_size
        leverage_amount = available * self.leverage
        amount = leverage_amount / price
        
        # 计算止损止盈
        if side == 'buy':
            stop_loss = price * (1 - self.stop_loss_pct)
            take_profit = price * (1 + self.take_profit_pct)
        else:
            stop_loss = price * (1 + self.stop_loss_pct)
            take_profit = price * (1 - self.take_profit_pct)
        
        # 保存持仓
        self.positions[symbol] = {
            'side': side,
            'entry_price': price,
            'amount': amount,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'entry_time': time,
            'signal_score': score
        }
        
        # 扣除保证金
        self.balance -= available
        
        logger.debug(f"开仓 {symbol}: {side} @ {price:.6f}, 数量={amount:.2f}")
    
    def _check_exit(self, symbol: str, price: float, time: str, signal: Dict):
        """检查平仓"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        entry_price = position['entry_price']
        stop_loss = position['stop_loss']
        take_profit = position['take_profit']
        
        # 检查止损
        if position['side'] == 'buy':
            if price <= stop_loss:
                self._close_position(symbol, price, time, '止损')
                return
            if price >= take_profit:
                self._close_position(symbol, price, time, '止盈')
                return
            if signal['signal'] in ['sell', 'strong_sell']:
                self._close_position(symbol, price, time, '反向信号')
                return
        else:  # sell
            if price >= stop_loss:
                self._close_position(symbol, price, time, '止损')
                return
            if price <= take_profit:
                self._close_position(symbol, price, time, '止盈')
                return
            if signal['signal'] in ['buy', 'strong_buy']:
                self._close_position(symbol, price, time, '反向信号')
                return
    
    def _close_position(self, symbol: str, price: float, time: str, reason: str):
        """平仓"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        entry_price = position['entry_price']
        amount = position['amount']
        
        # 计算盈亏
        if position['side'] == 'buy':
            pnl = (price - entry_price) * amount
        else:
            pnl = (entry_price - price) * amount
        
        pnl_pct = (pnl / (entry_price * amount)) * 100
        
        # 计算保证金（开仓时扣除的金额）
        margin = entry_price * amount / self.leverage
        
        # 更新余额：返还保证金 + 盈亏
        self.balance += margin + pnl
        
        # 记录交易
        trade = BacktestTrade(
            symbol=symbol,
            side=position['side'],
            entry_price=entry_price,
            exit_price=price,
            entry_time=position['entry_time'],
            exit_time=time,
            amount=amount,
            pnl=pnl,
            pnl_pct=pnl_pct,
            reason=reason,
            signal_score=position['signal_score']
        )
        self.trades.append(trade)
        
        # 删除持仓
        del self.positions[symbol]
        
        logger.debug(f"平仓 {symbol}: {reason}, 盈亏={pnl:.4f}U ({pnl_pct:.2f}%)")
    
    def _calculate_result(self, symbol: str, klines: List) -> BacktestResult:
        """计算回测结果"""
        # 基础统计
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        losing_trades = sum(1 for t in self.trades if t.pnl <= 0)
        
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        # 平均盈亏
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [t.pnl for t in self.trades if t.pnl <= 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # 盈亏比
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # 最大回撤
        max_drawdown, max_drawdown_pct = self._calculate_max_drawdown()
        
        # 夏普比率
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        # 总收益
        total_return = self.balance - self.initial_balance
        total_return_pct = (total_return / self.initial_balance) * 100
        
        # 时间范围
        start_time = datetime.fromtimestamp(klines[0][0] / 1000)
        end_time = datetime.fromtimestamp(klines[-1][0] / 1000)
        
        return BacktestResult(
            symbol=symbol,
            start_date=start_time.isoformat(),
            end_date=end_time.isoformat(),
            initial_balance=self.initial_balance,
            final_balance=self.balance,
            total_return=total_return,
            total_return_pct=total_return_pct,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            trades=self.trades
        )
    
    def _calculate_max_drawdown(self) -> Tuple[float, float]:
        """计算最大回撤"""
        if not self.trades:
            return 0.0, 0.0
        
        # 计算累计收益曲线
        balance_curve = [self.initial_balance]
        current_balance = self.initial_balance
        
        for trade in self.trades:
            current_balance += trade.pnl
            balance_curve.append(current_balance)
        
        # 计算最大回撤
        peak = balance_curve[0]
        max_drawdown = 0
        max_drawdown_pct = 0
        
        for balance in balance_curve:
            if balance > peak:
                peak = balance
            
            drawdown = peak - balance
            drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        return max_drawdown, max_drawdown_pct
    
    def _calculate_sharpe_ratio(self) -> float:
        """计算夏普比率"""
        if not self.trades or len(self.trades) < 2:
            return 0.0
        
        # 计算每笔交易的收益率
        returns = []
        for trade in self.trades:
            ret = trade.pnl_pct / 100
            returns.append(ret)
        
        # 计算平均收益率和标准差
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_return = variance ** 0.5
        
        # 夏普比率（假设无风险利率为0）
        sharpe = avg_return / std_return if std_return > 0 else 0
        
        # 年化（假设每小时交易一次）
        sharpe_annualized = sharpe * (365 * 24) ** 0.5
        
        return sharpe_annualized
    
    def format_report(self, result: BacktestResult) -> str:
        """格式化回测报告"""
        report = f"""
📊 回测报告 - {result.symbol}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 回测时间: {result.start_date[:10]} 至 {result.end_date[:10]}
💰 初始资金: {result.initial_balance:.2f}U
💰 最终资金: {result.final_balance:.2f}U
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 收益统计:
   总收益: {result.total_return:+.2f}U ({result.total_return_pct:+.2f}%)
   总交易: {result.total_trades} 笔
   盈利交易: {result.winning_trades} 笔
   亏损交易: {result.losing_trades} 笔
   胜率: {result.win_rate:.1f}%

📊 盈亏统计:
   平均盈利: {result.avg_win:+.4f}U
   平均亏损: {result.avg_loss:+.4f}U
   盈亏比: {result.profit_factor:.2f}

⚠️ 风险统计:
   最大回撤: {result.max_drawdown:.2f}U ({result.max_drawdown_pct:.2f}%)
   夏普比率: {result.sharpe_ratio:.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 最近交易:
"""
        for trade in result.trades[-5:]:
            pnl_sign = "+" if trade.pnl > 0 else ""
            report += f"   [{trade.entry_time[:10]}] {trade.side} @ {trade.entry_price:.6f} -> {trade.exit_price:.6f}\n"
            report += f"     盈亏: {pnl_sign}{trade.pnl:.4f}U ({pnl_sign}{trade.pnl_pct:.2f}%) - {trade.reason}\n"
        
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        return report


# 测试
if __name__ == '__main__':
    engine = BacktestEngine(initial_balance=1000.0)
    
    # 回测DOGE
    result = engine.run_backtest('DOGEUSDT', days=7)
    if result:
        report = engine.format_report(result)
        print(report)
