import asyncio
from datetime import datetime, timedelta
from src.data.data_fetcher import DataFetcher
from loguru import logger
from config.config import Config
import argparse

async def main():
    fetcher = DataFetcher()
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', type=str, default=Config.SYMBOL, help='交易对符号（例如：DOGEUSDT）')
    args = parser.parse_args()
    
    if not args.symbol.upper().endswith('USDT'):
        raise ValueError(f"交易对格式错误: {args.symbol}，必须以USDT结尾")
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=90)
    
    try:
        total_records = 0
        current_start = start_time
        
        while current_start < end_time:
            # 获取3个月数据（币安API限制每次最多1000条）
            data = await fetcher.get_historical_klines(
                interval=Config.INTERVAL,
                start_time=int(current_start.timestamp() * 1000),
                end_time=int(end_time.timestamp() * 1000)
            )
            
            if not data:
                break

            # 按日期分组保存
            data['date'] = data['timestamp'].dt.date
            for date, group in data.groupby('date'):
                save_path = Config.STORAGE_PATH / f"{args.symbol}/{args.symbol}_klines_{date.strftime('%Y%m%d')}.csv"
                group.to_csv(save_path, mode='a', header=not save_path.exists())
            
            total_records += len(data)
            current_start = datetime.fromtimestamp(data['timestamp'].iloc[-1]/1000)
            
            logger.info(f"已获取 {len(data)} 条记录，总记录数：{total_records}")
            
            # 遵守API速率限制
            await asyncio.sleep(1)

        logger.success(f"数据获取完成，总记录数：{total_records}")

    except Exception as e:
        logger.error(f"历史数据获取失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())