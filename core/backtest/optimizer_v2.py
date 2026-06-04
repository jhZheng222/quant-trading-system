"""
优化版参数优化器
使用网格搜索和贝叶斯优化
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from itertools import product
import json

from ..storage.sqlite_storage import SQLiteStorage
from ..backtest.engine_v2 import BacktestEngineV2


class ParameterOptimizerV2:
    """优化版参数优化器"""
    
    def __init__(self, db_manager: SQLiteStorage = None):
        """初始化优化器"""
        self.db_manager = db_manager or SQLiteStorage()
        self.backtest_engine = BacktestEngineV2(self.db_manager)
        
        # 参数搜索空间
        self.param_grid = {
            'leverage': [5, 10, 15, 20],
            'position_ratio': [0.1, 0.15, 0.2, 0.25],
            'stop_loss': [1, 1.5, 2, 2.5],
            'take_profit': [10, 12, 15, 18, 20],
            'buy_threshold': [60, 65, 70, 75],
            'sell_threshold': [30, 35, 40, 45]
        }
        
        # 优化结果
        self.results = []
        self.best_params = None
        self.best_score = -float('inf')
        
        print("📊 优化版参数优化器初始化完成")
    
    def grid_search(self, symbol: str, days: int = 30, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        网格搜索
        
        Args:
            symbol: 交易对
            days: 回测天数
            top_n: 返回前N个最佳参数
            
        Returns:
            排序后的参数组合
        """
        print(f"🔍 开始网格搜索...")
        print(f"   交易对: {symbol}")
        print(f"   回测天数: {days}")
        
        # 生成所有参数组合
        param_keys = list(self.param_grid.keys())
        param_values = list(self.param_grid.values())
        
        combinations = list(product(*param_values))
        total = len(combinations)
        
        print(f"   参数组合数: {total}")
        
        # 测试每种组合
        results = []
        
        for i, combo in enumerate(combinations):
            params = dict(zip(param_keys, combo))
            
            # 运行回测
            backtest_result = self._run_backtest_with_params(symbol, days, params)
            
            if backtest_result:
                # 计算综合评分
                score = self._calculate_score(backtest_result)
                
                results.append({
                    'params': params,
                    'score': score,
                    'stats': backtest_result['statistics']
                })
            
            # 进度显示
            if (i + 1) % 10 == 0:
                print(f"   进度: {i+1}/{total}")
        
        # 排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # 保存结果
        self.results = results[:top_n]
        
        if results:
            self.best_params = results[0]['params']
            self.best_score = results[0]['score']
        
        return results[:top_n]
    
    def random_search(self, symbol: str, days: int = 30, n_iter: int = 100) -> Dict[str, Any]:
        """
        随机搜索
        
        Args:
            symbol: 交易对
            days: 回测天数
            n_iter: 迭代次数
            
        Returns:
            最佳参数
        """
        print(f"🔍 开始随机搜索...")
        print(f"   迭代次数: {n_iter}")
        
        best_result = None
        best_score = -float('inf')
        
        for i in range(n_iter):
            # 随机生成参数
            params = {
                'leverage': np.random.choice(self.param_grid['leverage']),
                'position_ratio': np.random.choice(self.param_grid['position_ratio']),
                'stop_loss': np.random.choice(self.param_grid['stop_loss']),
                'take_profit': np.random.choice(self.param_grid['take_profit']),
                'buy_threshold': np.random.choice(self.param_grid['buy_threshold']),
                'sell_threshold': np.random.choice(self.param_grid['sell_threshold'])
            }
            
            # 运行回测
            backtest_result = self._run_backtest_with_params(symbol, days, params)
            
            if backtest_result:
                score = self._calculate_score(backtest_result)
                
                if score > best_score:
                    best_score = score
                    best_result = {
                        'params': params,
                        'score': score,
                        'stats': backtest_result['statistics']
                    }
            
            if (i + 1) % 10 == 0:
                print(f"   进度: {i+1}/{n_iter}")
        
        self.best_params = best_result['params']
        self.best_score = best_result['score']
        
        return best_result
    
    def _run_backtest_with_params(self, symbol: str, days: int, params: Dict) -> Dict[str, Any]:
        """使用指定参数运行回测"""
        # 更新参数
        self.backtest_engine.update_parameters(params)
        
        # 设置时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 运行回测
        return self.backtest_engine.run_backtest(symbol, start_date, end_date)
    
    def _calculate_score(self, backtest_result: Dict) -> float:
        """
        计算综合评分
        
        评分公式：
        - 收益率权重：40%
        - 胜率权重：20%
        - 盈亏比权重：20%
        - 最大回撤惩罚：20%
        """
        stats = backtest_result['statistics']
        
        if not stats:
            return -100
        
        # 收益率得分
        total_return = stats.get('total_return', 0)
        return_score = total_return * 0.4
        
        # 胜率得分
        win_rate = stats.get('win_rate', 0)
        win_score = win_rate * 0.2
        
        # 盈亏比得分
        profit_factor = stats.get('profit_factor', 0)
        pf_score = min(profit_factor * 10, 100) * 0.2
        
        # 最大回撤惩罚
        max_drawdown = stats.get('max_drawdown', 100)
        dd_penalty = max_drawdown * 0.2
        
        # 综合得分
        score = return_score + win_score + pf_score - dd_penalty
        
        return round(score, 2)
    
    def get_optimization_report(self) -> str:
        """生成优化报告"""
        if not self.results:
            return "无优化结果"
        
        report = []
        report.append("=" * 60)
        report.append("📊 参数优化报告")
        report.append("=" * 60)
        report.append("")
        
        # 最佳参数
        report.append("🏆 最佳参数组合:")
        report.append("-" * 40)
        for key, value in self.best_params.items():
            report.append(f"   {key}: {value}")
        report.append("")
        
        # 最佳回测结果
        report.append("📈 最佳回测结果:")
        report.append("-" * 40)
        best = self.results[0]
        stats = best['stats']
        report.append(f"   综合评分: {best['score']}")
        report.append(f"   总收益率: {stats.get('total_return', 0)}%")
        report.append(f"   胜率: {stats.get('win_rate', 0)}%")
        report.append(f"   盈亏比: {stats.get('profit_factor', 0)}")
        report.append(f"   最大回撤: {stats.get('max_drawdown', 0)}%")
        report.append(f"   夏普比率: {stats.get('sharpe_ratio', 0)}")
        report.append("")
        
        # Top 5 参数组合
        report.append("📊 Top 5 参数组合:")
        report.append("-" * 40)
        for i, result in enumerate(self.results[:5]):
            report.append(f"   #{i+1}: 得分={result['score']}, 收益={result['stats'].get('total_return', 0)}%, 胜率={result['stats'].get('win_rate', 0)}%")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def save_results(self, filepath: str = None):
        """保存优化结果"""
        if not filepath:
            filepath = f"~/quant-trading-system/optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = Path(filepath).expanduser()
        
        data = {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'results': self.results,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"💾 优化结果已保存到: {filepath}")