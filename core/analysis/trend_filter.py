"""
趋势过滤器
判断市场趋势，只在趋势明确时交易
"""

import numpy as np
from typing import Dict, Any, Optional

class TrendFilter:
    """趋势过滤器"""
    
    def __init__(self):
        """初始化"""
        self.trend_threshold = 0.6  # 趋势确认阈值
        self.adx_threshold = 25     # ADX趋势强度阈值
    
    def calculate_adx(self, highs: list, lows: list, closes: list, period: int = 14) -> float:
        """
        计算ADX（平均趋向指数）
        
        Args:
            highs: 最高价序列
            lows: 最低价序列
            closes: 收盘价序列
            period: 计算周期
            
        Returns:
            ADX值
        """
        if len(highs) < period * 2:
            return 0
        
        # 计算真实波幅TR
        tr_list = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
        
        # 计算方向运动+DM和-DM
        plus_dm = []
        minus_dm = []
        for i in range(1, len(highs)):
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            
            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
            else:
                plus_dm.append(0)
            
            if down_move > up_move and down_move > 0:
                minus_dm.append(down_move)
            else:
                minus_dm.append(0)
        
        # 平滑处理
        if len(tr_list) < period or len(plus_dm) < period:
            return 0
        
        tr_smooth = np.mean(tr_list[-period:])
        plus_dm_smooth = np.mean(plus_dm[-period:])
        minus_dm_smooth = np.mean(minus_dm[-period:])
        
        if tr_smooth == 0:
            return 0
        
        # 计算方向指标
        plus_di = (plus_dm_smooth / tr_smooth) * 100
        minus_di = (minus_dm_smooth / tr_smooth) * 100
        
        # 计算ADX
        di_sum = plus_di + minus_di
        if di_sum == 0:
            return 0
        
        di_diff = abs(plus_di - minus_di)
        dx = (di_diff / di_sum) * 100
        
        return dx
    
    def calculate_ema_trend(self, closes: list, fast_period: int = 12, slow_period: int = 26) -> str:
        """
        计算EMA趋势
        
        Args:
            closes: 收盘价序列
            fast_period: 快速EMA周期
            slow_period: 慢速EMA周期
            
        Returns:
            趋势方向: 'up', 'down', 'sideways'
        """
        if len(closes) < slow_period:
            return 'sideways'
        
        # 计算EMA
        prices = np.array(closes)
        
        # 快速EMA
        multiplier_fast = 2 / (fast_period + 1)
        ema_fast = prices[-fast_period]
        for price in prices[-fast_period+1:]:
            ema_fast = (price - ema_fast) * multiplier_fast + ema_fast
        
        # 慢速EMA
        multiplier_slow = 2 / (slow_period + 1)
        ema_slow = prices[-slow_period]
        for price in prices[-slow_period+1:]:
            ema_slow = (price - ema_slow) * multiplier_slow + ema_slow
        
        # 判断趋势
        diff_percent = (ema_fast - ema_slow) / ema_slow * 100
        
        if diff_percent > 0.5:  # 快EMA高于慢EMA 0.5%以上
            return 'up'
        elif diff_percent < -0.5:  # 快EMA低于慢EMA 0.5%以下
            return 'down'
        else:
            return 'sideways'
    
    def calculate_macd_trend(self, closes: list) -> str:
        """
        计算MACD趋势
        
        Args:
            closes: 收盘价序列
            
        Returns:
            趋势方向: 'up', 'down', 'sideways'
        """
        if len(closes) < 26:
            return 'sideways'
        
        prices = np.array(closes)
        
        # 计算EMA12和EMA26
        def ema(data, period):
            multiplier = 2 / (period + 1)
            result = data[0]
            for price in data[1:]:
                result = (price - result) * multiplier + result
            return result
        
        ema12 = ema(prices[-12:], 12)
        ema26 = ema(prices[-26:], 26)
        
        # MACD线
        macd_line = ema12 - ema26
        
        # 信号线（MACD的9日EMA）
        # 简化处理：使用最近几个MACD值
        macd_values = []
        for i in range(max(0, len(prices)-35), len(prices)):
            if i >= 26:
                ema12_i = ema(prices[i-11:i+1], 12)
                ema26_i = ema(prices[i-25:i+1], 26)
                macd_values.append(ema12_i - ema26_i)
        
        if len(macd_values) < 9:
            return 'sideways'
        
        signal_line = np.mean(macd_values[-9:])
        
        # 判断趋势
        if macd_line > signal_line and macd_line > 0:
            return 'up'
        elif macd_line < signal_line and macd_line < 0:
            return 'down'
        else:
            return 'sideways'
    
    def analyze_trend(self, klines: list) -> Dict[str, Any]:
        """
        综合分析趋势
        
        Args:
            klines: K线数据列表，每条包含 [timestamp, open, high, low, close, volume]
            
        Returns:
            趋势分析结果
        """
        if not klines or len(klines) < 26:
            return {
                'trend': 'sideways',
                'confidence': 0,
                'adx': 0,
                'ema_trend': 'sideways',
                'macd_trend': 'sideways',
                'should_trade': False
            }
        
        # 提取数据
        closes = [k[4] for k in klines]
        highs = [k[2] for k in klines]
        lows = [k[3] for k in klines]
        
        # 计算各指标
        adx = self.calculate_adx(highs, lows, closes)
        ema_trend = self.calculate_ema_trend(closes)
        macd_trend = self.calculate_macd_trend(closes)
        
        # 综合判断趋势
        trend_votes = [ema_trend, macd_trend]
        
        # 如果ADX高于阈值，趋势更可信
        if adx > self.adx_threshold:
            # 统计趋势投票
            up_votes = trend_votes.count('up')
            down_votes = trend_votes.count('down')
            
            if up_votes > down_votes:
                trend = 'up'
                confidence = up_votes / len(trend_votes)
            elif down_votes > up_votes:
                trend = 'down'
                confidence = down_votes / len(trend_votes)
            else:
                trend = 'sideways'
                confidence = 0.5
        else:
            # ADX低，市场震荡
            trend = 'sideways'
            confidence = 0.3
        
        # 是否应该交易
        should_trade = (
            trend != 'sideways' and 
            confidence >= self.trend_threshold and
            adx > self.adx_threshold
        )
        
        return {
            'trend': trend,
            'confidence': round(confidence, 2),
            'adx': round(adx, 2),
            'ema_trend': ema_trend,
            'macd_trend': macd_trend,
            'should_trade': should_trade
        }
    
    def get_trend_direction(self, klines: list) -> str:
        """
        获取趋势方向（简化版）
        
        Args:
            klines: K线数据
            
        Returns:
            'long', 'short', 或 'neutral'
        """
        result = self.analyze_trend(klines)
        
        if not result['should_trade']:
            return 'neutral'
        
        if result['trend'] == 'up':
            return 'long'
        elif result['trend'] == 'down':
            return 'short'
        else:
            return 'neutral'