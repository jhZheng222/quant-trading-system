"""
市场情绪分析模块
================

免费数据源：
- Fear & Greed Index (alternative.me)
- Binance 成交量/涨跌幅
- Binance 资金费率
- Binance 持仓量

情绪信号用于辅助决策，不直接产生交易信号。
"""

import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class MarketSentiment:
    """市场情绪分析器"""
    
    def __init__(self):
        if not HAS_HTTPX:
            logger.warning("httpx未安装，情绪分析不可用")
            self.client = None
        else:
            self.client = httpx.Client(timeout=15)
        
        # 缓存
        self._fng_cache = None
        self._fng_time = 0
        self._funding_cache = {}
        self._funding_time = 0
        
        logger.info("📊 市场情绪分析器初始化完成")
    
    def get_full_sentiment(self, symbols: List[str] = None) -> Dict:
        """
        获取完整情绪分析
        
        Returns:
            {
                'fear_greed': {'value': 29, 'label': 'Fear'},
                'funding_rates': {'DOGEUSDT': 0.01, ...},
                'volume_anomaly': {'DOGEUSDT': 1.5, ...},
                'market_heat': 'cold'|'warm'|'hot',
                'sentiment_score': 0-100,
                'signal': 'fear'|'neutral'|'greed',
                'contrarian_signal': 'buy'|'hold'|'sell'
            }
        """
        symbols = symbols or ['DOGEUSDT', 'PEPEUSDT']
        
        result = {
            'fear_greed': self._get_fear_greed(),
            'funding_rates': {},
            'volume_anomaly': {},
            'price_momentum': {},
            'market_heat': 'neutral',
            'sentiment_score': 50,
            'signal': 'neutral',
            'contrarian_signal': 'hold',
            'details': []
        }
        
        # 资金费率
        for symbol in symbols:
            fr = self._get_funding_rate(symbol)
            if fr is not None:
                result['funding_rates'][symbol] = fr
            
            # 成交量异常
            va = self._get_volume_anomaly(symbol)
            if va is not None:
                result['volume_anomaly'][symbol] = va
            
            # 价格动量
            pm = self._get_price_momentum(symbol)
            if pm is not None:
                result['price_momentum'][symbol] = pm
        
        # 综合评分
        result['sentiment_score'] = self._calc_sentiment_score(result)
        result['signal'] = self._score_to_signal(result['sentiment_score'])
        result['contrarian_signal'] = self._calc_contrarian(result)
        result['market_heat'] = self._calc_market_heat(result)
        
        return result
    
    def _get_fear_greed(self) -> Dict:
        """获取恐惧贪婪指数"""
        now = time.time()
        if self._fng_cache and now - self._fng_time < 3600:  # 1小时缓存
            return self._fng_cache
        
        if not self.client:
            return {'value': 50, 'label': 'Neutral'}
        
        try:
            resp = self.client.get('https://api.alternative.me/fng/?limit=7')
            data = resp.json()['data']
            
            current = int(data[0]['value'])
            label = data[0]['value_classification']
            
            # 7天趋势
            values = [int(d['value']) for d in data]
            trend = 'improving' if values[0] > values[-1] else 'worsening'
            
            self._fng_cache = {
                'value': current,
                'label': label,
                'trend': trend,
                'history': values
            }
            self._fng_time = now
            
            return self._fng_cache
        except Exception as e:
            logger.warning(f"获取恐惧贪婪指数失败: {e}")
            return {'value': 50, 'label': 'Neutral'}
    
    def _get_funding_rate(self, symbol: str) -> Optional[float]:
        """获取资金费率（多源fallback）"""
        if not self.client:
            return None
        
        # 方法1: 公开API（不需要Key）
        try:
            resp = self.client.get(
                'https://data-api.binance.vision/fapi/v1/premiumIndex',
                params={'symbol': symbol},
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json()
                return float(data['lastFundingRate'])
        except:
            pass
        
        # 方法2: 从K线数据估算（用价格偏离度作为代理）
        try:
            resp = self.client.get(
                'https://data-api.binance.vision/api/v3/klines',
                params={'symbol': symbol, 'interval': '1h', 'limit': 9},
                timeout=8
            )
            if resp.status_code == 200:
                klines = resp.json()
                closes = [float(k[4]) for k in klines]
                # 用8小时价格变化估算资金费率方向
                change_8h = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
                # 经验公式：费率 ≈ 价格变化 * 0.003（系数）
                return round(change_8h * 0.003, 6)
        except:
            pass
        
        return None
    
    def _get_volume_anomaly(self, symbol: str) -> Optional[float]:
        """
        成交量异常检测
        返回：当前成交量 / 20周期均值
        >2.0 = 异常放量, <0.5 = 极度缩量
        """
        if not self.client:
            return None
        
        try:
            resp = self.client.get(
                'https://data-api.binance.vision/api/v3/klines',
                params={'symbol': symbol, 'interval': '1h', 'limit': 21}
            )
            klines = resp.json()
            volumes = [float(k[5]) for k in klines]
            
            current_vol = volumes[-1]
            avg_vol = np.mean(volumes[:-1])
            
            if avg_vol > 0:
                return round(current_vol / avg_vol, 2)
            return 1.0
        except Exception as e:
            logger.debug(f"获取{symbol}成交量失败: {e}")
            return None
    
    def _get_price_momentum(self, symbol: str) -> Optional[Dict]:
        """价格动量（多周期涨跌幅）"""
        if not self.client:
            return None
        
        try:
            resp = self.client.get(
                'https://data-api.binance.vision/api/v3/klines',
                params={'symbol': symbol, 'interval': '1h', 'limit': 72}
            )
            klines = resp.json()
            closes = [float(k[4]) for k in klines]
            
            current = closes[-1]
            
            return {
                '1h': round((current / closes[-2] - 1) * 100, 2) if len(closes) >= 2 else 0,
                '4h': round((current / closes[-5] - 1) * 100, 2) if len(closes) >= 5 else 0,
                '24h': round((current / closes[-25] - 1) * 100, 2) if len(closes) >= 25 else 0,
                '72h': round((current / closes[0] - 1) * 100, 2) if closes[0] > 0 else 0,
            }
        except Exception as e:
            logger.debug(f"获取{symbol}价格动量失败: {e}")
            return None
    
    def _calc_sentiment_score(self, data: Dict) -> float:
        """
        综合情绪评分 (0-100)
        0 = 极度恐惧, 50 = 中性, 100 = 极度贪婪
        """
        scores = []
        
        # 恐惧贪婪指数权重40%
        fng = data.get('fear_greed', {})
        if fng.get('value'):
            scores.append(('fng', fng['value'], 0.4))
        
        # 资金费率权重30%
        frs = data.get('funding_rates', {})
        if frs:
            # 正费率=多头拥挤(贪婪), 负费率=空头拥挤(恐惧)
            avg_fr = np.mean(list(frs.values()))
            fr_score = 50 + avg_fr * 5000  # 0.01费率 → 100分
            fr_score = max(0, min(100, fr_score))
            scores.append(('funding', fr_score, 0.3))
        
        # 成交量异常权重15%
        vas = data.get('volume_anomaly', {})
        if vas:
            avg_va = np.mean(list(vas.values()))
            # 放量=情绪高涨, 缩量=情绪低迷
            va_score = min(100, avg_va * 40)
            scores.append(('volume', va_score, 0.15))
        
        # 价格动量权重15%
        pms = data.get('price_momentum', {})
        if pms:
            avg_24h = np.mean([p.get('24h', 0) for p in pms.values()])
            # 涨=贪婪, 跌=恐惧
            pm_score = 50 + avg_24h * 5  # 10%涨幅 → 100分
            pm_score = max(0, min(100, pm_score))
            scores.append(('momentum', pm_score, 0.15))
        
        if not scores:
            return 50
        
        # 加权平均
        total_weight = sum(w for _, _, w in scores)
        weighted_sum = sum(s * w for _, s, w in scores)
        
        return round(weighted_sum / total_weight, 1)
    
    def _score_to_signal(self, score: float) -> str:
        if score <= 25:
            return 'extreme_fear'
        elif score <= 40:
            return 'fear'
        elif score <= 60:
            return 'neutral'
        elif score <= 75:
            return 'greed'
        else:
            return 'extreme_greed'
    
    def _calc_contrarian(self, data: Dict) -> str:
        """
        反向信号（孙宇晨式操作）
        别人恐惧时贪婪，别人贪婪时恐惧
        """
        score = data.get('sentiment_score', 50)
        fng = data.get('fear_greed', {})
        
        # 极度恐惧 → 反向买入
        if score <= 20:
            return 'strong_buy'
        elif score <= 35:
            return 'buy'
        elif score >= 80:
            return 'strong_sell'
        elif score >= 65:
            return 'sell'
        
        return 'hold'
    
    def _calc_market_heat(self, data: Dict) -> str:
        score = data.get('sentiment_score', 50)
        
        # 检查成交量异常
        vas = data.get('volume_anomaly', {})
        max_va = max(vas.values()) if vas else 1.0
        
        if score >= 70 and max_va >= 2.0:
            return 'overheated'  # 过热，危险
        elif score >= 60:
            return 'warm'
        elif score <= 30:
            return 'frozen'  # 冰点，可能是机会
        elif score <= 40:
            return 'cold'
        
        return 'neutral'
    
    def format_report(self, data: Dict) -> str:
        """格式化情绪报告"""
        fng = data.get('fear_greed', {})
        
        emoji_map = {
            'extreme_fear': '😱',
            'fear': '😰',
            'neutral': '😐',
            'greed': '🤑',
            'extreme_greed': '🔥'
        }
        
        heat_map = {
            'overheated': '🔴 过热',
            'warm': '🟡 温热',
            'neutral': '🟢 正常',
            'cold': '🔵 冷淡',
            'frozen': '❄️ 冰点'
        }
        
        contrarian_map = {
            'strong_buy': '🟢 强烈看多（反向）',
            'buy': '🟢 看多（反向）',
            'hold': '⚪ 观望',
            'sell': '🔴 看空（反向）',
            'strong_sell': '🔴 强烈看空（反向）'
        }
        
        lines = [
            "📊 市场情绪分析",
            f"   恐惧贪婪: {fng.get('value', '?')} ({fng.get('label', '?')}) {emoji_map.get(data['signal'], '')}",
            f"   情绪评分: {data['sentiment_score']}/100",
            f"   市场温度: {heat_map.get(data['market_heat'], data['market_heat'])}",
            f"   反向信号: {contrarian_map.get(data['contrarian_signal'], data['contrarian_signal'])}",
        ]
        
        # 资金费率
        frs = data.get('funding_rates', {})
        if frs:
            fr_str = " | ".join(f"{s}: {r*100:.3f}%" for s, r in frs.items())
            lines.append(f"   资金费率: {fr_str}")
        
        # 成交量
        vas = data.get('volume_anomaly', {})
        if vas:
            va_str = " | ".join(f"{s}: {v:.1f}x" for s, v in vas.items())
            lines.append(f"   成交量比: {va_str}")
        
        # 价格动量
        pms = data.get('price_momentum', {})
        if pms:
            for sym, pm in pms.items():
                lines.append(f"   {sym}: 1h={pm.get('1h',0):+.1f}% 4h={pm.get('4h',0):+.1f}% 24h={pm.get('24h',0):+.1f}%")
        
        return "\n".join(lines)
