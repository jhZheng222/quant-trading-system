"""
订单簿分析模块（Orderbook Analyzer）
分析买卖盘深度，识别大额挂单和买卖压力
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass

from core.data.binance_data import BinanceDataCollector


@dataclass
class OrderbookAnalysis:
    """订单簿分析结果"""
    symbol: str
    bid_wall: float           # 买盘墙（大额买单）
    ask_wall: float           # 卖盘墙（大额卖单）
    bid_ask_ratio: float      # 买卖比例
    spread: float             # 价差
    spread_pct: float         # 价差百分比
    pressure: str             # 买卖压力：buy_pressure/sell_pressure/balanced
    signal: str               # 交易信号：buy/sell/hold
    confidence: float         # 置信度 0-1
    timestamp: str


class OrderbookAnalyzer:
    """订单簿分析器
    
    分析买卖盘深度，识别大额挂单和买卖压力
    """
    
    def __init__(self):
        self.collector = BinanceDataCollector()
        
        # 大额挂单阈值（相对于平均挂单量的倍数）
        self.wall_threshold = 5.0  # 5倍以上视为"墙"
        
        logger.info("订单簿分析器初始化完成")
    
    def analyze_orderbook(self, symbol: str, limit: int = 20) -> Optional[OrderbookAnalysis]:
        """分析订单簿
        
        Args:
            symbol: 交易对，如 'DOGEUSDT'
            limit: 深度档位数
            
        Returns:
            OrderbookAnalysis 对象或 None
        """
        try:
            # 获取深度数据
            depth = self.collector.collect_depth(symbol, limit)
            if not depth:
                logger.warning(f"无法获取 {symbol} 的深度数据")
                return None
            
            bids = depth['bids']  # [[price, quantity], ...]
            asks = depth['asks']
            
            if not bids or not asks:
                return None
            
            # 分析买盘
            bid_analysis = self._analyze_side(bids, 'bid')
            
            # 分析卖盘
            ask_analysis = self._analyze_side(asks, 'ask')
            
            # 计算买卖比例
            bid_volume = sum(q for _, q in bids)
            ask_volume = sum(q for _, q in asks)
            bid_ask_ratio = bid_volume / ask_volume if ask_volume > 0 else 1
            
            # 计算价差
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            spread = best_ask - best_bid
            spread_pct = (spread / best_bid) * 100 if best_bid > 0 else 0
            
            # 判断买卖压力
            pressure = self._determine_pressure(bid_ask_ratio, bid_analysis, ask_analysis)
            
            # 生成交易信号
            signal, confidence = self._generate_signal(
                bid_ask_ratio, pressure, bid_analysis, ask_analysis
            )
            
            result = OrderbookAnalysis(
                symbol=symbol,
                bid_wall=bid_analysis['wall_price'],
                ask_wall=ask_analysis['wall_price'],
                bid_ask_ratio=bid_ask_ratio,
                spread=spread,
                spread_pct=spread_pct,
                pressure=pressure,
                signal=signal,
                confidence=confidence,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"{symbol} 订单簿分析: 买卖比={bid_ask_ratio:.2f}, "
                       f"压力={pressure}, 信号={signal}")
            
            return result
            
        except Exception as e:
            logger.error(f"订单簿分析失败 {symbol}: {e}")
            return None
    
    def _analyze_side(self, orders: List[List[float]], side: str) -> Dict:
        """分析单侧订单簿
        
        Args:
            orders: [[price, quantity], ...]
            side: 'bid' 或 'ask'
            
        Returns:
            分析结果字典
        """
        if not orders:
            return {'wall_price': 0, 'wall_quantity': 0, 'avg_quantity': 0}
        
        quantities = [q for _, q in orders]
        avg_quantity = sum(quantities) / len(quantities)
        
        # 找到最大的"墙"
        max_qty = max(quantities)
        max_idx = quantities.index(max_qty)
        wall_price = orders[max_idx][0]
        
        # 判断是否为真正的"墙"（超过平均值的阈值倍）
        is_wall = max_qty > avg_quantity * self.wall_threshold
        
        return {
            'wall_price': wall_price if is_wall else 0,
            'wall_quantity': max_qty if is_wall else 0,
            'avg_quantity': avg_quantity,
            'is_wall': is_wall
        }
    
    def _determine_pressure(self, bid_ask_ratio: float, 
                           bid_analysis: Dict, ask_analysis: Dict) -> str:
        """判断买卖压力
        
        Args:
            bid_ask_ratio: 买卖比例
            bid_analysis: 买盘分析
            ask_analysis: 卖盘分析
            
        Returns:
            压力类型：buy_pressure/sell_pressure/balanced
        """
        # 因素1：买卖比例
        if bid_ask_ratio > 1.5:
            ratio_score = 1  # 买盘强
        elif bid_ask_ratio < 0.67:
            ratio_score = -1  # 卖盘强
        else:
            ratio_score = 0  # 平衡
        
        # 因素2：是否有买盘墙
        if bid_analysis.get('is_wall'):
            wall_score = 1
        elif ask_analysis.get('is_wall'):
            wall_score = -1
        else:
            wall_score = 0
        
        # 综合判断
        total_score = ratio_score + wall_score
        
        if total_score > 0:
            return 'buy_pressure'
        elif total_score < 0:
            return 'sell_pressure'
        else:
            return 'balanced'
    
    def _generate_signal(self, bid_ask_ratio: float, pressure: str,
                        bid_analysis: Dict, ask_analysis: Dict) -> Tuple[str, float]:
        """生成交易信号
        
        Args:
            bid_ask_ratio: 买卖比例
            pressure: 买卖压力
            bid_analysis: 买盘分析
            ask_analysis: 卖盘分析
            
        Returns:
            (信号, 置信度)
        """
        # 买盘强势
        if pressure == 'buy_pressure':
            if bid_ask_ratio > 2.0:
                return 'strong_buy', 0.7
            else:
                return 'buy', 0.6
        
        # 卖盘强势
        if pressure == 'sell_pressure':
            if bid_ask_ratio < 0.5:
                return 'strong_sell', 0.7
            else:
                return 'sell', 0.6
        
        # 平衡
        return 'hold', 0.5
    
    def get_pressure_score(self, bid_ask_ratio: float) -> int:
        """获取买卖压力评分（0-100）
        
        用于综合信号生成
        
        Args:
            bid_ask_ratio: 买卖比例
            
        Returns:
            评分：0-100
            - 0-30：卖压强
            - 30-45：偏卖
            - 45-55：平衡
            - 55-70：偏买
            - 70-100：买压强
        """
        # 将买卖比例映射到0-100评分
        # 假设比例范围：0.3 到 3.0
        normalized = (bid_ask_ratio - 0.3) / 2.7  # 归一化到 0-1
        normalized = max(0, min(1, normalized))  # 限制在 0-1
        score = int(normalized * 100)
        
        return score


# 测试
if __name__ == '__main__':
    analyzer = OrderbookAnalyzer()
    
    # 分析DOGE订单簿
    result = analyzer.analyze_orderbook('DOGEUSDT')
    if result:
        print(f"\n📊 DOGE 订单簿分析")
        print(f"   买盘墙: ${result.bid_wall:.6f}")
        print(f"   卖盘墙: ${result.ask_wall:.6f}")
        print(f"   买卖比例: {result.bid_ask_ratio:.2f}")
        print(f"   价差: {result.spread_pct:.4f}%")
        print(f"   买卖压力: {result.pressure}")
        print(f"   交易信号: {result.signal}")
        print(f"   置信度: {result.confidence:.0%}")
        
        # 获取评分
        score = analyzer.get_pressure_score(result.bid_ask_ratio)
        print(f"   压力评分: {score}/100")
