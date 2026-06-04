"""
参数优化器（Parameter Optimizer）
优化策略参数，提高收益
"""
import itertools
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass

from core.backtest.engine import BacktestEngine, BacktestResult


@dataclass
class OptimizationResult:
    """优化结果"""
    best_params: Dict
    best_return_pct: float
    best_win_rate: float
    best_sharpe: float
    best_max_drawdown_pct: float
    all_results: List[Dict]


class ParameterOptimizer:
    """参数优化器
    
    优化策略参数，提高收益
    """
    
    def __init__(self, initial_balance: float = 1000.0):
        self.initial_balance = initial_balance
        
        logger.info("参数优化器初始化完成")
    
    def optimize(self, symbol: str, days: int = 7) -> Optional[OptimizationResult]:
        """优化参数
        
        Args:
            symbol: 交易对
            days: 回测天数
            
        Returns:
            OptimizationResult 对象
        """
        try:
            # 参数范围
            param_grid = {
                'leverage': [10, 20, 30],
                'position_size': [0.2, 0.3, 0.4],
                'stop_loss_pct': [0.02, 0.03, 0.05],
                'take_profit_pct': [0.06, 0.10, 0.15],
                'buy_threshold': [50, 55, 60],
                'sell_threshold': [40, 45, 50],
            }
            
            # 生成参数组合
            param_names = list(param_grid.keys())
            param_values = list(param_grid.values())
            param_combinations = list(itertools.product(*param_values))
            
            logger.info(f"开始优化 {symbol}，参数组合数: {len(param_combinations)}")
            
            all_results = []
            best_return = -float('inf')
            best_params = None
            best_result = None
            
            # 测试每种参数组合
            for i, combo in enumerate(param_combinations):
                params = dict(zip(param_names, combo))
                
                # 运行回测
                engine = BacktestEngine(initial_balance=self.initial_balance)
                engine.leverage = params['leverage']
                engine.position_size = params['position_size']
                engine.stop_loss_pct = params['stop_loss_pct']
                engine.take_profit_pct = params['take_profit_pct']
                engine.buy_threshold = params['buy_threshold']
                engine.sell_threshold = params['sell_threshold']
                
                result = engine.run_backtest(symbol, days)
                
                if result:
                    # 记录结果
                    result_dict = {
                        'params': params,
                        'return_pct': result.total_return_pct,
                        'win_rate': result.win_rate,
                        'sharpe': result.sharpe_ratio,
                        'max_drawdown_pct': result.max_drawdown_pct,
                        'total_trades': result.total_trades,
                    }
                    all_results.append(result_dict)
                    
                    # 更新最佳参数
                    # 综合考虑收益、胜率和回撤
                    score = self._calculate_score(result)
                    
                    if score > best_return:
                        best_return = score
                        best_params = params
                        best_result = result
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"进度: {i+1}/{len(param_combinations)}")
            
            if not best_params:
                logger.warning("未找到有效参数")
                return None
            
            # 按综合评分排序
            all_results.sort(key=lambda x: self._calculate_score_from_dict(x), reverse=True)
            
            optimization_result = OptimizationResult(
                best_params=best_params,
                best_return_pct=best_result.total_return_pct,
                best_win_rate=best_result.win_rate,
                best_sharpe=best_result.sharpe_ratio,
                best_max_drawdown_pct=best_result.max_drawdown_pct,
                all_results=all_results[:10]  # 只保留前10个结果
            )
            
            logger.info(f"优化完成: 最佳收益={best_result.total_return_pct:.2f}%, "
                       f"胜率={best_result.win_rate:.1f}%")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"优化失败: {e}")
            return None
    
    def _calculate_score(self, result: BacktestResult) -> float:
        """计算综合评分
        
        综合考虑：
        1. 收益率（权重40%）
        2. 胜率（权重20%）
        3. 夏普比率（权重20%）
        4. 最大回撤（权重20%，负向）
        """
        # 收益率评分（归一化到0-100）
        return_score = min(100, max(-100, result.total_return_pct)) / 2 + 50
        
        # 胜率评分
        win_rate_score = result.win_rate
        
        # 夏普比率评分
        sharpe_score = min(100, max(-100, result.sharpe_ratio * 10)) / 2 + 50
        
        # 最大回撤评分（回撤越小越好）
        drawdown_score = max(0, 100 - result.max_drawdown_pct * 2)
        
        # 综合评分
        score = (
            return_score * 0.4 +
            win_rate_score * 0.2 +
            sharpe_score * 0.2 +
            drawdown_score * 0.2
        )
        
        return score
    
    def _calculate_score_from_dict(self, result_dict: Dict) -> float:
        """从字典计算综合评分"""
        return_score = min(100, max(-100, result_dict['return_pct'])) / 2 + 50
        win_rate_score = result_dict['win_rate']
        sharpe_score = min(100, max(-100, result_dict['sharpe'] * 10)) / 2 + 50
        drawdown_score = max(0, 100 - result_dict['max_drawdown_pct'] * 2)
        
        score = (
            return_score * 0.4 +
            win_rate_score * 0.2 +
            sharpe_score * 0.2 +
            drawdown_score * 0.2
        )
        
        return score
    
    def format_report(self, result: OptimizationResult) -> str:
        """格式化优化报告"""
        report = f"""
📊 参数优化报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 最佳参数:
   杠杆倍数: {result.best_params['leverage']}x
   仓位比例: {result.best_params['position_size']*100:.0f}%
   止损比例: {result.best_params['stop_loss_pct']*100:.0f}%
   止盈比例: {result.best_params['take_profit_pct']*100:.0f}%
   买入阈值: {result.best_params['buy_threshold']}
   卖出阈值: {result.best_params['sell_threshold']}

📈 最佳结果:
   总收益: {result.best_return_pct:+.2f}%
   胜率: {result.best_win_rate:.1f}%
   夏普比率: {result.best_sharpe:.2f}
   最大回撤: {result.best_max_drawdown_pct:.2f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Top 5 参数组合:
"""
        for i, res in enumerate(result.all_results[:5]):
            report += f"\n   #{i+1}: 收益={res['return_pct']:+.2f}%, 胜率={res['win_rate']:.1f}%, 回撤={res['max_drawdown_pct']:.2f}%"
            report += f"\n       参数: 杠杆={res['params']['leverage']}x, 仓位={res['params']['position_size']*100:.0f}%, 止损={res['params']['stop_loss_pct']*100:.0f}%, 止盈={res['params']['take_profit_pct']*100:.0f}%"
        
        report += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        return report


# 测试
if __name__ == '__main__':
    optimizer = ParameterOptimizer(initial_balance=1000.0)
    
    # 优化DOGE参数（7天数据）
    result = optimizer.optimize('DOGEUSDT', days=7)
    if result:
        report = optimizer.format_report(result)
        print(report)
