class TradingEngine:
    def __init__(self):
        self.data_provider = BinanceDataProvider()
        self.strategy_runner = StrategyRunner()
        self.risk_manager = ContractRiskManager()
        self.notifier = DingtalkNotifier()

    async def run(self):
        while True:
            try:
                # 获取多交易对数据
                symbols = Config.TRADING_SYMBOLS
                tasks = [self.data_provider.get_klines(s) for s in symbols]
                all_data = await asyncio.gather(*tasks)

                # 策略对比
                best_strategy = await self.strategy_runner.evaluate_strategies(all_data)

                # 执行交易
                if best_strategy.signal:
                    await self.risk_manager.execute_contract_order(best_strategy)
                    self.notifier.send_order_alert(best_strategy)

                await asyncio.sleep(Config.CHECK_INTERVAL)

            except Exception as e:
                self.notifier.send_error_alert(e)
                logger.error(f"引擎运行异常: {e}")