#!/usr/bin/env python3
"""
利弗莫尔策略 — 自适应版启动脚本

用法：
    python livermore.py                    # 持续运行（每小时）
    python livermore.py --once             # 只运行一次
    python livermore.py --interval 1800    # 30分钟间隔
    python livermore.py --balance 20       # 20U初始资金
    python livermore.py --symbols DOGEUSDT # 指定交易对
"""

import asyncio
import argparse
from loguru import logger
import sys

from core.simulation.engine_livermore_v2 import LivermoreEngineV2


def setup_logging():
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/livermore_v2.log", rotation="1 day", retention="7 days", level="DEBUG")


async def run_loop(interval: int, balance: float, symbols: list):
    engine = LivermoreEngineV2(initial_balance=balance)
    
    logger.info(f"启动利弗莫尔自适应策略，初始资金: {balance}U，间隔: {interval}秒")
    
    while True:
        try:
            logger.info("开始分析周期...")
            engine.run_once(symbols)
            logger.info(f"等待 {interval} 秒后进入下一个周期...")
        except Exception as e:
            logger.error(f"运行异常: {e}")
        
        await asyncio.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description='利弗莫尔策略 — 自适应版')
    parser.add_argument('--interval', type=int, default=3600,
                       help='交易间隔（秒），默认3600')
    parser.add_argument('--balance', type=float, default=10.0,
                       help='初始资金（U），默认10')
    parser.add_argument('--once', action='store_true',
                       help='只运行一次')
    parser.add_argument('--symbols', type=str, default='DOGEUSDT,PEPEUSDT',
                       help='交易对，逗号分隔')
    
    args = parser.parse_args()
    setup_logging()
    
    symbols = args.symbols.split(',')
    
    if args.once:
        engine = LivermoreEngineV2(initial_balance=args.balance)
        engine.run_once(symbols)
    else:
        asyncio.run(run_loop(args.interval, args.balance, symbols))


if __name__ == '__main__':
    main()
