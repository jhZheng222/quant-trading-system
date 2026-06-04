"""
策略参数优化器
使用历史数据进行网格搜索，找到最优参数组合
"""

import itertools
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger

from core.backtest.engine import BacktestEngine


@dataclass
class OptimizationResult:
    """优化结果"""
    params: Dict[str, Any]
    total_return_pct: float
    win_rate: float
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    total_trades: int


class StrategyOptimizer:
    """策略参数优化器
    
    使用网格搜索优化策略参数
    """
    
    def __init__(self, symbol: str = 'DOGEUSDT', days: int = 30):
        """
        Args:
            symbol: 交易对
            days: 回测天数
        """
        self.symbol = symbol
        self.days = days
        self.results: List[OptimizationResult] = []
        
        logger.info(f"📊 优化器初始化: {symbol}, {days}天")
    
    def define_param_grid(self) -> Dict[str, List]:
        """定义参数搜索范围"""
        return {
            'stop_loss_pct': [0.02, 0.03, 0.05, 0.08],      # 止损比例
            'take_profit_pct': [0.05, 0.10, 0.15, 0.20],    # 止盈比例
            'buy_threshold': [50, 55, 60, 65],               # 买入阈值
            'sell_threshold': [35, 40, 45, 50],              # 卖出阈值
            'position_size': [0.2, 0.3, 0.4],               # 仓位比例
        }
    
    def run_optimization(self, param_grid: Dict[str, List] = None) -> List[OptimizationResult]:
        """运行参数优化
        
        Args:
            param_grid: 参数网格，如果为None则使用默认值
            
        Returns:
            优化结果列表
        """
        if param_grid is None:
            param_grid = self.define_param_grid()
        
        # 生成所有参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))
        
        total = len(combinations)
        logger.info(f"🔍 开始优化: {total}种参数组合")
        
        self.results = []
        
        for i, values in enumerate(combinations):
            # 构建参数字典
            params = dict(zip(param_names, values))
            
            # 显示进度
            if (i + 1) % 10 == 0 or i == 0:
                logger.info(f"   进度: {i+1}/{total}")
            
            # 运行回测
            try:
                result = self._run_single_backtest(params)
                if result:
                    self.results.append(result)
            except Exception as e:
                logger.warning(f"   回测失败: {e}")
        
        # 按收益排序
        self.results.sort(key=lambda x: x.total_return_pct, reverse=True)
        
        logger.info(f"✅ 优化完成: {len(self.results)}个有效结果")
        
        return self.results
    
    def _run_single_backtest(self, params: Dict[str, Any]) -> Optional[OptimizationResult]:
        """运行单次回测"""
        # 创建回测引擎
        engine = BacktestEngine(initial_balance=1000.0)
        
        # 更新参数
        engine.stop_loss_pct = params['stop_loss_pct']
        engine.take_profit_pct = params['take_profit_pct']
        engine.buy_threshold = params['buy_threshold']
        engine.sell_threshold = params['sell_threshold']
        engine.position_size = params['position_size']
        
        # 运行回测
        result = engine.run_backtest(self.symbol, self.days)
        
        if result and result.total_trades >= 3:  # 至少3笔交易才有意义
            return OptimizationResult(
                params=params,
                total_return_pct=result.total_return_pct,
                win_rate=result.win_rate,
                max_drawdown_pct=result.max_drawdown_pct,
                sharpe_ratio=result.sharpe_ratio,
                profit_factor=result.profit_factor,
                total_trades=result.total_trades
            )
        
        return None
    
    def get_top_results(self, n: int = 10, sort_by: str = 'total_return_pct') -> List[OptimizationResult]:
        """获取前N个最优结果
        
        Args:
            n: 返回数量
            sort_by: 排序字段
            
        Returns:
            最优结果列表
        """
        if not self.results:
            logger.warning("没有优化结果")
            return []
        
        # 排序
        if sort_by == 'total_return_pct':
            sorted_results = sorted(self.results, key=lambda x: x.total_return_pct, reverse=True)
        elif sort_by == 'sharpe_ratio':
            sorted_results = sorted(self.results, key=lambda x: x.sharpe_ratio, reverse=True)
        elif sort_by == 'win_rate':
            sorted_results = sorted(self.results, key=lambda x: x.win_rate, reverse=True)
        elif sort_by == 'max_drawdown_pct':
            sorted_results = sorted(self.results, key=lambda x: x.max_drawdown_pct)
        else:
            sorted_results = self.results
        
        return sorted_results[:n]
    
    def get_best_params(self, sort_by: str = 'total_return_pct') -> Dict[str, Any]:
        """获取最优参数
        
        Args:
            sort_by: 排序字段
            
        Returns:
            最优参数字典
        """
        top_results = self.get_top_results(1, sort_by)
        
        if top_results:
            return top_results[0].params
        
        return {}
    
    def format_report(self, top_n: int = 10) -> str:
        """格式化优化报告"""
        if not self.results:
            return "❌ 没有优化结果"
        
        top_results = self.get_top_results(top_n)
        
        report = f"""
📊 策略参数优化报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
交易对: {self.symbol}
回测天数: {self.days}
参数组合: {len(self.results)}种
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 前{top_n}个最优参数组合:
"""
        
        for i, result in enumerate(top_results, 1):
            report += f"""
#{i} ─────────────────────────────────────
📈 收益: {result.total_return_pct:+.2f}% | 胜率: {result.win_rate:.1f}% | 回撤: {result.max_drawdown_pct:.2f}%
📊 夏普: {result.sharpe_ratio:.2f} | 盈亏比: {result.profit_factor:.2f} | 交易: {result.total_trades}笔
⚙️  参数:
   止损={result.params['stop_loss_pct']*100:.0f}%
   止盈={result.params['take_profit_pct']*100:.0f}%
   买入阈值={result.params['buy_threshold']}
   卖出阈值={result.params['sell_threshold']}
   仓位={result.params['position_size']*100:.0f}%
"""
        
        # 最优参数总结
        best = top_results[0]
        report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 推荐参数（收益最高）:
   止损比例: {best.params['stop_loss_pct']*100:.0f}%
   止盈比例: {best.params['take_profit_pct']*100:.0f}%
   买入阈值: {best.params['buy_threshold']}
   卖出阈值: {best.params['sell_threshold']}
   仓位比例: {best.params['position_size']*100:.0f}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        return report


class SmartOptimizer(StrategyOptimizer):
    """智能优化器
    
    支持多种优化策略
    """
    
    def optimize_for_risk_adjusted(self) -> Dict[str, Any]:
        """优化风险调整后收益（夏普比率）"""
        logger.info("📊 优化目标: 夏普比率")
        self.run_optimization()
        return self.get_best_params('sharpe_ratio')
    
    def optimize_for_win_rate(self) -> Dict[str, Any]:
        """优化胜率"""
        logger.info("📊 优化目标: 胜率")
        self.run_optimization()
        return self.get_best_params('win_rate')
    
    def optimize_for_low_drawdown(self) -> Dict[str, Any]:
        """优化低回撤"""
        logger.info("📊 优化目标: 低回撤")
        self.run_optimization()
        return self.get_best_params('max_drawdown_pct')
    
    def multi_objective_optimization(self) -> Dict[str, Any]:
        """多目标优化
        
        综合考虑收益、胜率、回撤
        """
        logger.info("📊 多目标优化")
        self.run_optimization()
        
        if not self.results:
            return {}
        
        # 计算综合得分
        scored_results = []
        for result in self.results:
            # 归一化各指标
            return_score = (result.total_return_pct + 100) / 200  # 假设范围-100%到+100%
            win_score = result.win_rate / 100
            drawdown_score = 1 - (result.max_drawdown_pct / 100)  # 回撤越小越好
            sharpe_score = min(max(result.sharpe_ratio, 0), 3) / 3  # 夏普0-3
            
            # 综合得分（权重可调）
            total_score = (
                return_score * 0.3 +
                win_score * 0.2 +
                drawdown_score * 0.3 +
                sharpe_score * 0.2
            )
            
            scored_results.append((total_score, result))
        
        # 排序
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        if scored_results:
            best_result = scored_results[0][1]
            logger.info(f"✅ 最优综合得分: {scored_results[0][0]:.3f}")
            return best_result.params
        
        return {}


# 使用示例
if __name__ == '__main__':
    # 创建优化器
    optimizer = StrategyOptimizer('DOGEUSDT', days=30)
    
    # 定义参数网格
    param_grid = {
        'stop_loss_pct': [0.02, 0.03, 0.05],
        'take_profit_pct': [0.08, 0.10, 0.15],
        'buy_threshold': [55, 60, 65],
        'sell_threshold': [40, 45],
        'position_size': [0.2, 0.3],
    }
    
    # 运行优化
    results = optimizer.run_optimization(param_grid)
    
    # 打印报告
    print(optimizer.format_report(5))
