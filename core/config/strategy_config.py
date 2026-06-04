"""
策略配置管理器
保存/加载优化后的策略参数，支持模拟和实盘切换
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger


CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'config')
STRATEGY_CONFIG_FILE = os.path.join(CONFIG_DIR, 'strategy_params.json')
SIMULATION_LOG_FILE = os.path.join(CONFIG_DIR, 'simulation_log.json')


class StrategyConfig:
    """策略配置管理器"""
    
    def __init__(self):
        self.config_dir = CONFIG_DIR
        self.config_file = STRATEGY_CONFIG_FILE
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """确保配置目录存在"""
        os.makedirs(self.config_dir, exist_ok=True)
    
    def save_params(self, params: Dict[str, Any], name: str = 'default', 
                    description: str = '') -> str:
        """保存策略参数"""
        configs = self._load_all_configs()
        
        configs[name] = {
            'params': params,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(configs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ 策略参数已保存: {name}")
        return self.config_file
    
    def load_params(self, name: str = 'default') -> Optional[Dict[str, Any]]:
        """加载策略参数"""
        configs = self._load_all_configs()
        
        if name in configs:
            return configs[name]['params']
        
        logger.warning(f"⚠️ 配置不存在: {name}")
        return None
    
    def list_configs(self) -> Dict[str, Dict]:
        """列出所有配置"""
        return self._load_all_configs()
    
    def delete_config(self, name: str) -> bool:
        """删除配置"""
        configs = self._load_all_configs()
        
        if name in configs:
            del configs[name]
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(configs, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 配置已删除: {name}")
            return True
        
        return False
    
    def _load_all_configs(self) -> Dict[str, Dict]:
        """加载所有配置"""
        if not os.path.exists(self.config_file):
            return {}
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return {}
    
    def export_config(self, name: str, output_file: str) -> bool:
        """导出配置到文件"""
        params = self.load_params(name)
        
        if params:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(params, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 配置已导出: {output_file}")
            return True
        
        return False
    
    def import_config(self, input_file: str, name: str = 'imported') -> bool:
        """从文件导入配置"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                params = json.load(f)
            
            self.save_params(params, name, f'从 {input_file} 导入')
            return True
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False


class SimulatedTrader:
    """模拟交易器
    
    使用优化后的参数进行模拟交易
    """
    
    def __init__(self, config_name: str = 'default'):
        self.config_manager = StrategyConfig()
        self.params = self.config_manager.load_params(config_name)
        self.config_name = config_name
        
        if not self.params:
            # 使用默认参数
            self.params = {
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.08,
                'buy_threshold': 65,
                'sell_threshold': 40,
                'position_size': 0.2
            }
            logger.warning("使用默认参数")
        
        # 模拟状态
        self.initial_balance = 10000.0
        self.balance = self.initial_balance
        self.positions: List[Dict] = []
        self.trades: List[Dict] = []
        self.equity_curve: List[float] = [self.initial_balance]
        
        # 交易统计
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0
        self.peak_balance = self.initial_balance
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        
        # 加载历史记录
        self._load_history()
        
        logger.info(f"📊 模拟交易器初始化: {config_name}")
        logger.info(f"   止损: {self.params['stop_loss_pct']*100:.0f}%")
        logger.info(f"   止盈: {self.params['take_profit_pct']*100:.0f}%")
        logger.info(f"   买入阈值: {self.params['buy_threshold']}")
        logger.info(f"   卖出阈值: {self.params['sell_threshold']}")
        logger.info(f"   仓位: {self.params['position_size']*100:.0f}%")
    
    def _load_history(self):
        """加载交易历史"""
        log_file = os.path.join(CONFIG_DIR, f'simulation_{self.config_name}.json')
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.balance = data.get('balance', self.initial_balance)
                self.trades = data.get('trades', [])
                self.equity_curve = data.get('equity_curve', [self.initial_balance])
                self.max_drawdown = data.get('max_drawdown', 0.0)
                self.max_drawdown_pct = data.get('max_drawdown_pct', 0.0)
                self.peak_balance = data.get('peak_balance', self.initial_balance)
                self.consecutive_losses = data.get('consecutive_losses', 0)
                self.max_consecutive_losses = data.get('max_consecutive_losses', 0)
                
                logger.info(f"   加载历史: {len(self.trades)}笔交易")
            except Exception as e:
                logger.warning(f"加载历史失败: {e}")
    
    def _save_history(self):
        """保存交易历史"""
        log_file = os.path.join(CONFIG_DIR, f'simulation_{self.config_name}.json')
        
        data = {
            'config_name': self.config_name,
            'balance': self.balance,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'peak_balance': self.peak_balance,
            'consecutive_losses': self.consecutive_losses,
            'max_consecutive_losses': self.max_consecutive_losses,
            'updated_at': datetime.now().isoformat()
        }
        
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def open_position(self, symbol: str, side: str, price: float, 
                      amount: float = None, reason: str = 'signal') -> Dict:
        """开仓
        
        Args:
            symbol: 交易对
            side: 方向 (buy/sell)
            price: 开仓价格
            amount: 数量（如果为None则自动计算）
            reason: 开仓原因
            
        Returns:
            交易记录
        """
        # 计算仓位
        if amount is None:
            available = self.balance * self.params['position_size']
            leverage = 10  # 默认10倍杠杆
            amount = available * leverage / price
        
        # 计算止损止盈
        if side == 'buy':
            stop_loss = price * (1 - self.params['stop_loss_pct'])
            take_profit = price * (1 + self.params['take_profit_pct'])
        else:
            stop_loss = price * (1 + self.params['stop_loss_pct'])
            take_profit = price * (1 - self.params['take_profit_pct'])
        
        # 创建持仓
        position = {
            'symbol': symbol,
            'side': side,
            'entry_price': price,
            'amount': amount,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'entry_time': datetime.now().isoformat(),
            'reason': reason
        }
        
        self.positions.append(position)
        
        logger.info(f"📈 开仓 {symbol}: {side} @ {price:.6f}, 数量={amount:.2f}")
        
        return position
    
    def close_position(self, index: int, price: float, reason: str = 'manual') -> Dict:
        """平仓
        
        Args:
            index: 持仓索引
            price: 平仓价格
            reason: 平仓原因
            
        Returns:
            交易记录
        """
        if index >= len(self.positions):
            logger.error(f"持仓索引无效: {index}")
            return {}
        
        position = self.positions[index]
        entry_price = position['entry_price']
        amount = position['amount']
        
        # 计算盈亏
        if position['side'] == 'buy':
            pnl = (price - entry_price) * amount
        else:
            pnl = (entry_price - price) * amount
        
        pnl_pct = (pnl / (entry_price * amount)) * 100
        
        # 更新余额
        self.balance += pnl
        
        # 更新回撤
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance
        
        drawdown = self.peak_balance - self.balance
        drawdown_pct = (drawdown / self.peak_balance) * 100
        
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
            self.max_drawdown_pct = drawdown_pct
        
        # 更新连续亏损
        if pnl < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses > self.max_consecutive_losses:
                self.max_consecutive_losses = self.consecutive_losses
        else:
            self.consecutive_losses = 0
        
        # 记录交易
        trade = {
            'symbol': position['symbol'],
            'side': position['side'],
            'entry_price': entry_price,
            'exit_price': price,
            'amount': amount,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'entry_time': position['entry_time'],
            'exit_time': datetime.now().isoformat(),
            'reason': reason,
            'open_reason': position['reason']
        }
        
        self.trades.append(trade)
        self.equity_curve.append(self.balance)
        
        # 删除持仓
        del self.positions[index]
        
        # 保存历史
        self._save_history()
        
        logger.info(f"📉 平仓 {trade['symbol']}: {reason}, 盈亏={pnl:.2f}U ({pnl_pct:.2f}%)")
        
        return trade
    
    def check_stop_loss_take_profit(self, symbol: str, current_price: float) -> List[Dict]:
        """检查止损止盈
        
        Args:
            symbol: 交易对
            current_price: 当前价格
            
        Returns:
            平仓交易列表
        """
        closed_trades = []
        
        for i in range(len(self.positions) - 1, -1, -1):
            position = self.positions[i]
            
            if position['symbol'] != symbol:
                continue
            
            should_close = False
            reason = ''
            
            if position['side'] == 'buy':
                if current_price <= position['stop_loss']:
                    should_close = True
                    reason = '止损'
                elif current_price >= position['take_profit']:
                    should_close = True
                    reason = '止盈'
            else:  # sell
                if current_price >= position['stop_loss']:
                    should_close = True
                    reason = '止损'
                elif current_price <= position['take_profit']:
                    should_close = True
                    reason = '止盈'
            
            if should_close:
                trade = self.close_position(i, current_price, reason)
                if trade:
                    closed_trades.append(trade)
        
        return closed_trades
    
    def get_status(self) -> Dict[str, Any]:
        """获取模拟状态"""
        total_pnl = sum(t.get('pnl', 0) for t in self.trades)
        winning_trades = sum(1 for t in self.trades if t.get('pnl', 0) > 0)
        losing_trades = sum(1 for t in self.trades if t.get('pnl', 0) < 0)
        
        # 计算平均盈亏
        wins = [t['pnl'] for t in self.trades if t['pnl'] > 0]
        losses = [t['pnl'] for t in self.trades if t['pnl'] < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # 计算盈亏比
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # 计算总持仓价值
        total_position_value = sum(
            p['entry_price'] * p['amount'] for p in self.positions
        )
        
        return {
            'config_name': self.config_name,
            'balance': self.balance,
            'initial_balance': self.initial_balance,
            'total_pnl': total_pnl,
            'total_return_pct': (total_pnl / self.initial_balance) * 100,
            'total_trades': len(self.trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': (winning_trades / len(self.trades) * 100) if self.trades else 0,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'open_positions': len(self.positions),
            'total_position_value': total_position_value,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'consecutive_losses': self.consecutive_losses,
            'max_consecutive_losses': self.max_consecutive_losses,
            'params': self.params
        }
    
    def format_status(self) -> str:
        """格式化状态"""
        status = self.get_status()
        
        report = f"""
📊 模拟交易状态 - {status['config_name']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 资金:
   初始资金: {status['initial_balance']:.2f}U
   当前余额: {status['balance']:.2f}U
   总盈亏: {status['total_pnl']:+.2f}U ({status['total_return_pct']:+.2f}%)
   持仓价值: {status['total_position_value']:.2f}U

📈 交易统计:
   总交易: {status['total_trades']}笔
   盈利交易: {status['winning_trades']}笔
   亏损交易: {status['losing_trades']}笔
   胜率: {status['win_rate']:.1f}%
   平均盈利: {status['avg_win']:+.2f}U
   平均亏损: {status['avg_loss']:+.2f}U
   盈亏比: {status['profit_factor']:.2f}

⚠️  风险指标:
   最大回撤: {status['max_drawdown']:.2f}U ({status['max_drawdown_pct']:.2f}%)
   连续亏损: {status['consecutive_losses']}笔
   最大连续亏损: {status['max_consecutive_losses']}笔

📋 当前持仓: {status['open_positions']}笔
"""
        
        # 显示持仓详情
        if self.positions:
            report += "\n   持仓明细:\n"
            for i, pos in enumerate(self.positions):
                report += f"   #{i}: {pos['symbol']} {pos['side']} @ {pos['entry_price']:.6f}\n"
                report += f"       止损={pos['stop_loss']:.6f}, 止盈={pos['take_profit']:.6f}\n"
        
        report += f"""
⚙️  策略参数:
   止损: {status['params']['stop_loss_pct']*100:.0f}%
   止盈: {status['params']['take_profit_pct']*100:.0f}%
   买入阈值: {status['params']['buy_threshold']}
   卖出阈值: {status['params']['sell_threshold']}
   仓位: {status['params']['position_size']*100:.0f}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return report
    
    def format_trades(self, limit: int = 10) -> str:
        """格式化交易历史"""
        if not self.trades:
            return "📋 无交易记录"
        
        trades = self.trades[-limit:]
        
        report = f"""
📋 交易历史（最近{limit}笔）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        for trade in trades:
            pnl_emoji = "✅" if trade['pnl'] > 0 else "❌"
            report += f"""
{pnl_emoji} {trade['symbol']} {trade['side']}
   开仓: {trade['entry_price']:.6f} → 平仓: {trade['exit_price']:.6f}
   盈亏: {trade['pnl']:+.2f}U ({trade['pnl_pct']:+.2f}%)
   原因: {trade['reason']}
   时间: {trade['exit_time'][:19]}
"""
        
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        return report
    
    def export_report(self, output_file: str = None) -> str:
        """导出详细报告"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(CONFIG_DIR, f'report_{self.config_name}_{timestamp}.txt')
        
        status = self.get_status()
        
        report = f"""
═══════════════════════════════════════════════════════════════
                        模拟交易报告
═══════════════════════════════════════════════════════════════

配置名称: {status['config_name']}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

───────────────────────────────────────────────────────────────
                           资金概况
───────────────────────────────────────────────────────────────

初始资金: {status['initial_balance']:.2f}U
当前余额: {status['balance']:.2f}U
总盈亏: {status['total_pnl']:+.2f}U ({status['total_return_pct']:+.2f}%)
持仓价值: {status['total_position_value']:.2f}U

───────────────────────────────────────────────────────────────
                          交易统计
───────────────────────────────────────────────────────────────

总交易笔数: {status['total_trades']}
盈利交易: {status['winning_trades']}笔
亏损交易: {status['losing_trades']}笔
胜率: {status['win_rate']:.1f}%

平均盈利: {status['avg_win']:+.2f}U
平均亏损: {status['avg_loss']:+.2f}U
盈亏比: {status['profit_factor']:.2f}

───────────────────────────────────────────────────────────────
                          风险指标
───────────────────────────────────────────────────────────────

最大回撤: {status['max_drawdown']:.2f}U ({status['max_drawdown_pct']:.2f}%)
当前连续亏损: {status['consecutive_losses']}笔
最大连续亏损: {status['max_consecutive_losses']}笔

───────────────────────────────────────────────────────────────
                         策略参数
───────────────────────────────────────────────────────────────

止损比例: {status['params']['stop_loss_pct']*100:.0f}%
止盈比例: {status['params']['take_profit_pct']*100:.0f}%
买入阈值: {status['params']['buy_threshold']}
卖出阈值: {status['params']['sell_threshold']}
仓位比例: {status['params']['position_size']*100:.0f}%

───────────────────────────────────────────────────────────────
                         交易明细
───────────────────────────────────────────────────────────────

"""
        
        for i, trade in enumerate(self.trades, 1):
            report += f"""
交易 #{i}:
  交易对: {trade['symbol']}
  方向: {trade['side']}
  开仓价: {trade['entry_price']:.6f}
  平仓价: {trade['exit_price']:.6f}
  数量: {trade['amount']:.2f}
  盈亏: {trade['pnl']:+.2f}U ({trade['pnl_pct']:+.2f}%)
  开仓时间: {trade['entry_time']}
  平仓时间: {trade['exit_time']}
  平仓原因: {trade['reason']}
"""
        
        report += """
═══════════════════════════════════════════════════════════════
                           报告结束
═══════════════════════════════════════════════════════════════
"""
        
        # 保存到文件
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"✅ 报告已导出: {output_file}")
        
        return output_file
    
    def reset(self):
        """重置模拟状态"""
        self.balance = self.initial_balance
        self.positions = []
        self.trades = []
        self.equity_curve = [self.initial_balance]
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0
        self.peak_balance = self.initial_balance
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        
        # 删除历史文件
        log_file = os.path.join(CONFIG_DIR, f'simulation_{self.config_name}.json')
        if os.path.exists(log_file):
            os.remove(log_file)
        
        logger.info(f"✅ 模拟状态已重置: {self.config_name}")


# 使用示例
if __name__ == '__main__':
    # 创建模拟交易器
    trader = SimulatedTrader('optimized_DOGEUSDT_30d')
    
    # 模拟开仓
    trader.open_position('DOGEUSDT', 'buy', 0.095, reason='信号得分65')
    
    # 模拟平仓
    trader.close_position(0, 0.100, reason='止盈')
    
    # 显示状态
    print(trader.format_status())
    
    # 导出报告
    trader.export_report()
