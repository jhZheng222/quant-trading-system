"""
清算地图模块（Liquidation Map）
识别高杠杆仓位，预测清算瀑布
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass

from core.data.binance_data import BinanceDataCollector


@dataclass
class LiquidationZone:
    """清算区域"""
    price: float              # 清算价格
    side: str                 # long/short
    leverage: int             # 杠杆倍数
    estimated_size: float     # 预估仓位大小（USDT）
    distance_pct: float       # 距离当前价格的百分比


@dataclass
class LiquidationMap:
    """清算地图"""
    symbol: str
    current_price: float
    long_zones: List[LiquidationZone]   # 多头清算区域
    short_zones: List[LiquidationZone]  # 空头清算区域
    long_pressure: float       # 多头清算压力 0-1
    short_pressure: float      # 空头清算压力 0-1
    signal: str                # 交易信号
    confidence: float          # 置信度
    timestamp: str


class LiquidationAnalyzer:
    """清算地图分析器
    
    核心理念：
    - 高杠杆仓位是"送钱"的
    - 庄家会故意触发清算来获利
    - 识别这些位置，跟随庄家
    
    清算价格计算：
    - 多头清算价 = 开仓价 * (1 - 1/杠杆)
    - 空头清算价 = 开仓价 * (1 + 1/杠杆)
    """
    
    def __init__(self):
        self.collector = BinanceDataCollector()
        
        # 杠杆倍数范围
        self.leverage_levels = [10, 20, 25, 50, 75, 100]
        
        # 清算压力阈值
        self.high_pressure = 0.7  # 高压力
        
        logger.info("清算地图分析器初始化完成")
    
    def analyze_liquidation(self, symbol: str) -> Optional[LiquidationMap]:
        """分析清算地图
        
        Args:
            symbol: 交易对，如 'DOGEUSDT'
            
        Returns:
            LiquidationMap 对象或 None
        """
        try:
            # 获取当前价格
            ticker = self.collector.collect_ticker(symbol)
            if not ticker:
                return None
            
            current_price = ticker['last']
            
            # 获取K线数据（用于估算仓位分布）
            klines = self.collector.collect_klines(symbol, '1h', 168)  # 7天
            if not klines:
                return None
            
            # 估算多头清算区域
            long_zones = self._estimate_long_zones(current_price, klines)
            
            # 估算空头清算区域
            short_zones = self._estimate_short_zones(current_price, klines)
            
            # 计算清算压力
            long_pressure = self._calculate_pressure(current_price, long_zones)
            short_pressure = self._calculate_pressure(current_price, short_zones)
            
            # 生成信号
            signal, confidence = self._generate_signal(
                current_price, long_zones, short_zones, long_pressure, short_pressure
            )
            
            result = LiquidationMap(
                symbol=symbol,
                current_price=current_price,
                long_zones=long_zones,
                short_zones=short_zones,
                long_pressure=long_pressure,
                short_pressure=short_pressure,
                signal=signal,
                confidence=confidence,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"{symbol} 清算地图: 多头压力={long_pressure:.2f}, "
                       f"空头压力={short_pressure:.2f}, 信号={signal}")
            
            return result
            
        except Exception as e:
            logger.error(f"清算地图分析失败 {symbol}: {e}")
            return None
    
    def _estimate_long_zones(self, current_price: float, klines: List) -> List[LiquidationZone]:
        """估算多头清算区域
        
        逻辑：
        - 多头在上涨过程中建仓
        - 价格越高，建仓越多
        - 清算价 = 建仓价 * (1 - 1/杠杆)
        """
        zones = []
        
        # 分析最近7天的价格区间
        highs = [k[2] for k in klines]
        lows = [k[3] for k in klines]
        volumes = [k[5] for k in klines]
        
        max_high = max(highs)
        min_low = min(lows)
        
        # 为每个杠杆倍数估算清算区域
        for leverage in self.leverage_levels:
            # 假设多头在价格下跌过程中建仓
            # 清算价 = 当前价格 * (1 - 1/杠杆)
            liq_price = current_price * (1 - 1/leverage)
            
            # 如果清算价在合理范围内
            if liq_price > min_low:
                # 估算仓位大小（基于成交量）
                avg_volume = sum(volumes) / len(volumes)
                estimated_size = avg_volume * current_price * 0.1  # 简化估算
                
                # 距离当前价格的百分比
                distance_pct = (current_price - liq_price) / current_price * 100
                
                zones.append(LiquidationZone(
                    price=liq_price,
                    side='long',
                    leverage=leverage,
                    estimated_size=estimated_size,
                    distance_pct=distance_pct
                ))
        
        # 按距离排序
        zones.sort(key=lambda z: z.distance_pct)
        
        return zones
    
    def _estimate_short_zones(self, current_price: float, klines: List) -> List[LiquidationZone]:
        """估算空头清算区域
        
        逻辑：
        - 空头在下跌过程中建仓
        - 价格越低，建仓越多
        - 清算价 = 建仓价 * (1 + 1/杠杆)
        """
        zones = []
        
        # 分析最近7天的价格区间
        highs = [k[2] for k in klines]
        lows = [k[3] for k in klines]
        volumes = [k[5] for k in klines]
        
        max_high = max(highs)
        min_low = min(lows)
        
        # 为每个杠杆倍数估算清算区域
        for leverage in self.leverage_levels:
            # 假设空头在价格上涨过程中建仓
            # 清算价 = 当前价格 * (1 + 1/杠杆)
            liq_price = current_price * (1 + 1/leverage)
            
            # 如果清算价在合理范围内
            if liq_price < max_high * 1.1:
                # 估算仓位大小（基于成交量）
                avg_volume = sum(volumes) / len(volumes)
                estimated_size = avg_volume * current_price * 0.1  # 简化估算
                
                # 距离当前价格的百分比
                distance_pct = (liq_price - current_price) / current_price * 100
                
                zones.append(LiquidationZone(
                    price=liq_price,
                    side='short',
                    leverage=leverage,
                    estimated_size=estimated_size,
                    distance_pct=distance_pct
                ))
        
        # 按距离排序
        zones.sort(key=lambda z: z.distance_pct)
        
        return zones
    
    def _calculate_pressure(self, current_price: float, zones: List[LiquidationZone]) -> float:
        """计算清算压力
        
        逻辑：
        - 距离越近，压力越大
        - 杠杆越高，压力越大
        """
        if not zones:
            return 0.0
        
        total_pressure = 0.0
        
        for zone in zones:
            # 距离因子（越近压力越大）
            distance_factor = max(0, 1 - zone.distance_pct / 10)
            
            # 杠杆因子（越高压力越大）
            leverage_factor = zone.leverage / 100
            
            # 综合压力
            pressure = distance_factor * leverage_factor
            total_pressure += pressure
        
        # 归一化到 0-1
        normalized = min(1.0, total_pressure / len(zones))
        
        return normalized
    
    def _generate_signal(self, current_price: float,
                        long_zones: List[LiquidationZone],
                        short_zones: List[LiquidationZone],
                        long_pressure: float,
                        short_pressure: float) -> Tuple[str, float]:
        """生成交易信号
        
        逻辑：
        - 多头清算压力大 → 庄家可能砸盘 → 做空
        - 空头清算压力大 → 庄家可能拉盘 → 做多
        """
        # 压力差
        pressure_diff = short_pressure - long_pressure
        
        if pressure_diff > 0.3:
            # 空头压力大，庄家可能拉盘触发空头清算
            return 'buy', 0.7
        elif pressure_diff < -0.3:
            # 多头压力大，庄家可能砸盘触发多头清算
            return 'sell', 0.7
        elif pressure_diff > 0.1:
            return 'buy', 0.5
        elif pressure_diff < -0.1:
            return 'sell', 0.5
        else:
            return 'hold', 0.5
    
    def get_liquidation_score(self, long_pressure: float, short_pressure: float) -> int:
        """获取清算评分（0-100）
        
        用于综合信号生成
        
        逻辑：
        - 空头压力大 → 评分高（买入）
        - 多头压力大 → 评分低（卖出）
        """
        # 压力差
        pressure_diff = short_pressure - long_pressure
        
        # 归一化到 0-100
        # 压力差范围：-1 到 1
        normalized = (pressure_diff + 1) / 2
        score = int(normalized * 100)
        
        return score
    
    def format_liquidation_report(self, liquidation_map: LiquidationMap) -> str:
        """格式化清算地图报告"""
        report = f"""
💥 {liquidation_map.symbol} 清算地图
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 当前价格: ${liquidation_map.current_price:.6f}

🔴 多头清算区域（庄家砸盘目标）:
"""
        for zone in liquidation_map.long_zones[:5]:
            report += f"   {zone.leverage}x: ${zone.price:.6f} (距离 {zone.distance_pct:.1f}%)\n"
        
        report += f"\n🟢 空头清算区域（庄家拉盘目标）:\n"
        for zone in liquidation_map.short_zones[:5]:
            report += f"   {zone.leverage}x: ${zone.price:.6f} (距离 {zone.distance_pct:.1f}%)\n"
        
        report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 清算压力:
   多头压力: {liquidation_map.long_pressure:.0%}
   空头压力: {liquidation_map.short_pressure:.0%}
🎯 信号: {liquidation_map.signal}
💡 置信度: {liquidation_map.confidence:.0%}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return report


# 测试
if __name__ == '__main__':
    analyzer = LiquidationAnalyzer()
    
    # 分析DOGE清算地图
    result = analyzer.analyze_liquidation('DOGEUSDT')
    if result:
        report = analyzer.format_liquidation_report(result)
        print(report)
