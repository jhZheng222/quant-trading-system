from abc import ABC, abstractmethod
from datetime import datetime
from typing import List
from data.data_fetcher import KLineModel

class BaseStrategy(ABC):
    @abstractmethod
    def analyze(self, historical_data: List[KLineModel]) -> bool:
        """
        策略分析核心方法
        :param historical_data: 历史K线数据
        :return: 是否触发交易信号
        """
        
    @abstractmethod
    def get_parameters(self) -> dict:
        """
        获取策略参数
        """

    @abstractmethod
    def update_parameters(self, params: dict):
        """
        更新策略参数
        """