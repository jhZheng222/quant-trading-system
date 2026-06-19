class BinanceHistoryDownloader:
    async def download(
            self,
            symbol: str,
            interval: str,
            start_date: datetime,
            end_date: datetime
    ):
        """支持多时间粒度下载"""
        try:
            path = Config.HISTORY_DATA_PATH / f"{symbol.replace('/', '_')}"
            path.mkdir(parents=True, exist_ok=True)

            while start_date < end_date:
                data = await self._fetch_batch(symbol, interval, start_date)
                self._save_data(data, path)
                start_date = data[-1]['timestamp'] + timedelta(minutes=1)

        except Exception as e:
            logger.error(f"历史数据下载失败: {e}")
            raise