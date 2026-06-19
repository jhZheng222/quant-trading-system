"""策略基类类型定义

策略系统中使用的通用类型定义，供所有策略模块使用。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Signal:
    """交易信号"""
    action: str  # buy, sell, hold
    symbol: str
    price: float
    size: float = 0.0
    confidence: float = 0.5
    reason: str = ""
    timestamp: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "action": self.action,
            "symbol": self.symbol,
            "price": self.price,
            "size": self.size,
            "confidence": self.confidence,
            "reason": self.reason,
        }


class Strategy:
    """策略基类
    
    所有具体策略应继承此类，实现 analyze() 方法。
    """
    
    name: str = "base_strategy"
    
    def __init__(self, **kwargs):
        self.config = kwargs
        
    def analyze(self, klines: List[Dict], **kwargs) -> Signal:
        """分析 K 线数据，返回交易信号"""
        raise NotImplementedError
    
    def get_confidence(self, score: float) -> float:
        """将评分转为置信度 (0-1)"""
        return max(0.0, min(1.0, (score + 100) / 200))
