#!/usr/bin/env python3
"""
量化交易系统 v3.0 - 持续运行版

支持单币种独立运行:
  python run_live.py --symbol DOGEUSDT
  python run_live.py --symbol PEPEUSDT
"""

import sys
import os
import time
import signal
import json
import argparse
from datetime import datetime
from loguru import logger

sys.path.insert(0, os.path.dirname(__file__))

# 全局变量
engine = None
running = True


def signal_handler(sig, frame):
    global running
    logger.info("收到停止信号，正在关闭...")
    running = False


def main():
    global engine, running
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='量化交易系统实盘模拟')
    parser.add_argument('--symbol', '-s', type=str, help='指定交易对 (如 DOGEUSDT)')
    args = parser.parse_args()
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 加载配置
    with open('config/settings.json', 'r') as f:
        config = json.load(f)
    
    # 确定交易对
    if args.symbol:
        symbol = args.symbol.upper()
        symbols = [symbol]
        config_name = f'live_{symbol.lower()}'
    else:
        symbols = config['data']['symbols']
        symbol = symbols[0] if len(symbols) == 1 else 'multi'
        config_name = 'live_test'
    
    # 添加日志文件输出（解决 Broken pipe 问题）
    os.makedirs("logs", exist_ok=True)
    log_file = f"logs/{config_name}.log"
    logger.remove()  # 移除默认的 stderr handler
    logger.add(sys.stderr, level="INFO")  # 保留 stderr
    logger.add(log_file, rotation="1 day", retention="7 days", level="INFO",
               format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}")
    
    logger.info("=" * 60)
    logger.info("🚀 量化交易系统 v3.0 - 实盘模拟")
    logger.info("=" * 60)
    logger.info(f"📊 策略: {config['strategy']['name']}")
    logger.info(f"💰 初始资金: {config['risk']['initial_balance']}U")
    logger.info(f"📈 交易对: {', '.join(symbols)}")
    logger.info(f"⚡ 杠杆: {config['strategy']['leverage']}x")
    logger.info(f"🏷️ 配置名: {config_name}")
    logger.info("=" * 60)
    
    # 保存策略参数（仅当配置不存在时）
    from core.config.strategy_config import StrategyConfig
    config_manager = StrategyConfig()
    existing_params = config_manager.load_params(config_name)
    
    if not existing_params:
        # 配置不存在，使用默认参数创建
        config_manager.save_params(
            config['strategy'],
            name=config_name,
            description=f"实盘模拟 {symbol} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        logger.info(f"📝 创建新配置: {config_name}")
    else:
        logger.info(f"📝 使用已有配置: {config_name}")
        logger.info(f"   止损: {existing_params.get('stop_loss_pct', 0)*100:.0f}%")
        logger.info(f"   止盈: {existing_params.get('take_profit_pct', 0)*100:.0f}%")
    
    # 创建引擎
    from core.realtime.engine_v3 import RealtimeEngineV3
    engine = RealtimeEngineV3(
        config_name=config_name,
        mode='simulation',
        symbols=symbols
    )
    
    # 启动引擎
    engine.start()
    
    # 保存PID
    os.makedirs('data', exist_ok=True)
    pid_file = f'data/{config_name}.pid'
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
    
    logger.info(f"✅ 引擎已启动，等待K线数据...")
    logger.info(f"   PID文件: {pid_file}")
    logger.info(f"   按 Ctrl+C 停止")
    
    # 主循环
    try:
        while running:
            time.sleep(10)
            
            # 定期打印状态
            if engine.evaluation_count > 0 and engine.evaluation_count % 5 == 0:
                status = engine.get_status()
                logger.info(f"📊 状态更新: 评估={status['evaluations']} 价格={status.get('prices', {})}")
    except KeyboardInterrupt:
        pass
    finally:
        # 停止引擎
        if engine:
            engine.stop()
        logger.info("🛑 引擎已停止")


if __name__ == "__main__":
    main()
