from binance import AsyncClient
from config.config import Config
from loguru import logger

class RiskManager:
    def __init__(self):
        self.client = AsyncClient(Config.API_KEY, Config.API_SECRET)
        self.position = 0

    async def execute_trade(self, signal):
        try:
            if signal == 'buy' and self.position == 0:
                # 市价单买入
                order = await self.client.create_order(
                    symbol=Config.SYMBOL,
                    side='BUY',
                    type='MARKET',
                    quantity=Config.TRADE_AMOUNT
                )
                self.position = 1
                logger.info(f"买入订单执行成功: {order}")
                
                # 设置止损止盈单
                await self.place_stop_loss_take_profit('SELL')

            elif signal == 'sell' and self.position == 1:
                await self.client.create_order(
                    symbol=Config.SYMBOL,
                    side='SELL',
                    type='MARKET',
                    quantity=Config.TRADE_AMOUNT
                )
                self.position = 0
                logger.info("卖出订单执行成功")

        except Exception as e:
            logger.error(f"交易执行失败: {e}")
        finally:
            await self.client.close_connection()

    async def place_stop_loss_take_profit(self, side):
        ticker = await self.client.get_symbol_ticker(symbol=Config.SYMBOL)
        price = float(ticker['price'])
        
        stop_price = price * (1 - Config.STOP_LOSS_PCT/100) if side == 'SELL' else price * (1 + Config.STOP_LOSS_PCT/100)
        take_profit_price = price * (1 + Config.TAKE_PROFIT_PCT/100) if side == 'SELL' else price * (1 - Config.TAKE_PROFIT_PCT/100)
        
        await self.client.create_order(
            symbol=Config.SYMBOL,
            side=side,
            type='STOP_LOSS_LIMIT',
            quantity=Config.TRADE_AMOUNT,
            price=round(take_profit_price, 4),
            stopPrice=round(stop_price, 4),
            timeInForce='GTC'
        )
        logger.info(f"已设置止损价: {stop_price} 和止盈价: {take_profit_price}")