"""
资金费率分析模块（简化版）
使用估算方式，不依赖外部API
"""
from datetime import datetime
from typing import Dict, Optional
from loguru import logger
from dataclasses import dataclass


@dataclass
class FundingRateInfo:
    """资金费率信息"""
    symbol: str
    current_rate: float       # 当前资金费率
    sentiment: str            # 市场情绪：bullish/bearish/neutral
    signal: str               # 交易信号：buy/sell/hold
    confidence: float         # 置信度 0-1
    timestamp: str


class FundingRateAnalyzer:
    """资金费率分析器（简化版）
    
    基于价格变化估算市场情绪
    """
    
    def __init__(self):
        logger.info("资金费率分析器初始化完成（简化版）")
    
    def analyze_from_price(self, symbol: str, current_price: float, 
                          price_change_24h: float) -> FundingRateInfo:
        """基于价格变化分析市场情绪
        
        Args:
            symbol: 交易对
            current_price: 当前价格
            price_change_24h: 24小时涨跌幅（百分比）
            
        Returns:
            FundingRateInfo 对象
        """
        # 基于涨跌幅估算市场情绪
        if price_change_24h > 5:
            sentiment = 'bullish'
            signal = 'sell'  # 涨太多，考虑卖出
            confidence = 0.6
        elif price_change_24h > 2:
            sentiment = 'bullish'
            signal = 'hold'
            confidence = 0.5
        elif price_change_24h < -5:
            sentiment = 'bearish'
            signal = 'buy'  # 跌太多，考虑买入
            confidence = 0.6
        elif price_change_24h < -2:
            sentiment = 'bearish'
            signal = 'hold'
            confidence = 0.5
        else:
            sentiment = 'neutral'
            signal = 'hold'
            confidence = 0.5
        
        # 估算资金费率（简化）
        # 正涨跌 -> 正费率，跌涨跌 -> 负费率
        estimated_rate = price_change_24h / 1000  # 简化估算
        
        result = FundingRateInfo(
            symbol=symbol,
            current_rate=estimated_rate,
            sentiment=sentiment,
            signal=signal,
            confidence=confidence,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"{symbol} 市场情绪分析: 涨跌={price_change_24h:.2f}%, "
                   f"情绪={sentiment}, 信号={signal}")
        
        return result
    
    def get_rate_score(self, price_change_24h: float) -> int:
        """获取情绪评分（0-100）
        
        用于综合信号生成
        """
        # 将涨跌幅映射到0-100评分
        # 假设涨跌幅范围：-10% 到 10%
        normalized = (price_change_24h + 10) / 20  # 归一化到 0-1
        normalized = max(0, min(1, normalized))  # 限制在 0-1
        score = int(normalized * 100)
        
        return score


# 测试
if __name__ == '__main__':
    analyzer = FundingRateAnalyzer()
    
    # 测试不同涨跌幅
    test_cases = [
        (10.0, "大涨"),
        (5.0, "上涨"),
        (0.0, "横盘"),
        (-5.0, "下跌"),
        (-10.0, "大跌"),
    ]
    
    for change, desc in test_cases:
        result = analyzer.analyze_from_price('DOGEUSDT', 0.1, change)
        score = analyzer.get_rate_score(change)
        print(f"{desc}: 涨跌={change}%, 情绪={result.sentiment}, 信号={result.signal}, 评分={score}")
