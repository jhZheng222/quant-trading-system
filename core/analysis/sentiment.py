"""
散户情绪分析模块（Sentiment Analyzer）
监控散户情绪，作为反向指标
"""
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
from dataclasses import dataclass

from core.data.binance_data import BinanceDataCollector


@dataclass
class SentimentInfo:
    """情绪分析结果"""
    symbol: str
    fear_greed_index: int     # 恐惧贪婪指数 0-100
    sentiment: str            # extreme_fear/fear/neutral/greed/extreme_greed
    signal: str               # 交易信号（反向）
    confidence: float         # 置信度 0-1
    indicators: Dict          # 各指标详情
    timestamp: str


class SentimentAnalyzer:
    """散户情绪分析器
    
    核心理念：
    - 散户极度恐慌 = 底部信号（反向买入）
    - 散户极度贪婪 = 顶部信号（反向卖出）
    
    数据来源：
    - 价格波动率
    - 成交量变化
    - 价格位置（相对高低）
    """
    
    def __init__(self):
        self.collector = BinanceDataCollector()
        
        # 情绪阈值
        self.extreme_fear = 20      # 极度恐慌
        self.fear = 40              # 恐慌
        self.neutral_low = 45       # 中性下限
        self.neutral_high = 55      # 中性上限
        self.greed = 60             # 贪婪
        self.extreme_greed = 80     # 极度贪婪
        
        logger.info("散户情绪分析器初始化完成")
    
    def analyze_sentiment(self, symbol: str) -> Optional[SentimentInfo]:
        """分析散户情绪
        
        Args:
            symbol: 交易对，如 'DOGEUSDT'
            
        Returns:
            SentimentInfo 对象或 None
        """
        try:
            # 获取K线数据
            klines = self.collector.collect_klines(symbol, '1h', 168)  # 7天
            if not klines or len(klines) < 24:
                logger.warning(f"无法获取足够的K线数据")
                return None
            
            # 计算各指标
            volatility_score = self._calculate_volatility(klines)
            volume_score = self._calculate_volume_trend(klines)
            price_position_score = self._calculate_price_position(klines)
            momentum_score = self._calculate_momentum(klines)
            
            # 计算综合恐惧贪婪指数
            fear_greed_index = int(
                volatility_score * 0.25 +
                volume_score * 0.25 +
                price_position_score * 0.30 +
                momentum_score * 0.20
            )
            
            # 限制在 0-100
            fear_greed_index = max(0, min(100, fear_greed_index))
            
            # 判断情绪
            sentiment = self._index_to_sentiment(fear_greed_index)
            
            # 生成信号（反向）
            signal, confidence = self._generate_signal(fear_greed_index, sentiment)
            
            # 各指标详情
            indicators = {
                'volatility': volatility_score,
                'volume_trend': volume_score,
                'price_position': price_position_score,
                'momentum': momentum_score,
            }
            
            result = SentimentInfo(
                symbol=symbol,
                fear_greed_index=fear_greed_index,
                sentiment=sentiment,
                signal=signal,
                confidence=confidence,
                indicators=indicators,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"{symbol} 情绪分析: 恐惧贪婪指数={fear_greed_index}, "
                       f"情绪={sentiment}, 信号={signal}")
            
            return result
            
        except Exception as e:
            logger.error(f"情绪分析失败 {symbol}: {e}")
            return None
    
    def _calculate_volatility(self, klines: List) -> int:
        """计算波动率评分
        
        高波动率 = 恐慌
        低波动率 = 平静
        """
        # 计算每小时收益率
        returns = []
        for i in range(1, len(klines)):
            prev_close = klines[i-1][4]
            curr_close = klines[i][4]
            if prev_close > 0:
                ret = (curr_close - prev_close) / prev_close
                returns.append(ret)
        
        if not returns:
            return 50
        
        # 计算标准差
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        std_ret = variance ** 0.5
        
        # 标准差越大，越恐慌（评分越低）
        # 假设标准差范围：0.001 到 0.05
        normalized = (std_ret - 0.001) / 0.049
        normalized = max(0, min(1, normalized))
        
        # 反转：高波动 = 低分（恐慌）
        score = int((1 - normalized) * 100)
        
        return score
    
    def _calculate_volume_trend(self, klines: List) -> int:
        """计算成交量趋势评分
        
        成交量放大 + 价格下跌 = 恐慌抛售
        成交量放大 + 价格上涨 = 贪婪追涨
        """
        if len(klines) < 48:
            return 50
        
        # 最近24小时成交量
        recent_volume = sum(k[5] for k in klines[-24:])
        
        # 前24小时成交量
        prev_volume = sum(k[5] for k in klines[-48:-24])
        
        if prev_volume == 0:
            return 50
        
        volume_ratio = recent_volume / prev_volume
        
        # 最近24小时价格变化
        recent_price_change = (klines[-1][4] - klines[-24][4]) / klines[-24][4]
        
        # 成交量放大
        if volume_ratio > 1.5:
            if recent_price_change < -0.03:  # 恐慌抛售
                return 20
            elif recent_price_change > 0.03:  # 贪婪追涨
                return 80
            else:
                return 50
        elif volume_ratio < 0.7:  # 成交量萎缩
            return 50
        else:
            return 50
    
    def _calculate_price_position(self, klines: List) -> int:
        """计算价格位置评分
        
        价格在近期高点 = 贪婪
        价格在近期低点 = 恐慌
        """
        if len(klines) < 24:
            return 50
        
        # 最近7天的高低点
        highs = [k[2] for k in klines]
        lows = [k[3] for k in klines]
        
        max_high = max(highs)
        min_low = min(lows)
        current_price = klines[-1][4]
        
        if max_high == min_low:
            return 50
        
        # 计算当前位置（0=最低，1=最高）
        position = (current_price - min_low) / (max_high - min_low)
        
        # 位置越高，越贪婪（评分越高）
        score = int(position * 100)
        
        return score
    
    def _calculate_momentum(self, klines: List) -> int:
        """计算动量评分
        
        持续上涨 = 贪婪
        持续下跌 = 恐慌
        """
        if len(klines) < 24:
            return 50
        
        # 最近24小时的价格变化
        price_changes = []
        for i in range(-24, -1):
            prev = klines[i-1][4]
            curr = klines[i][4]
            if prev > 0:
                change = (curr - prev) / prev
                price_changes.append(change)
        
        if not price_changes:
            return 50
        
        # 计算正收益和负收益
        positive_count = sum(1 for c in price_changes if c > 0)
        negative_count = sum(1 for c in price_changes if c < 0)
        
        # 正收益比例
        positive_ratio = positive_count / len(price_changes)
        
        # 正收益越多，越贪婪
        score = int(positive_ratio * 100)
        
        return score
    
    def _index_to_sentiment(self, index: int) -> str:
        """指数转情绪"""
        if index <= self.extreme_fear:
            return 'extreme_fear'
        elif index <= self.fear:
            return 'fear'
        elif index <= self.neutral_high:
            return 'neutral'
        elif index <= self.extreme_greed:
            return 'greed'
        else:
            return 'extreme_greed'
    
    def _generate_signal(self, index: int, sentiment: str) -> tuple:
        """生成交易信号（反向）
        
        极度恐慌 → 强烈买入
        恐慌 → 买入
        中性 → 观望
        贪婪 → 卖出
        极度贪婪 → 强烈卖出
        """
        if sentiment == 'extreme_fear':
            return 'strong_buy', 0.8
        elif sentiment == 'fear':
            return 'buy', 0.6
        elif sentiment == 'neutral':
            return 'hold', 0.5
        elif sentiment == 'greed':
            return 'sell', 0.6
        else:  # extreme_greed
            return 'strong_sell', 0.8
    
    def get_sentiment_score(self, fear_greed_index: int) -> int:
        """获取情绪评分（0-100）
        
        用于综合信号生成
        
        注意：这是反向指标！
        - 恐惧贪婪指数低 → 评分高（买入）
        - 恐惧贪婪指数高 → 评分低（卖出）
        """
        # 反转：恐惧贪婪指数越低，评分越高
        return 100 - fear_greed_index


# 测试
if __name__ == '__main__':
    analyzer = SentimentAnalyzer()
    
    # 分析DOGE情绪
    result = analyzer.analyze_sentiment('DOGEUSDT')
    if result:
        print(f"\n📊 DOGE 散户情绪分析")
        print(f"   恐惧贪婪指数: {result.fear_greed_index}")
        print(f"   市场情绪: {result.sentiment}")
        print(f"   交易信号: {result.signal}")
        print(f"   置信度: {result.confidence:.0%}")
        print(f"   各指标: {result.indicators}")
        
        # 获取评分
        score = analyzer.get_sentiment_score(result.fear_greed_index)
        print(f"   情绪评分（反向）: {score}/100")
