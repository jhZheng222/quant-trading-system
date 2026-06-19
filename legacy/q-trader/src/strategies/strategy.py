from ta.momentum import RSIIndicator
from loguru import logger
from config import Config
import numpy as np

class TradingStrategy:
    def __init__(self, window=14):
        self.window = window
        self.overbought = 70
        self.oversold = 30

    def analyze(self, df):
        try:
            close_prices = df['close'].values
            rsi = RSIIndicator(pd.Series(close_prices), window=self.window).rsi()
            
            last_rsi = rsi.iloc[-1]
            
            if last_rsi > self.overbought:
                return 'sell'
            elif last_rsi < self.oversold:
                return 'buy'
            return 'hold'
        except Exception as e:
            logger.error(f"策略分析错误: {e}")
            return 'error'