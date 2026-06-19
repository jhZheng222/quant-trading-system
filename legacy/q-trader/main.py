import asyncio
from src.data.data_fetcher import DataFetcher
from strategy import TradingStrategy
from risk_manager import RiskManager
from loguru import logger
from config.config import Config

async def main():
    fetcher = DataFetcher()
    strategy = TradingStrategy()
    risk_manager = RiskManager()

    while True:
        try:
            df = await fetcher.get_klines(Config.INTERVAL)
            signal = strategy.analyze(df)
            
            if signal in ('buy', 'sell'):
                risk_manager.execute_trade(signal)
                
            await asyncio.sleep(60)  # 每分钟检查一次
            
        except Exception as e:
            logger.error(f"程序运行异常: {e}")

if __name__ == "__main__":
    asyncio.run(main())