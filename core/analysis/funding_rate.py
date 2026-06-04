"""
资金费率分析模块（Funding Rate Analyzer）
监控永续合约资金费率，判断多空力量对比
"""
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
from dataclasses import dataclass

from core.data.binance_data import BinanceDataCollector


@dataclass
class FundingRateInfo:
    """资金费率信息"""
    symbol: str
    current_rate: float       # 当前资金费率
    predicted_rate: float     # 预测资金费率
    avg_rate_8h: float        # 8小时平均费率
    avg_rate_24h: float       # 24小时平均费率
    rate_trend: str           # 费率趋势：rising/falling/stable
    sentiment: str            # 市场情绪：bullish/bearish/neutral
    signal: str               # 交易信号：buy/sell/hold
    confidence: float         # 置信度 0-1
    timestamp: str


class FundingRateAnalyzer:
    """资金费率分析器
    
    资金费率是永续合约特有的机制：
    - 正费率：多头支付空头（市场偏多）
    - 负费率：空头支付多头（市场偏空）
    - 极端费率：可能预示反转
    """
    
    def __init__(self):
        self.collector = BinanceDataCollector()
        
        # 费率阈值
        self.extreme_high = 0.001    # 0.1% 极端高费率
        self.high = 0.0005           # 0.05% 高费率
        self.low = -0.0005           # -0.05% 低费率
        self.extreme_low = -0.001    # -0.1% 极端低费率
        
        logger.info("资金费率分析器初始化完成")
    
    def analyze_funding_rate(self, symbol: str) -> Optional[FundingRateInfo]:
        """分析资金费率
        
        Args:
            symbol: 交易对，如 'DOGEUSDT'
            
        Returns:
            FundingRateInfo 对象或 None
        """
        try:
            # 获取当前资金费率
            funding_rate = self.collector.get_funding_rate(symbol)
            if not funding_rate:
                logger.warning(f"无法获取 {symbol} 的资金费率")
                return None
            
            current_rate = funding_rate.get('lastFundingRate', 0)
            predicted_rate = funding_rate.get('nextFundingRate', current_rate)
            
            # 获取历史资金费率（用于计算平均值和趋势）
            # 注意：Binance公开API可能不提供历史资金费率，这里使用当前费率估算
            avg_rate_8h = current_rate  # 简化处理
            avg_rate_24h = current_rate
            
            # 分析费率趋势
            rate_trend = self._analyze_trend(current_rate, predicted_rate)
            
            # 分析市场情绪
            sentiment = self._analyze_sentiment(current_rate)
            
            # 生成交易信号
            signal, confidence = self._generate_signal(current_rate, sentiment, rate_trend)
            
            result = FundingRateInfo(
                symbol=symbol,
                current_rate=current_rate,
                predicted_rate=predicted_rate,
                avg_rate_8h=avg_rate_8h,
                avg_rate_24h=avg_rate_24h,
                rate_trend=rate_trend,
                sentiment=sentiment,
                signal=signal,
                confidence=confidence,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"{symbol} 资金费率分析: 费率={current_rate:.6f}, "
                       f"情绪={sentiment}, 信号={signal}")
            
            return result
            
        except Exception as e:
            logger.error(f"资金费率分析失败 {symbol}: {e}")
            return None
    
    def _analyze_trend(self, current_rate: float, predicted_rate: float) -> str:
        """分析费率趋势
        
        Args:
            current_rate: 当前费率
            predicted_rate: 预测费率
            
        Returns:
            趋势：rising/falling/stable
        """
        diff = predicted_rate - current_rate
        
        if diff > 0.0001:  # 上升超过0.01%
            return 'rising'
        elif diff < -0.0001:  # 下降超过0.01%
            return 'falling'
        else:
            return 'stable'
    
    def _analyze_sentiment(self, rate: float) -> str:
        """分析市场情绪
        
        Args:
            rate: 资金费率
            
        Returns:
            情绪：bullish/bearish/neutral
        """
        if rate > self.high:
            return 'bullish'  # 多头强势
        elif rate < self.low:
            return 'bearish'  # 空头强势
        else:
            return 'neutral'  # 中性
    
    def _generate_signal(self, rate: float, sentiment: str, trend: str) -> tuple:
        """生成交易信号
        
        策略逻辑：
        - 极端高费率：市场过热，考虑做空（反向思维）
        - 高费率：多头强势，但可能接近顶部
        - 中性费率：观望
        - 低费率：空头强势，但可能接近底部
        - 极端低费率：市场恐慌，考虑做多（反向思维）
        
        Args:
            rate: 资金费率
            sentiment: 市场情绪
            trend: 费率趋势
            
        Returns:
            (信号, 置信度)
        """
        # 极端费率（反向信号）
        if rate > self.extreme_high:
            # 市场极度贪婪，可能是顶部
            confidence = 0.7
            if trend == 'falling':
                confidence = 0.8  # 费率开始下降，更强的卖出信号
            return 'strong_sell', confidence
        
        if rate < self.extreme_low:
            # 市场极度恐慌，可能是底部
            confidence = 0.7
            if trend == 'rising':
                confidence = 0.8  # 费率开始上升，更强的买入信号
            return 'strong_buy', confidence
        
        # 高费率
        if rate > self.high:
            if trend == 'falling':
                # 费率开始下降，卖出信号
                return 'sell', 0.6
            else:
                # 费率还在上升，观望
                return 'hold', 0.5
        
        # 低费率
        if rate < self.low:
            if trend == 'rising':
                # 费率开始上升，买入信号
                return 'buy', 0.6
            else:
                # 费率还在下降，观望
                return 'hold', 0.5
        
        # 中性费率
        return 'hold', 0.5
    
    def get_rate_score(self, rate: float) -> int:
        """获取费率评分（0-100）
        
        用于综合信号生成
        
        Args:
            rate: 资金费率
            
        Returns:
            评分：0-100
            - 0-30：空头强势（可能触底）
            - 30-45：偏空
            - 45-55：中性
            - 55-70：偏多
            - 70-100：多头强势（可能见顶）
        """
        # 将费率映射到0-100评分
        # 假设费率范围：-0.1% 到 0.1%
        normalized = (rate + 0.001) / 0.002  # 归一化到 0-1
        normalized = max(0, min(1, normalized))  # 限制在 0-1
        score = int(normalized * 100)
        
        return score


# 使用示例
if __name__ == '__main__':
    analyzer = FundingRateAnalyzer()
    
    # 分析DOGE资金费率
    result = analyzer.analyze_funding_rate('DOGEUSDT')
    if result:
        print(f"\n📊 DOGE 资金费率分析")
        print(f"   当前费率: {result.current_rate:.6f} ({result.current_rate*100:.4f}%)")
        print(f"   预测费率: {result.predicted_rate:.6f}")
        print(f"   费率趋势: {result.rate_trend}")
        print(f"   市场情绪: {result.sentiment}")
        print(f"   交易信号: {result.signal}")
        print(f"   置信度: {result.confidence:.0%}")
        
        # 获取评分
        score = analyzer.get_rate_score(result.current_rate)
        print(f"   费率评分: {score}/100")
