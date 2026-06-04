"""
交易执行器
"""
import time
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime, timedelta
from dataclasses import dataclass

from core.exchange.gate_rest import GateRestClient
from core.strategy.engine import Signal
from config.settings import trading_config, gate_config


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    side: str
    amount: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    leverage: int
    liquidation_price: float
    timestamp: datetime


class TradeExecutor:
    """交易执行器"""
    
    def __init__(self, sandbox: bool = True):
        """初始化交易执行器
        
        Args:
            sandbox: 是否使用模拟盘
        """
        self.client = GateRestClient(
            api_key=gate_config.api_key,
            secret_key=gate_config.secret_key,
            sandbox=sandbox
        )
        
        self.sandbox = sandbox
        self.positions = {}  # 当前持仓
        self.daily_trades = 0  # 当日交易次数
        self.daily_pnl = 0.0  # 当日盈亏
        self.last_reset = datetime.now()
        
        logger.info(f"交易执行器初始化完成 (模拟盘: {sandbox})")
    
    def reset_daily_stats(self):
        """重置每日统计"""
        now = datetime.now()
        if now.date() > self.last_reset.date():
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.last_reset = now
            logger.info("每日统计已重置")
    
    def check_risk_limits(self, signal: Signal) -> bool:
        """检查风控限制
        
        Args:
            signal: 交易信号
            
        Returns:
            是否允许交易
        """
        self.reset_daily_stats()
        
        # 检查每日交易次数
        if self.daily_trades >= trading_config.max_daily_trades:
            logger.warning(f"达到每日交易上限: {self.daily_trades}")
            return False
        
        # 检查每日亏损
        if self.daily_pnl < -trading_config.max_daily_loss * trading_config.initial_capital:
            logger.warning(f"达到每日最大亏损: {self.daily_pnl:.2f}U")
            return False
        
        # 检查是否已有持仓
        if signal.symbol in self.positions:
            logger.warning(f"已有持仓: {signal.symbol}")
            return False
        
        return True
    
    def calculate_position_size(self, signal: Signal) -> float:
        """计算仓位大小
        
        Args:
            signal: 交易信号
            
        Returns:
            仓位大小（USDT）
        """
        # 获取账户余额
        balance = self.client.get_balance()
        available = balance['USDT']['free']
        
        # 计算仓位
        position_value = available * trading_config.position_size
        
        # 计算杠杆后的仓位
        leverage = trading_config.leverage.get(signal.symbol, 20)
        position_amount = position_value * leverage
        
        # 转换为合约数量
        if signal.price > 0:
            contracts = position_amount / signal.price
        else:
            contracts = 0
        
        logger.info(f"仓位计算: 可用={available:.2f}U, 仓位={position_value:.2f}U, "
                    f"杠杆={leverage}x, 合约={contracts:.2f}")
        
        return contracts
    
    def execute_signal(self, signal: Signal) -> Optional[Dict]:
        """执行交易信号
        
        Args:
            signal: 交易信号
            
        Returns:
            订单信息或None
        """
        # 检查信号类型
        if signal.signal_type == 'hold':
            logger.info(f"观望信号，不执行: {signal.symbol}")
            return None
        
        # 检查风控
        if not self.check_risk_limits(signal):
            return None
        
        try:
            # 计算仓位
            amount = self.calculate_position_size(signal)
            
            if amount <= 0:
                logger.warning("仓位计算为0，不执行")
                return None
            
            # 设置杠杆
            leverage = trading_config.leverage.get(signal.symbol, 20)
            self.client.set_leverage(signal.symbol, leverage)
            
            # 创建订单
            order = self.client.create_order(
                symbol=signal.symbol,
                side=signal.signal_type,
                amount=amount,
                order_type='market',
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )
            
            # 更新统计
            self.daily_trades += 1
            
            # 记录持仓
            self.positions[signal.symbol] = Position(
                symbol=signal.symbol,
                side=signal.signal_type,
                amount=amount,
                entry_price=signal.price,
                mark_price=signal.price,
                unrealized_pnl=0,
                leverage=leverage,
                liquidation_price=signal.stop_loss,
                timestamp=datetime.now()
            )
            
            logger.info(f"订单执行成功: {signal.symbol} {signal.signal_type} {amount} @ {signal.price}")
            
            return order
            
        except Exception as e:
            logger.error(f"订单执行失败: {e}")
            return None
    
    def update_positions(self):
        """更新持仓信息"""
        try:
            positions = self.client.get_positions()
            
            # 清空已平仓的持仓
            closed_symbols = []
            for symbol in self.positions:
                if not any(p['symbol'] == symbol for p in positions):
                    closed_symbols.append(symbol)
            
            for symbol in closed_symbols:
                logger.info(f"持仓已平仓: {symbol}")
                del self.positions[symbol]
            
            # 更新持仓信息
            for pos in positions:
                if pos['symbol'] in self.positions:
                    self.positions[pos['symbol']].mark_price = pos['markPrice']
                    self.positions[pos['symbol']].unrealized_pnl = pos['unrealizedPnl']
                    
        except Exception as e:
            logger.error(f"更新持仓失败: {e}")
    
    def check_stop_loss_take_profit(self):
        """检查止损止盈"""
        self.update_positions()
        
        for symbol, position in list(self.positions.items()):
            try:
                ticker = self.client.get_ticker(symbol)
                current_price = ticker['last']
                
                # 计算盈亏百分比
                if position.side == 'buy':
                    pnl_pct = (current_price - position.entry_price) / position.entry_price
                else:
                    pnl_pct = (position.entry_price - current_price) / position.entry_price
                
                # 检查止损
                if pnl_pct <= -trading_config.stop_loss_pct:
                    logger.info(f"触发止损: {symbol} 亏损 {pnl_pct:.2%}")
                    self.close_position(symbol, '止损')
                
                # 检查止盈
                elif pnl_pct >= trading_config.take_profit_pct:
                    logger.info(f"触发止盈: {symbol} 盈利 {pnl_pct:.2%}")
                    self.close_position(symbol, '止盈')
                    
            except Exception as e:
                logger.error(f"检查止损止盈失败 {symbol}: {e}")
    
    def close_position(self, symbol: str, reason: str = '手动'):
        """平仓
        
        Args:
            symbol: 交易对
            reason: 平仓原因
        """
        if symbol not in self.positions:
            logger.warning(f"无持仓: {symbol}")
            return
        
        position = self.positions[symbol]
        
        try:
            # 创建平仓订单
            close_side = 'sell' if position.side == 'buy' else 'buy'
            order = self.client.create_order(
                symbol=symbol,
                side=close_side,
                amount=position.amount,
                order_type='market'
            )
            
            # 计算盈亏
            ticker = self.client.get_ticker(symbol)
            current_price = ticker['last']
            
            if position.side == 'buy':
                pnl = (current_price - position.entry_price) * position.amount
            else:
                pnl = (position.entry_price - current_price) * position.amount
            
            # 扣除手续费
            fee = position.amount * position.entry_price * trading_config.trading_fee * 2
            pnl -= fee
            
            # 更新统计
            self.daily_pnl += pnl
            
            logger.info(f"平仓成功: {symbol} 原因={reason} 盈亏={pnl:.2f}U")
            
            # 删除持仓记录
            del self.positions[symbol]
            
            return order
            
        except Exception as e:
            logger.error(f"平仓失败 {symbol}: {e}")
            return None
    
    def get_status(self) -> Dict:
        """获取交易状态"""
        return {
            'sandbox': self.sandbox,
            'positions': len(self.positions),
            'daily_trades': self.daily_trades,
            'daily_pnl': self.daily_pnl,
            'position_details': [
                {
                    'symbol': p.symbol,
                    'side': p.side,
                    'amount': p.amount,
                    'entry_price': p.entry_price,
                    'mark_price': p.mark_price,
                    'unrealized_pnl': p.unrealized_pnl,
                    'leverage': p.leverage,
                }
                for p in self.positions.values()
            ]
        }


# 使用示例
if __name__ == '__main__':
    # 创建交易执行器（模拟盘）
    executor = TradeExecutor(sandbox=True)
    
    # 获取状态
    status = executor.get_status()
    print(f"交易状态: {status}")