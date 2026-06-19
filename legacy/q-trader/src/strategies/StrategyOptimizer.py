class StrategyOptimizer:
    async def backtest_strategies(self, data: pd.DataFrame) -> Dict[str, dict]:
        """多策略回测对比"""
        strategies = {
            'RSI策略': RSIStrategy(),
            'MACD策略': MACDStrategy(),
            '布林带策略': BollingerStrategy()
        }

        results = {}
        for name, strategy in strategies.items():
            try:
                perf = await self._run_backtest(strategy, data)
                results[name] = perf
            except Exception as e:
                logger.error(f"{name} 回测失败: {e}")

        return self._select_best(results)