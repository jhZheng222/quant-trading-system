"""
量化交易系统 - 主程序
Binance获取数据 + Gate.io执行交易
"""
import asyncio
import signal
import sys
from datetime import datetime
from loguru import logger

from config.settings import (
    gate_config, trading_config, strategy_config, 
    monitor_config, log_config
)
from core.data.service import DataCollectionService
from core.strategy.engine import StrategyEngine
from core.exchange.executor import TradeExecutor
from models.init_db import init_database


class TradingSystem:
    """量化交易系统"""
    
    def __init__(self, sandbox: bool = True):
        """初始化系统
        
        Args:
            sandbox: 是否使用模拟盘
        """
        self.sandbox = sandbox
        self.running = False
        
        # 配置日志
        self._setup_logging()
        
        logger.info("=" * 50)
        logger.info("量化交易系统初始化")
        logger.info(f"模式: {'模拟盘' if sandbox else '实盘'}")
        logger.info("数据源: Binance (公开API)")
        logger.info("交易所: Gate.io")
        logger.info("=" * 50)
        
        # 初始化数据库
        try:
            init_database()
            logger.info("数据库初始化完成")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
        
        # 初始化组件
        self.data_service = DataCollectionService()
        self.strategy = StrategyEngine(strategy_config.dict())
        self.executor = TradeExecutor(sandbox=sandbox)
        
        # 交易对映射 (Binance -> Gate.io)
        self.symbol_mapping = {
            'DOGEUSDT': 'DOGE/USDT',
            'PEPEUSDT': 'PEPE/USDT',
        }
        
        logger.info("系统初始化完成")
    
    def _setup_logging(self):
        """配置日志"""
        import os
        os.makedirs(log_config.log_dir, exist_ok=True)
        
        logger.remove()
        logger.add(sys.stderr, level=log_config.log_level)
        logger.add(
            f"{log_config.log_dir}/trading.log",
            rotation=log_config.log_rotation,
            retention=log_config.log_retention,
            compression=log_config.log_compression,
            level=log_config.log_level
        )
    
    def analyze_symbol(self, binance_symbol: str):
        """分析单个交易对
        
        Args:
            binance_symbol: Binance交易对格式，如 'DOGEUSDT'
        """
        try:
            # 获取Gate.io交易对格式
            gate_symbol = self.symbol_mapping.get(binance_symbol)
            if not gate_symbol:
                logger.warning(f"未知交易对: {binance_symbol}")
                return
            
            # 从Binance获取K线数据
            klines = self.data_service.get_latest_klines(binance_symbol, '1h')
            
            if not klines:
                # 如果缓存没有，实时采集
                klines = self.data_service.collector.collect_klines(binance_symbol, '1h', 100)
            
            if not klines:
                logger.warning(f"无法获取K线数据: {binance_symbol}")
                return
            
            # 策略分析
            signal = self.strategy.analyze(
                symbol=gate_symbol,
                klines=klines
            )
            
            logger.info(f"分析结果: {binance_symbol} -> {gate_symbol}")
            logger.info(f"  信号={signal.signal_type} 置信度={signal.confidence:.2f}")
            logger.info(f"  价格={signal.price} 原因={signal.reason}")
            
            # 执行信号
            if signal.signal_type != 'hold':
                self.executor.execute_signal(signal)
            
        except Exception as e:
            logger.error(f"分析失败 {binance_symbol}: {e}")
    
    def run_cycle(self):
        """运行一个交易周期"""
        logger.info(f"开始交易周期: {datetime.now()}")
        
        # 1. 采集数据
        logger.info("采集市场数据...")
        self.data_service.collect_all_tickers()
        self.data_service.collect_all_klines('1h', 100)
        
        # 2. 分析所有交易对
        for binance_symbol in self.symbol_mapping.keys():
            self.analyze_symbol(binance_symbol)
        
        # 3. 检查止损止盈
        self.executor.check_stop_loss_take_profit()
        
        # 4. 更新持仓
        self.executor.update_positions()
        
        # 5. 获取状态
        status = self.executor.get_status()
        cache_status = self.data_service.get_cache_status()
        
        logger.info(f"当前状态:")
        logger.info(f"  持仓: {status['positions']}")
        logger.info(f"  今日交易: {status['daily_trades']}")
        logger.info(f"  今日盈亏: {status['daily_pnl']:.2f}U")
        
        for symbol, info in cache_status.items():
            logger.info(f"  {symbol}: 更新时间={info['last_update']}")
        
        logger.info(f"交易周期结束: {datetime.now()}")
    
    async def run(self, interval: int = 3600):
        """运行系统
        
        Args:
            interval: 交易间隔（秒），默认1小时
        """
        self.running = True
        
        logger.info(f"系统启动，交易间隔: {interval}秒")
        
        # 注册信号处理
        def signal_handler(sig, frame):
            logger.info("收到停止信号，正在关闭...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 主循环
        while self.running:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"交易周期异常: {e}")
            
            # 等待下一个周期
            logger.info(f"等待 {interval} 秒后进入下一个周期...")
            await asyncio.sleep(interval)
        
        logger.info("系统已停止")
    
    def stop(self):
        """停止系统"""
        self.running = False
        self.data_service.stop()
        logger.info("系统停止中...")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='量化交易系统')
    parser.add_argument('--sandbox', action='store_true', default=True,
                       help='使用模拟盘（默认）')
    parser.add_argument('--live', action='store_true',
                       help='使用实盘')
    parser.add_argument('--interval', type=int, default=3600,
                       help='交易间隔（秒），默认3600')
    parser.add_argument('--once', action='store_true',
                       help='只运行一次')
    
    args = parser.parse_args()
    
    # 确定模式
    sandbox = not args.live
    
    try:
        # 创建系统
        system = TradingSystem(sandbox=sandbox)
        
        if args.once:
            # 只运行一次
            system.run_cycle()
        else:
            # 持续运行
            asyncio.run(system.run(interval=args.interval))
            
    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"系统异常: {e}")
        raise


if __name__ == '__main__':
    main()