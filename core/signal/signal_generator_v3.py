"""
优化版信号生成器
集成趋势过滤，提高盈亏比
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from ..analysis.cost_basis import CostBasisAnalyzer
from ..analysis.funding_rate_simple import FundingRateAnalyzer
from ..analysis.orderbook import OrderbookAnalyzer
from ..analysis.sentiment import SentimentAnalyzer
from ..analysis.liquidation import LiquidationAnalyzer
from ..analysis.trend_filter import TrendFilter
from ..storage.sqlite_storage import SQLiteStorage


class SignalGeneratorV3:
    """优化版信号生成器 - 集成趋势过滤"""
    
    def __init__(self, db_manager: SQLiteStorage = None):
        """初始化信号生成器"""
        self.db_manager = db_manager or SQLiteStorage()
        
        # 初始化各模块
        self.cost_analyzer = CostBasisAnalyzer()
        self.funding_analyzer = FundingRateAnalyzer()
        self.orderbook_analyzer = OrderbookAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.liquidation_analyzer = LiquidationAnalyzer()
        self.trend_filter = TrendFilter()
        
        # 优化后的权重分配（更注重趋势和成本）
        self.weights = {
            'trend': 0.35,      # 趋势方向（最重要）
            'cost': 0.25,       # 成本分析
            'sentiment': 0.20,  # 市场情绪
            'orderbook': 0.10,  # 订单簿
            'liquidation': 0.10 # 清算地图
        }
        
        # 优化后的信号阈值
        self.buy_threshold = 65    # 买入阈值（提高）
        self.sell_threshold = 35   # 卖出阈值（降低）
        
        # 优化后的盈亏比设置
        self.stop_loss_pct = 1.5   # 止损比例（降低）
        self.take_profit_pct = 15  # 止盈比例（提高）
        self.leverage = 10         # 杠杆倍数
        self.position_ratio = 0.2  # 仓位比例
        
        print("📊 优化版信号生成器 v3 初始化完成")
    
    def analyze_trend_score(self, klines: list) -> Tuple[float, str]:
        """
        分析趋势得分
        
        Args:
            klines: K线数据
            
        Returns:
            (得分, 趋势方向)
        """
        trend_result = self.trend_filter.analyze_trend(klines)
        
        if not trend_result['should_trade']:
            return 50, 'sideways'  # 震荡市场，中性分数
        
        if trend_result['trend'] == 'up':
            # 上涨趋势，得分70-95
            score = 70 + (trend_result['confidence'] * 25)
            return min(95, score), 'up'
        elif trend_result['trend'] == 'down':
            # 下跌趋势，得分5-30
            score = 30 - (trend_result['confidence'] * 25)
            return max(5, score), 'down'
        else:
            return 50, 'sideways'
    
    def generate_signal(self, symbol: str) -> Dict[str, Any]:
        """
        生成交易信号
        
        Args:
            symbol: 交易对
            
        Returns:
            信号详情
        """
        # 从数据库获取最新数据
        klines = self.db_manager.get_klines(symbol, '1h', 100)
        
        if not klines:
            return {
                'symbol': symbol,
                'signal': 'hold',
                'score': 50,
                'confidence': 0,
                'reason': '无数据'
            }
        
        # 计算各模块得分
        scores = {}
        
        # 1. 趋势分析（最重要）
        trend_score, trend_direction = self.analyze_trend_score(klines)
        scores['trend'] = trend_score
        
        # 2. 成本分析
        prices = [k[4] for k in klines]
        volumes = [k[5] for k in klines]
        current_price = prices[-1] if prices else 0
        cost_signal = self.cost_analyzer.get_trading_signal(symbol, current_price)
        # 将信号转换为分数
        signal_to_score = {
            'strong_buy': 85,
            'buy': 65,
            'hold': 50,
            'sell': 35,
            'strong_sell': 15
        }
        scores['cost'] = signal_to_score.get(cost_signal.get('signal', 'hold'), 50)
        
        # 3. 资金费率（简化处理）
        funding_rate = 0.01  # 默认值
        scores['funding'] = 50  # 中性
        
        # 4. 订单簿分析（使用价格作为代理）
        scores['orderbook'] = self._analyze_orderbook_proxy(prices)
        
        # 5. 市场情绪
        scores['sentiment'] = self._analyze_sentiment_proxy(prices, volumes)
        
        # 6. 清算地图
        scores['liquidation'] = self._analyze_liquidation_proxy(prices)
        
        # 计算综合得分
        final_score = (
            scores['trend'] * self.weights['trend'] +
            scores['cost'] * self.weights['cost'] +
            scores['sentiment'] * self.weights['sentiment'] +
            scores['orderbook'] * self.weights['orderbook'] +
            scores['liquidation'] * self.weights['liquidation']
        )
        
        # 生成信号（必须趋势一致）
        signal = self._generate_signal_with_trend(final_score, trend_direction)
        
        return {
            'symbol': symbol,
            'signal': signal,
            'score': round(final_score, 2),
            'confidence': self._calculate_confidence(scores),
            'trend': trend_direction,
            'details': scores,
            'parameters': {
                'stop_loss': self.stop_loss_pct,
                'take_profit': self.take_profit_pct,
                'leverage': self.leverage,
                'position_ratio': self.position_ratio
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_signal_with_trend(self, score: float, trend: str) -> str:
        """
        结合趋势生成信号
        
        Args:
            score: 综合得分
            trend: 趋势方向
            
        Returns:
            信号: 'buy', 'sell', 'hold'
        """
        # 趋势必须一致才能交易
        if trend == 'up' and score >= self.buy_threshold:
            return 'buy'
        elif trend == 'down' and score <= self.sell_threshold:
            return 'sell'
        else:
            return 'hold'
    
    def _analyze_orderbook_proxy(self, prices: list) -> float:
        """订单簿代理分析"""
        if len(prices) < 20:
            return 50
        
        # 使用价格动量作为订单簿代理
        recent_prices = prices[-20:]
        momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100
        
        if momentum > 2:
            return 65  # 买方力量强
        elif momentum < -2:
            return 35  # 卖方力量强
        else:
            return 50
    
    def _analyze_sentiment_proxy(self, prices: list, volumes: list) -> float:
        """市场情绪代理分析"""
        if len(prices) < 20 or len(volumes) < 20:
            return 50
        
        # 价格和成交量的关系
        recent_prices = prices[-20:]
        recent_volumes = volumes[-20:]
        
        price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100
        volume_change = (recent_volumes[-1] - np.mean(recent_volumes[:-1])) / np.mean(recent_volumes[:-1]) * 100
        
        # 放量上涨 = 看涨，放量下跌 = 看跌
        if price_change > 0 and volume_change > 20:
            return 70
        elif price_change < 0 and volume_change > 20:
            return 30
        else:
            return 50
    
    def _analyze_liquidation_proxy(self, prices: list) -> float:
        """清算地图代理分析"""
        if len(prices) < 20:
            return 50
        
        # 使用价格波动性作为清算风险代理
        recent_prices = prices[-20:]
        volatility = np.std(recent_prices) / np.mean(recent_prices) * 100
        
        if volatility > 5:
            return 40  # 高波动，清算风险高
        elif volatility < 2:
            return 60  # 低波动，清算风险低
        else:
            return 50
    
    def _calculate_confidence(self, scores: Dict[str, float]) -> float:
        """计算置信度"""
        # 各模块得分的一致性
        values = list(scores.values())
        std = np.std(values)
        
        # 标准差越小，一致性越高
        if std < 10:
            return 0.8
        elif std < 20:
            return 0.6
        else:
            return 0.4
    
    def update_parameters(self, params: Dict[str, Any]):
        """
        更新参数
        
        Args:
            params: 参数字典
        """
        if 'stop_loss' in params:
            self.stop_loss_pct = params['stop_loss']
        if 'take_profit' in params:
            self.take_profit_pct = params['take_profit']
        if 'leverage' in params:
            self.leverage = params['leverage']
        if 'position_ratio' in params:
            self.position_ratio = params['position_ratio']
        if 'buy_threshold' in params:
            self.buy_threshold = params['buy_threshold']
        if 'sell_threshold' in params:
            self.sell_threshold = params['sell_threshold']
        
        print(f"📊 参数已更新:")
        print(f"   止损: {self.stop_loss_pct}%")
        print(f"   止盈: {self.take_profit_pct}%")
        print(f"   杠杆: {self.leverage}x")
        print(f"   仓位: {self.position_ratio*100}%")
        print(f"   买入阈值: {self.buy_threshold}")
        print(f"   卖出阈值: {self.sell_threshold}")


# 创建全局实例
signal_generator_v3 = SignalGeneratorV3()