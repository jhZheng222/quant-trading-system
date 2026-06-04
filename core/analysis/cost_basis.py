"""
成本分析模块（Cost Basis Analyzer）
分析大户的成本区间，预判止损位置
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
from collections import defaultdict

from core.data.binance_data import BinanceDataCollector


@dataclass
class WhaleCost:
    """大户成本分析结果"""
    symbol: str
    avg_cost: float           # 平均成本
    total_amount: float       # 总持仓量（USDT）
    entry_prices: List[float] # 入场价格列表
    entry_times: List[str]    # 入场时间列表
    estimated_stop_loss: float  # 预估止损位
    estimated_take_profit: float  # 预估止盈位
    confidence: float         # 置信度 0-1
    timestamp: str


class CostBasisAnalyzer:
    """成本分析器
    
    分析大户的成本区间，预判止损位置
    """
    
    def __init__(self, db_path: str = "data/trading.db"):
        self.collector = BinanceDataCollector()
        self.db_path = db_path
        
        # 大户定义：单笔交易 > 10万USDT
        self.whale_threshold = 100000  # USDT
        
        # 止损估算参数
        self.stop_loss_pct = 0.05  # 默认止损5%
        self.take_profit_pct = 0.15  # 默认止盈15%
        
        logger.info("成本分析器初始化完成")
    
    def analyze_whale_cost(self, symbol: str, lookback_hours: int = 24) -> Optional[WhaleCost]:
        """分析大户成本
        
        Args:
            symbol: 交易对，如 'DOGEUSDT'
            lookback_hours: 回溯时间（小时）
            
        Returns:
            WhaleCost 对象或 None
        """
        try:
            # 获取大额交易数据
            # 注意：Binance公开API不提供历史大额交易，这里使用K线数据估算
            klines = self.collector.collect_klines(symbol, '1h', lookback_hours)
            if not klines:
                logger.warning(f"无法获取 {symbol} 的K线数据")
                return None
            
            # 分析成交量异常（可能是大户活动）
            whale_activities = self._detect_whale_activities(klines)
            
            if not whale_activities:
                logger.info(f"{symbol} 未检测到大户活动")
                return None
            
            # 计算大户成本
            total_cost = 0
            total_amount = 0
            entry_prices = []
            entry_times = []
            
            for activity in whale_activities:
                cost = activity['price'] * activity['volume']
                total_cost += cost
                total_amount += activity['volume']
                entry_prices.append(activity['price'])
                entry_times.append(activity['time'])
            
            if total_amount == 0:
                return None
            
            avg_cost = total_cost / total_amount
            
            # 估算止损止盈
            stop_loss = avg_cost * (1 - self.stop_loss_pct)
            take_profit = avg_cost * (1 + self.take_profit_pct)
            
            # 计算置信度
            confidence = self._calculate_confidence(whale_activities, klines)
            
            result = WhaleCost(
                symbol=symbol,
                avg_cost=avg_cost,
                total_amount=total_cost,
                entry_prices=entry_prices,
                entry_times=entry_times,
                estimated_stop_loss=stop_loss,
                estimated_take_profit=take_profit,
                confidence=confidence,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"{symbol} 大户成本分析: 均价={avg_cost:.6f}, "
                       f"止损={stop_loss:.6f}, 止盈={take_profit:.6f}, "
                       f"置信度={confidence:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"成本分析失败 {symbol}: {e}")
            return None
    
    def _detect_whale_activities(self, klines: List) -> List[Dict]:
        """检测大户活动
        
        通过成交量异常来识别可能的大户活动
        
        K线格式: [timestamp, open, high, low, close, volume]
        """
        if len(klines) < 10:
            return []
        
        # 计算平均成交量
        volumes = [k[5] for k in klines]  # volume在第5个位置
        avg_volume = sum(volumes) / len(volumes)
        
        # 标准差
        variance = sum((v - avg_volume) ** 2 for v in volumes) / len(volumes)
        std_volume = variance ** 0.5
        
        # 检测异常成交量（>2倍标准差）
        whale_activities = []
        for kline in klines:
            if kline[5] > avg_volume + 2 * std_volume:
                # 这可能是大户活动
                whale_activities.append({
                    'price': (kline[1] + kline[4]) / 2,  # 使用中间价 (open + close) / 2
                    'volume': kline[5],
                    'time': datetime.fromtimestamp(kline[0] / 1000).isoformat(),
                    'kline': kline
                })
        
        return whale_activities
    
    def _calculate_confidence(self, whale_activities: List[Dict], klines: List) -> float:
        """计算置信度
        
        基于以下因素：
        1. 大户活动数量
        2. 成交量异常程度
        3. 价格集中度
        
        K线格式: [timestamp, open, high, low, close, volume]
        """
        if not whale_activities:
            return 0.0
        
        # 因素1：大户活动数量（越多越可信）
        activity_score = min(len(whale_activities) / 5, 1.0)  # 最多5个活动得满分
        
        # 因素2：成交量异常程度
        volumes = [a['volume'] for a in whale_activities]
        avg_whale_volume = sum(volumes) / len(volumes)
        all_volumes = [k[5] for k in klines]  # volume在第5个位置
        avg_all_volume = sum(all_volumes) / len(all_volumes)
        
        volume_ratio = avg_whale_volume / avg_all_volume if avg_all_volume > 0 else 1
        volume_score = min(volume_ratio / 3, 1.0)  # 3倍以上得满分
        
        # 因素3：价格集中度（价格越集中越可信）
        prices = [a['price'] for a in whale_activities]
        if len(prices) > 1:
            price_std = (sum((p - sum(prices)/len(prices)) ** 2 for p in prices) / len(prices)) ** 0.5
            price_mean = sum(prices) / len(prices)
            price_cv = price_std / price_mean if price_mean > 0 else 1  # 变异系数
            price_score = max(0, 1 - price_cv * 10)  # 变异系数越小越好
        else:
            price_score = 0.5
        
        # 综合置信度
        confidence = (activity_score * 0.3 + volume_score * 0.4 + price_score * 0.3)
        
        return round(confidence, 2)
    
    def get_trading_signal(self, symbol: str, current_price: float) -> Dict:
        """基于成本分析生成交易信号
        
        Args:
            symbol: 交易对
            current_price: 当前价格
            
        Returns:
            交易信号字典
        """
        whale_cost = self.analyze_whale_cost(symbol)
        
        if not whale_cost:
            return {
                'signal': 'hold',
                'reason': '未检测到大户活动',
                'confidence': 0.0
            }
        
        # 计算当前价格相对于大户成本的位置
        price_ratio = current_price / whale_cost.avg_cost
        
        if price_ratio < 0.97:  # 低于大户成本3%
            signal = 'strong_buy'
            reason = f'价格低于大户成本{((1-price_ratio)*100):.1f}%，大户不会轻易割肉'
            confidence = whale_cost.confidence
        elif price_ratio < 1.0:  # 低于大户成本
            signal = 'buy'
            reason = f'价格接近大户成本，跟随建仓'
            confidence = whale_cost.confidence * 0.8
        elif price_ratio < 1.05:  # 高于大户成本5%以内
            signal = 'hold'
            reason = f'价格略高于大户成本，观望'
            confidence = 0.5
        elif price_ratio < 1.15:  # 高于大户成本15%以内
            signal = 'sell'
            reason = f'价格高于大户成本{((price_ratio-1)*100):.1f}%，可能接近止盈'
            confidence = whale_cost.confidence * 0.7
        else:  # 高于大户成本15%以上
            signal = 'strong_sell'
            reason = f'价格远高于大户成本，大户可能已出货'
            confidence = whale_cost.confidence * 0.6
        
        return {
            'signal': signal,
            'reason': reason,
            'confidence': confidence,
            'whale_cost': whale_cost.avg_cost,
            'current_price': current_price,
            'price_ratio': price_ratio,
            'stop_loss': whale_cost.estimated_stop_loss,
            'take_profit': whale_cost.estimated_take_profit
        }


# 使用示例
if __name__ == '__main__':
    analyzer = CostBasisAnalyzer()
    
    # 分析DOGE
    result = analyzer.analyze_whale_cost('DOGEUSDT')
    if result:
        print(f"\n📊 DOGE 大户成本分析")
        print(f"   平均成本: ${result.avg_cost:.6f}")
        print(f"   总持仓: ${result.total_amount:,.0f}")
        print(f"   预估止损: ${result.estimated_stop_loss:.6f}")
        print(f"   预估止盈: ${result.estimated_take_profit:.6f}")
        print(f"   置信度: {result.confidence:.0%}")
    
    # 获取交易信号
    current_price = 0.1005  # 示例价格
    signal = analyzer.get_trading_signal('DOGEUSDT', current_price)
    print(f"\n📈 交易信号")
    print(f"   信号: {signal['signal']}")
    print(f"   原因: {signal['reason']}")
    print(f"   置信度: {signal['confidence']:.0%}")
