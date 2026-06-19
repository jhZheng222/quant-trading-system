"""
监控服务启动脚本
"""
import asyncio
import argparse
from loguru import logger
import sys

from core.monitor.contract_monitor import ContractMonitor
from core.monitor.web_dashboard import start_web_monitor


def setup_logging():
    """配置日志"""
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/monitor.log", rotation="1 day", retention="7 days", level="DEBUG")


async def run_monitor(interval: int = 60):
    """运行监控服务"""
    monitor = ContractMonitor()
    
    logger.info(f"启动监控服务，更新间隔: {interval}秒")
    
    # 首次更新
    monitor.update()
    print(monitor.get_market_overview())
    
    # 持续监控
    await monitor.start(interval)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='合约数据监控')
    parser.add_argument('--mode', choices=['cli', 'web', 'both'], default='cli',
                       help='运行模式: cli=命令行, web=Web面板, both=两者')
    parser.add_argument('--interval', type=int, default=60,
                       help='数据更新间隔（秒），默认60')
    parser.add_argument('--port', type=int, default=8080,
                       help='Web端口，默认8080')
    
    args = parser.parse_args()
    
    setup_logging()
    
    if args.mode == 'cli':
        asyncio.run(run_monitor(args.interval))
    elif args.mode == 'web':
        start_web_monitor(port=args.port)
    elif args.mode == 'both':
        # 启动Web服务器
        import threading
        web_thread = threading.Thread(target=start_web_monitor, kwargs={'port': args.port})
        web_thread.daemon = True
        web_thread.start()
        
        # 运行CLI监控
        asyncio.run(run_monitor(args.interval))


if __name__ == '__main__':
    main()