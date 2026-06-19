#!/usr/bin/env python3
"""
启动实盘模拟测试
================

使用优化版策略 + 10U启动资金

用法：
    python start_live_test.py                # 启动模拟
    python start_live_test.py --status       # 查看状态
    python start_live_test.py --stop         # 停止
"""

import sys
import os
import json
import signal
import argparse
from datetime import datetime
from loguru import logger

sys.path.insert(0, os.path.dirname(__file__))

CONFIG_FILE = "config/settings.json"
PID_FILE = "data/live_test.pid"


def load_config():
    """加载配置"""
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def save_pid(pid: int):
    """保存PID"""
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, 'w') as f:
        f.write(str(pid))


def get_pid() -> int:
    """获取PID"""
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            return int(f.read().strip())
    return 0


def start_engine():
    """启动引擎"""
    config = load_config()
    
    logger.info("=" * 60)
    logger.info("🚀 启动量化交易系统 v3.0 实盘模拟")
    logger.info("=" * 60)
    logger.info(f"📊 策略: {config['strategy']['name']}")
    logger.info(f"💰 初始资金: {config['risk']['initial_balance']}U")
    logger.info(f"📈 交易对: {', '.join(config['data']['symbols'])}")
    logger.info(f"⚡ 杠杆: {config['strategy']['leverage']}x")
    logger.info(f"🛡️ 止损: {config['strategy']['stop_loss_pct']*100}%")
    logger.info(f"🎯 止盈: {config['strategy']['take_profit_pct']*100}%")
    logger.info("=" * 60)
    
    # 导入引擎
    from core.realtime.engine_v3 import RealtimeEngineV3 as TradingEngine
    
    # 保存策略参数
    from core.config.strategy_config import StrategyConfig
    config_manager = StrategyConfig()
    config_manager.save_params(
        config['strategy'],
        name='live_test',
        description=f"实盘模拟测试 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    # 创建引擎
    engine = TradingEngine(
        config_name='live_test',
        mode='simulation',
        symbols=config['data']['symbols']
    )
    
    # 保存PID
    save_pid(os.getpid())
    
    # 启动引擎
    engine.start()
    
    return engine


def show_status():
    """显示状态"""
    pid = get_pid()
    
    if pid:
        try:
            os.kill(pid, 0)
            logger.info(f"✅ 引擎运行中 (PID: {pid})")
        except:
            logger.warning("⚠️ 引擎未运行")
            return
    
    # 读取交易日志
    log_file = "data/simulation_log.json"
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            data = json.load(f)
        
        logger.info("\n📊 交易统计:")
        logger.info(f"   初始资金: {data.get('initial_balance', 10)}U")
        logger.info(f"   当前余额: {data.get('balance', 0):.2f}U")
        logger.info(f"   总盈亏: {data.get('total_pnl', 0):.2f}U")
        logger.info(f"   交易次数: {data.get('total_trades', 0)}")
        logger.info(f"   胜率: {data.get('win_rate', 0):.1f}%")
    else:
        logger.info("📊 暂无交易记录")


def stop_engine():
    """停止引擎"""
    pid = get_pid()
    
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"✅ 已停止引擎 (PID: {pid})")
            os.remove(PID_FILE)
        except:
            logger.warning("⚠️ 停止失败")
    else:
        logger.info("⚠️ 引擎未运行")


def main():
    parser = argparse.ArgumentParser(description='量化交易系统 v3.0 实盘模拟')
    parser.add_argument('--status', action='store_true', help='查看状态')
    parser.add_argument('--stop', action='store_true', help='停止引擎')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.stop:
        stop_engine()
    else:
        start_engine()


if __name__ == "__main__":
    main()
