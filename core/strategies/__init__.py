"""
策略接口和管理器
================

支持动态加载和切换策略。

使用方式：
1. 创建策略文件 core/strategies/my_strategy.py
2. 继承 Strategy 基类
3. 实现 generate_signal 方法
4. 在配置中指定策略名称
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import importlib
import os
from pathlib import Path


@dataclass
class Signal:
    """交易信号"""
    action: str  # 'buy', 'sell', 'hold'
    symbol: str
    price: float
    score: float  # 信号强度 0-100
    reason: str = ''
    metadata: Dict[str, Any] = None


class Strategy(ABC):
    """策略基类"""
    
    name: str = "base"
    description: str = "基础策略"
    version: str = "1.0.0"
    
    # 默认参数
    default_params: Dict[str, Any] = {
        'stop_loss_pct': 0.05,
        'take_profit_pct': 0.08,
        'buy_threshold': 65,
        'sell_threshold': 40,
        'position_size': 0.2
    }
    
    def __init__(self, params: Dict[str, Any] = None):
        self.params = {**self.default_params, **(params or {})}
    
    @abstractmethod
    def generate_signal(self, symbol: str, klines: List, current_price: float) -> Optional[Signal]:
        """
        生成交易信号
        
        Args:
            symbol: 交易对
            klines: K线数据 [[timestamp, open, high, low, close, volume], ...]
            current_price: 当前价格
            
        Returns:
            Signal 对象或 None
        """
        pass
    
    def calculate_position_size(self, balance: float, price: float) -> float:
        """计算仓位大小"""
        available = balance * self.params['position_size']
        leverage = self.params.get('leverage', 10)
        return available * leverage / price
    
    def get_stop_loss(self, price: float, side: str) -> float:
        """计算止损价"""
        if side == 'buy':
            return price * (1 - self.params['stop_loss_pct'])
        else:
            return price * (1 + self.params['stop_loss_pct'])
    
    def get_take_profit(self, price: float, side: str) -> float:
        """计算止盈价"""
        if side == 'buy':
            return price * (1 + self.params['take_profit_pct'])
        else:
            return price * (1 - self.params['take_profit_pct'])
    
    def to_dict(self) -> Dict[str, Any]:
        """导出策略信息"""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'params': self.params
        }


class StrategyManager:
    """策略管理器"""
    
    def __init__(self, strategies_dir: str = None):
        self.strategies_dir = strategies_dir or os.path.join(
            os.path.dirname(__file__), 'strategies'
        )
        self._strategies: Dict[str, type] = {}
        self._load_builtin_strategies()
    
    def _load_builtin_strategies(self):
        """加载内置策略"""
        from . import ema_rsi_strategy
        from . import macd_strategy
        from . import bollinger_strategy
        from . import livermore_strategy
        from . import multi_strategy
        
        self.register_strategy(ema_rsi_strategy.EMARsiStrategy)
        self.register_strategy(macd_strategy.MACDStrategy)
        self.register_strategy(bollinger_strategy.BollingerStrategy)
        self.register_strategy(livermore_strategy.LivermoreStrategy)
        self.register_strategy(multi_strategy.MultiStrategy)
    
    def register_strategy(self, strategy_class: type):
        """注册策略"""
        if not issubclass(strategy_class, Strategy):
            raise ValueError(f"{strategy_class} 必须继承 Strategy")
        self._strategies[strategy_class.name] = strategy_class
    
    def load_strategy(self, name: str, params: Dict[str, Any] = None) -> Strategy:
        """加载策略实例"""
        if name not in self._strategies:
            # 尝试从文件加载
            self._load_from_file(name)
        
        if name not in self._strategies:
            raise ValueError(f"策略不存在: {name}")
        
        strategy_class = self._strategies[name]
        return strategy_class(params)
    
    def _load_from_file(self, name: str):
        """从文件加载策略"""
        strategy_file = os.path.join(self.strategies_dir, f"{name}.py")
        if not os.path.exists(strategy_file):
            return
        
        # 动态导入
        spec = importlib.util.spec_from_file_location(name, strategy_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 查找 Strategy 子类
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, Strategy) and 
                attr is not Strategy):
                self.register_strategy(attr)
                break
    
    def list_strategies(self) -> List[Dict[str, str]]:
        """列出所有可用策略"""
        strategies = []
        for name, cls in self._strategies.items():
            strategies.append({
                'name': name,
                'description': cls.description,
                'version': cls.version
            })
        return strategies
    
    def get_strategy_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取策略详细信息"""
        if name not in self._strategies:
            return None
        
        cls = self._strategies[name]
        return {
            'name': cls.name,
            'description': cls.description,
            'version': cls.version,
            'default_params': cls.default_params
        }


# 全局策略管理器
_manager: Optional[StrategyManager] = None


def get_strategy_manager() -> StrategyManager:
    """获取策略管理器实例"""
    global _manager
    if _manager is None:
        _manager = StrategyManager()
    return _manager


def load_strategy(name: str, params: Dict[str, Any] = None) -> Strategy:
    """加载策略"""
    return get_strategy_manager().load_strategy(name, params)


def list_strategies() -> List[Dict[str, str]]:
    """列出所有策略"""
    return get_strategy_manager().list_strategies()
