"""
综合信号生成器 v2（Signal Generator）
整合所有分析模块，生成最终交易信号

模块：
1. 成本分析（大户成本）
2. 资金费率（市场情绪）
3. 订单簿（买卖压力）
4. 散户情绪（反向指标）
5. 清算地图（杠杆猎杀）
"""
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
from dataclasses import dataclass

from core.analysis.cost_basis import CostBasisAnalyzer
from core.analysis.funding_rate_simple import FundingRateAnalyzer
from core.analysis.orderbook import OrderbookAnalyzer
from core.analysis.sentiment import SentimentAnalyzer
from core.analysis.liquidation import LiquidationAnalyzer
from core.data.binance_data import BinanceDataCollector


@dataclass
class TradingSignal:
    """交易信号"""
    symbol: str
    signal: str               # strong_buy/buy/hold/sell/strong_sell
    confidence: float         # 置信度 0-1
    score: int                # 综合评分 0-100
    components: Dict[str, int]  # 各模块评分
    reasons: List[str]        # 信号原因
    current_price: float
    timestamp: str


class SignalGeneratorV2:
    """综合信号生成器 v2（孙宇晨式）
    
    整合以下模块：
    1. 成本分析（大户成本）
    2. 资金费率（市场情绪）
    3. 订单簿（买卖压力）
    4. 散户情绪（反向指标）
    5. 清算地图（杠杆猎杀）
    """
    
    def __init__(self):
        self.collector = BinanceDataCollector()
        self.cost_analyzer = CostBasisAnalyzer()
        self.funding_analyzer = FundingRateAnalyzer()
        self.orderbook_analyzer = OrderbookAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.liquidation_analyzer = LiquidationAnalyzer()
        
        # 模块权重（孙宇晨式：更关注大户行为、情绪和清算）
        self.weights = {
            'cost_basis': 0.25,      # 成本分析
            'funding_rate': 0.15,    # 资金费率/情绪
            'orderbook': 0.15,       # 订单簿
            'sentiment': 0.20,       # 散户情绪（反向）
            'liquidation': 0.25,     # 清算地图
        }
        
        logger.info("综合信号生成器 v2 初始化完成")
    
    def generate_signal(self, symbol: str) -> Optional[TradingSignal]:
        """生成综合交易信号
        
        Args:
            symbol: 交易对，如 'DOGEUSDT'
            
        Returns:
            TradingSignal 对象或 None
        """
        try:
            # 获取当前价格
            ticker = self.collector.collect_ticker(symbol)
            if not ticker:
                logger.warning(f"无法获取 {symbol} 的行情")
                return None
            
            current_price = ticker['last']
            price_change = ticker.get('change', 0)
            
            # 模块1：成本分析
            cost_score = self._analyze_cost(symbol, current_price)
            
            # 模块2：资金费率（基于涨跌幅估算）
            funding_score = self.funding_analyzer.get_rate_score(price_change)
            
            # 模块3：订单簿
            orderbook_score = self._analyze_orderbook(symbol)
            
            # 模块4：散户情绪
            sentiment_score = self._analyze_sentiment(symbol)
            
            # 模块5：清算地图
            liquidation_score = self._analyze_liquidation(symbol)
            
            # 计算综合评分
            components = {
                'cost_basis': cost_score,
                'funding_rate': funding_score,
                'orderbook': orderbook_score,
                'sentiment': sentiment_score,
                'liquidation': liquidation_score,
            }
            
            total_score = sum(
                components[k] * self.weights[k] 
                for k in components
            )
            total_score = int(total_score)
            
            # 生成信号
            signal, confidence = self._score_to_signal(total_score)
            
            # 生成原因
            reasons = self._generate_reasons(components, signal, price_change)
            
            result = TradingSignal(
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                score=total_score,
                components=components,
                reasons=reasons,
                current_price=current_price,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"{symbol} 综合信号 v2: {signal} (评分={total_score}, "
                       f"置信度={confidence:.0%})")
            
            return result
            
        except Exception as e:
            logger.error(f"信号生成失败 {symbol}: {e}")
            return None
    
    def _analyze_cost(self, symbol: str, current_price: float) -> int:
        """成本分析评分"""
        try:
            cost_result = self.cost_analyzer.analyze_whale_cost(symbol)
            if not cost_result:
                return 50
            
            price_ratio = current_price / cost_result.avg_cost
            
            if price_ratio < 0.97:
                return 80
            elif price_ratio < 1.0:
                return 65
            elif price_ratio < 1.05:
                return 50
            elif price_ratio < 1.15:
                return 35
            else:
                return 20
                
        except Exception as e:
            logger.warning(f"成本分析评分失败: {e}")
            return 50
    
    def _analyze_orderbook(self, symbol: str) -> int:
        """订单簿分析评分"""
        try:
            orderbook_result = self.orderbook_analyzer.analyze_orderbook(symbol)
            if not orderbook_result:
                return 50
            
            return self.orderbook_analyzer.get_pressure_score(orderbook_result.bid_ask_ratio)
                
        except Exception as e:
            logger.warning(f"订单簿分析评分失败: {e}")
            return 50
    
    def _analyze_sentiment(self, symbol: str) -> int:
        """散户情绪分析评分"""
        try:
            sentiment_result = self.sentiment_analyzer.analyze_sentiment(symbol)
            if not sentiment_result:
                return 50
            
            return self.sentiment_analyzer.get_sentiment_score(sentiment_result.fear_greed_index)
                
        except Exception as e:
            logger.warning(f"散户情绪分析评分失败: {e}")
            return 50
    
    def _analyze_liquidation(self, symbol: str) -> int:
        """清算地图分析评分"""
        try:
            liquidation_result = self.liquidation_analyzer.analyze_liquidation(symbol)
            if not liquidation_result:
                return 50
            
            return self.liquidation_analyzer.get_liquidation_score(
                liquidation_result.long_pressure,
                liquidation_result.short_pressure
            )
                
        except Exception as e:
            logger.warning(f"清算地图分析评分失败: {e}")
            return 50
    
    def _score_to_signal(self, score: int) -> tuple:
        """评分转信号"""
        if score >= 70:
            return 'strong_buy', 0.8
        elif score >= 55:
            return 'buy', 0.6
        elif score >= 45:
            return 'hold', 0.5
        elif score >= 30:
            return 'sell', 0.6
        else:
            return 'strong_sell', 0.8
    
    def _generate_reasons(self, components: Dict[str, int], 
                         signal: str, price_change: float) -> List[str]:
        """生成信号原因"""
        reasons = []
        
        # 成本分析原因
        cost_score = components.get('cost_basis', 50)
        if cost_score >= 65:
            reasons.append("🐋 价格低于大户成本，大户不会轻易割肉")
        elif cost_score <= 35:
            reasons.append("🐋 价格远高于大户成本，大户可能已出货")
        
        # 资金费率原因
        funding_score = components.get('funding_rate', 50)
        if funding_score >= 70:
            reasons.append("💰 市场过热，散户极度贪婪（反向卖出）")
        elif funding_score <= 30:
            reasons.append("💰 市场恐慌，散户极度恐惧（反向买入）")
        
        # 订单簿原因
        orderbook_score = components.get('orderbook', 50)
        if orderbook_score >= 70:
            reasons.append("📖 买盘强势，大额买单支撑")
        elif orderbook_score <= 30:
            reasons.append("📖 卖盘强势，大额卖单压制")
        
        # 散户情绪原因
        sentiment_score = components.get('sentiment', 50)
        if sentiment_score >= 70:
            reasons.append("😱 散户极度恐慌，可能是底部（反向买入）")
        elif sentiment_score <= 30:
            reasons.append("🤑 散户极度贪婪，可能是顶部（反向卖出）")
        
        # 清算地图原因
        liquidation_score = components.get('liquidation', 50)
        if liquidation_score >= 70:
            reasons.append("💥 空头清算压力大，庄家可能拉盘")
        elif liquidation_score <= 30:
            reasons.append("💥 多头清算压力大，庄家可能砸盘")
        
        # 涨跌幅原因
        if price_change > 5:
            reasons.append(f"📈 24h涨幅 {price_change:.1f}%，注意回调风险")
        elif price_change < -5:
            reasons.append(f"📉 24h跌幅 {price_change:.1f}%，可能超跌反弹")
        
        if not reasons:
            reasons.append("📊 各指标中性，建议观望")
        
        return reasons
    
    def format_signal_report(self, signal: TradingSignal) -> str:
        """格式化信号报告"""
        signal_icons = {
            'strong_buy': '🟢🟢',
            'buy': '🟢',
            'hold': '🟡',
            'sell': '🔴',
            'strong_sell': '🔴🔴'
        }
        
        icon = signal_icons.get(signal.signal, '⚪')
        
        score_bar = '█' * (signal.score // 5) + '░' * (20 - signal.score // 5)
        
        report = f"""
📊 {signal.symbol} 信号分析 v2（孙宇晨式）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🐋 成本分析:      {signal.components['cost_basis']}/100  {self._score_bar(signal.components['cost_basis'])}
💰 市场情绪:      {signal.components['funding_rate']}/100  {self._score_bar(signal.components['funding_rate'])}
📖 订单簿:        {signal.components['orderbook']}/100  {self._score_bar(signal.components['orderbook'])}
😱 散户情绪:      {signal.components['sentiment']}/100  {self._score_bar(signal.components['sentiment'])}
💥 清算地图:      {signal.components['liquidation']}/100  {self._score_bar(signal.components['liquidation'])}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 综合评分:      {signal.score}/100  {score_bar}
🎯 信号:          {icon} {signal.signal.upper()}
💡 置信度:        {signal.confidence:.0%}
💰 当前价格:      ${signal.current_price:.6f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 分析原因:
"""
        for reason in signal.reasons:
            report += f"   {reason}\n"
        
        report += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        report += f"⏰ {signal.timestamp}\n"
        
        return report
    
    def _score_bar(self, score: int) -> str:
        """生成评分条"""
        filled = score // 5
        empty = 20 - filled
        return '█' * filled + '░' * empty


# 测试
if __name__ == '__main__':
    generator = SignalGeneratorV2()
    
    # 生成DOGE信号
    signal = generator.generate_signal('DOGEUSDT')
    if signal:
        report = generator.format_signal_report(signal)
        print(report)
