from binance import AsyncClient
from config.config import Config
import pandas as pd
from loguru import logger
from functools import singledispatchmethod
import time
from pathlib import Path

class KLineModel:
    def __init__(self, raw_data):
        self.open_time = raw_data[0]
        self.open = float(raw_data[1])
        self.high = float(raw_data[2])
        self.low = float(raw_data[3])
        self.close = float(raw_data[4])
        self.volume = float(raw_data[5])
        self.close_time = raw_data[6]
        self.quote_volume = float(raw_data[7])
        self.trades = raw_data[8]
        self.taker_buy_volume = float(raw_data[9])
        self.taker_buy_quote_volume = float(raw_data[10])

    def to_dict(self):
        return self.__dict__

class BaseFetcher:
    def __init__(self):
        self.client = AsyncClient(Config.API_KEY, Config.API_SECRET)
        self._rate_limited_call = asyncio.Semaphore(Config.MAX_CONCURRENT_REQUESTS)
        self.retry_policy = retry(
            stop=stop_after_attempt(Config.MAX_RETRIES),
            wait=wait_exponential(multiplier=1, max=10)
        )

    async def _fetch_klines(self, interval: str, **params) -> List[KLineModel]:
        async with self._rate_limited_call:
            try:
                klines = await self.client.get_klines(
                    symbol=Config.SYMBOL,
                    interval=interval,
                    **params
                )
                return [KLineModel(k) for k in klines]
            except (BinanceAPIError, BinanceRequestException) as e:
                logger.warning(f"API请求失败: {e}")
                raise
            finally:
                await self.client.close_connection()

class DataFetcher(BaseFetcher):
    MAX_RETRIES = 3
    RATE_LIMIT = 5  # 每秒最大请求数

    def __init__(self):
        super().__init__()
        self._rate_limiter = asyncio.Semaphore(self.RATE_LIMIT)
        self._last_request_time = 0

    async def _rate_limited_call(self, coro):
        async with self._rate_limiter:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < 1/self.RATE_LIMIT:
                await asyncio.sleep(1/self.RATE_LIMIT - elapsed)
            self._last_request_time = time.monotonic()
            return await coro

    @singledispatchmethod
    async def get_klines(self, interval: str):
        """实时数据获取默认实现"""
        return await self._fetch_realtime_klines(interval)

    @get_klines.register
    async def _(self, interval: str, start_time: int, end_time: int):
        """历史数据获取实现"""
        return await self.get_historical_klines(interval, start_time, end_time)

    async def get_historical_klines(self, interval: str, start_time: int, end_time: int):
        """公开的历史数据获取方法"""
        return await self._fetch_historical_klines(interval, start_time, end_time)

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, max=10))
    async def _fetch_realtime_klines(self, interval: str):
        try:
            if interval not in Client.KLINE_INTERVALS:
                raise ValueError(f"Invalid interval: {interval}")

            async with self._rate_limited_call:
                klines = await self.client.get_klines(
                    symbol=Config.SYMBOL,
                    interval=interval,
                    limit=Config.REALTIME_LIMIT
                )
                return [KLineModel(k) for k in klines]

        except (BinanceAPIError, BinanceRequestException) as e:
            logger.warning(f"API请求失败: {e}, 剩余重试次数: {self.MAX_RETRIES - _retry_state.attempt_number}")
            raise
        finally:
            await self.client.close_connection()

    async def _fetch_historical_klines(self, interval: str, start_time: int, end_time: int):
        return await self._fetch_klines(
            interval,
            startTime=start_time,
            endTime=end_time,
            limit=Config.HISTORY_LIMIT
        )
# 语法错误通常是由于缺少对应的try语句块。这里补充上try语句块，确保except语句有对应的try。
        try:
            # 这里可以添加需要执行的代码
            pass
        except Exception as e:
            logger.error(f"历史数据获取失败: {e}")

    async def get_bulk_historical_klines(self, interval: str, start_time: int = None, end_time: int = None):
        """批量获取指定时间范围历史数据"""
        end_time = end_time or pd.Timestamp.now().timestamp() * 1000
        start_time = start_time or end_time - Config.MAX_HISTORICAL_DAYS * 24 * 60 * 60 * 1000
        
        all_data = []
        while start_time < end_time:
            chunk_end = min(start_time + Config.HISTORICAL_LIMIT * 60 * 1000, end_time)
            data = await self._fetch_historical_klines(interval, int(start_time), int(chunk_end))
            if data is not None:
                all_data.append(data)
            start_time = chunk_end
        
        return pd.concat(all_data) if all_data else pd.DataFrame()

    def save_to_directory(self, df: pd.DataFrame, directory: str = Config.DATA_DIRECTORY):
        """保存数据到指定目录"""
        try:
            if not df.empty:
                df['date'] = df['timestamp'].dt.date
                Path(directory).mkdir(parents=True, exist_ok=True)
                
                for date, group in df.groupby('date'):
                    filename = f"{directory}/{date}_market_data.parquet"
                    group.drop('date', axis=1).to_parquet(filename)
                    logger.success(f"成功保存数据到 {filename}")
        except Exception as e:
            logger.error(f"数据保存失败: {e}")

    def _process_data(self, klines):
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                          'close_time', 'quote_asset_volume', 'num_trades',
                                          'taker_buy_base', 'taker_buy_quote', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].astype(float)