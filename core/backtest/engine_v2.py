"""
优化版回测引擎
使用趋势过滤和优化参数
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

from ..storage.sqlite_storage import SQLiteStorage
from ..signal.signal_generator_v3 import SignalGeneratorV3


class BacktestEngineV2:
    """优化版回测引擎"""
    
    def __init__(self, db_manager: SQLiteStorage = None):
        """初始化回测引擎"""
        self.db_manager = db_manager or SQLiteStorage()
        self.signal_generator = SignalGeneratorV3(self.db_manager)
        
        # 交易参数
        self.initial_capital = 10000  # 初始资金 10000U
        self.leverage = 10            # 杠杆倍数
        self.position_ratio = 0.2     # 仓位比例
        self.stop_loss_pct = 1.5      # 止损比例
        self.take_profit_pct = 15     # 止盈比例
        self.fee_rate = 0.001         # 手续费率 0.1%
        
        # 回测结果
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        
        print("📊 优化版回测引擎 v2 初始化完成")
    
    def run_backtest(self, symbol: str, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            symbol: 交易对
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            回测结果
        """
        # 获取历史数据
        historical_data = self._get_historical_data(symbol, start_date, end_date)
        
        if not historical_data:
            return {'error': '无历史数据'}
        
        # 初始化状态
        capital = self.initial_capital
        position = None  # 当前仓位
        equity_history = [capital]
        trade_history = []
        
        # 模拟交易
        for i in range(50, len(historical_data)):
            # 获取当前K线
            current_kline = historical_data[i]
            current_price = current_kline[4]  # 收盘价
            current_time = datetime.fromtimestamp(current_kline[0] / 1000)
            
            # 获取历史窗口（用于信号生成）
            kline_window = historical_data[max(0, i-100):i+1]
            
            # 生成信号
            signal = self._generate_signal_from_klines(symbol, kline_window)
            
            # 检查止损止盈
            if position:
                pnl_pct = self._calculate_pnl_pct(position, current_price)
                
                # 止损
                if pnl_pct <= -self.stop_loss_pct:
                    capital = self._close_position(position, current_price, '止损')
                    trade_history.append({
                        'time': current_time,
                        'type': 'sell',
                        'price': current_price,
                        'reason': '止损',
                        'pnl': capital - position['entry_capital'],
                        'capital': capital
                    })
                    position = None
                
                # 止盈
                elif pnl_pct >= self.take_profit_pct:
                    capital = self._close_position(position, current_price, '止盈')
                    trade_history.append({
                        'time': current_time,
                        'type': 'sell',
                        'price': current_price,
                        'reason': '止盈',
                        'pnl': capital - position['entry_capital'],
                        'capital': capital
                    })
                    position = None
            
            # 开仓信号
            if not position:
                if signal['signal'] == 'buy' and signal['score'] >= 65:
                    # 多头开仓
                    position = self._open_position('long', current_price, capital)
                    trade_history.append({
                        'time': current_time,
                        'type': 'buy',
                        'price': current_price,
                        'reason': f"信号得分: {signal['score']}",
                        'capital': capital
                    })
                elif signal['signal'] == 'sell' and signal['score'] <= 35:
                    # 空头开仓
                    position = self._open_position('short', current_price, capital)
                    trade_history.append({
                        'time': current_time,
                        'type': 'sell',
                        'price': current_price,
                        'reason': f"信号得分: {signal['score']}",
                        'capital': capital
                    })
            
            # 记录权益
            if position:
                unrealized_pnl = self._calculate_unrealized_pnl(position, current_price)
                equity_history.append(capital + unrealized_pnl)
            else:
                equity_history.append(capital)
        
        # 计算统计指标
        stats = self._calculate_statistics(trade_history, equity_history)
        
        return {
            'symbol': symbol,
            'period': f"{start_date} - {end_date}",
            'initial_capital': self.initial_capital,
            'final_capital': capital,
            'trades': trade_history,
            'equity_curve': equity_history,
            'statistics': stats
        }
    
    def _get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> list:
        """获取历史数据"""
        # 计算需要的K线数量
        delta = end_date - start_date
        hours = delta.total_seconds() / 3600
        limit = int(hours)
        
        # 从数据库获取K线数据
        klines = self.db_manager.get_klines(symbol, '1h', limit)
        
        if not klines:
            return []
        
        return klines
    
    def _generate_signal_from_klines(self, symbol: str, klines: list) -> Dict[str, Any]:
        """从K线生成信号"""
        # 创建临时数据
        temp_data = []
        for k in klines:
            temp_data.append({
                'timestamp': k[0],
                'open': k[1],
                'high': k[2],
                'low': k[3],
                'close': k[4],
                'volume': k[5]
            })
        
        # 使用信号生成器
        original_get = self.db_manager.get_klines
        self.db_manager.get_klines = lambda s, tf, limit: klines
        signal = self.signal_generator.generate_signal(symbol)
        self.db_manager.get_klines = original_get
        
        return signal
    
    def _open_position(self, side: str, price: float, capital: float) -> Dict[str, Any]:
        """开仓"""
        position_size = capital * self.position_ratio
        margin = position_size / self.leverage
        
        return {
            'side': side,
            'entry_price': price,
            'entry_capital': capital,
            'position_size': position_size,
            'margin': margin,
            'entry_time': datetime.now()
        }
    
    def _close_position(self, position: Dict, current_price: float, reason: str) -> float:
        """平仓"""
        entry_price = position['entry_price']
        position_size = position['position_size']
        
        # 计算盈亏
        if position['side'] == 'long':
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price
        
        pnl = position_size * pnl_pct * self.leverage
        
        # 扣除手续费
        fee = position_size * self.fee_rate * 2
        net_pnl = pnl - fee
        
        # 更新资金
        new_capital = position['entry_capital'] + net_pnl
        
        return new_capital
    
    def _calculate_pnl_pct(self, position: Dict, current_price: float) -> float:
        """计算盈亏百分比"""
        entry_price = position['entry_price']
        
        if position['side'] == 'long':
            return (current_price - entry_price) / entry_price * 100
        else:
            return (entry_price - current_price) / entry_price * 100
    
    def _calculate_unrealized_pnl(self, position: Dict, current_price: float) -> float:
        """计算未实现盈亏"""
        pnl_pct = self._calculate_pnl_pct(position, current_price) / 100
        return position['position_size'] * pnl_pct * self.leverage
    
    def _calculate_statistics(self, trades: list, equity_curve: list) -> Dict[str, Any]:
        """计算统计指标"""
        if not trades:
            return {}
        
        # 计算胜率
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0
        
        # 计算平均盈亏
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([abs(t['pnl']) for t in losing_trades]) if losing_trades else 0
        
        # 计算盈亏比
        profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 计算最大回撤
        peak = equity_curve[0]
        max_drawdown = 0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 计算总收益
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0] * 100
        
        # 计算夏普比率
        returns = np.diff(equity_curve) / equity_curve[:-1]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate * 100, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown': round(max_drawdown, 2),
            'total_return': round(total_return, 2),
            'sharpe_ratio': round(sharpe_ratio, 2)
        }
    
    def update_parameters(self, params: Dict[str, Any]):
        """更新参数"""
        if 'leverage' in params:
            self.leverage = params['leverage']
        if 'position_ratio' in params:
            self.position_ratio = params['position_ratio']
        if 'stop_loss' in params:
            self.stop_loss_pct = params['stop_loss']
        if 'take_profit' in params:
            self.take_profit_pct = params['take_profit']
        
        # 同时更新信号生成器参数
        self.signal_generator.update_parameters(params)
        
        print(f"📊 回测参数已更新")