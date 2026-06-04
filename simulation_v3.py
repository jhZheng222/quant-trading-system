"""
模拟交易启动脚本 v3
集成庄家行为分析信号系统
"""
import asyncio
import argparse
from loguru import logger
import sys

from core.simulation.engine_v3 import SimulationEngineV3


def setup_logging():
    """配置日志"""
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/simulation_v3.log", rotation="1 day", retention="7 days", level="DEBUG")


async def run_simulation(interval: int = 3600, initial_balance: float = 10.0):
    """运行模拟交易
    
    Args:
        interval: 交易间隔（秒）
        initial_balance: 初始资金（U）
    """
    engine = SimulationEngineV3(initial_balance=initial_balance)
    
    logger.info(f"启动模拟交易v3（庄家行为分析），初始资金: {initial_balance}U，间隔: {interval}秒")
    
    while True:
        try:
            logger.info(f"开始分析周期...")
            engine.run_once()
            logger.info(f"等待 {interval} 秒后进入下一个周期...")
        except Exception as e:
            logger.error(f"模拟交易异常: {e}")
        
        await asyncio.sleep(interval)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='模拟交易系统 v3 (庄家行为分析)')
    parser.add_argument('--interval', type=int, default=3600,
                       help='交易间隔（秒），默认3600')
    parser.add_argument('--balance', type=float, default=10.0,
                       help='初始资金（U），默认10')
    parser.add_argument('--once', action='store_true',
                       help='只运行一次')
    
    args = parser.parse_args()
    
    setup_logging()
    
    if args.once:
        # 只运行一次
        engine = SimulationEngineV3(initial_balance=args.balance)
        engine.run_once()
    else:
        # 持续运行
        asyncio.run(run_simulation(args.interval, args.balance))


if __name__ == '__main__':
    main()
