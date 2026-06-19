#!/usr/bin/env python3
"""
实时交易引擎启动脚本
====================

WebSocket驱动，K线收盘时自动评估策略。

用法：
    python realtime.py                    # 启动实时引擎
    python realtime.py --symbols DOGEUSDT # 指定交易对
    python realtime.py --interval 15m     # 15分钟周期
    python realtime.py --test             # 测试WebSocket连接
"""

import sys
import os
import signal
import argparse
from loguru import logger

sys.path.insert(0, os.path.dirname(__file__))


def setup_logging():
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
    logger.add("logs/realtime.log", rotation="1 day", retention="7 days", level="DEBUG")


def test_connection(symbols):
    """测试WebSocket连接"""
    from core.realtime import BinanceWebSocket
    import time
    
    print("📡 测试Binance WebSocket连接...")
    ws = BinanceWebSocket(symbols, ['1h'])
    
    # 测试预热
    import httpx
    client = httpx.Client(timeout=15)
    
    for symbol in symbols:
        try:
            resp = client.get(
                'https://data-api.binance.vision/api/v3/klines',
                params={'symbol': symbol, 'interval': '1h', 'limit': 5}
            )
            if resp.status_code == 200:
                data = resp.json()
                price = float(data[-1][4])
                print(f"   ✅ {symbol}: ${price:.8f} ({len(data)}根K线)")
            else:
                print(f"   ❌ {symbol}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"   ❌ {symbol}: {e}")
    
    client.close()
    
    # 测试WebSocket
    print("\n📡 测试WebSocket连接...")
    ws.start()
    time.sleep(5)
    
    status = ws.get_status()
    if status['connected']:
        print(f"   ✅ WebSocket已连接")
        print(f"   📊 K线缓存: {status['kline_counts']}")
    else:
        print(f"   ❌ WebSocket未连接")
    
    ws.stop()
    print("\n✅ 测试完成")


def run_realtime(symbols, interval):
    """运行实时引擎"""
    from core.engine.livermore_engine import LivermoreEngine
    from core.realtime import RealtimeEngine
    import json
    
    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), "test_config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {'leverage': 10, 'initial_balance': 10.0}
    
    # 创建引擎
    engine = LivermoreEngine(
        initial_balance=config.get('initial_balance', 10.0),
        db_path="data/realtime.db",
        config=config
    )
    
    # 创建实时引擎
    rt = RealtimeEngine(engine, symbols, [interval])
    
    # 优雅退出
    def shutdown(sig, frame):
        print("\n🛑 收到停止信号，正在关闭...")
        rt.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    # 启动
    rt.start()
    
    print(f"""
╔══════════════════════════════════════╗
║     ⚡ 实时交易引擎已启动            ║
╠══════════════════════════════════════╣
║  交易对: {', '.join(symbols):<26} ║
║  周期:   {interval:<26} ║
║  策略:   {config.get('strategy', 'livermore'):<26} ║
║  杠杆:   {config.get('leverage', 10)}x{'':<23} ║
║  资金:   {config.get('initial_balance', 10)}U{'':<23} ║
║                                      ║
║  按 Ctrl+C 停止                      ║
╚══════════════════════════════════════╝
""")
    
    # 保持运行
    import time
    while True:
        time.sleep(60)
        status = rt.get_status()
        logger.info(status)


def main():
    parser = argparse.ArgumentParser(description='实时交易引擎')
    parser.add_argument('--symbols', type=str, default='DOGEUSDT,PEPEUSDT',
                       help='交易对，逗号分隔')
    parser.add_argument('--interval', type=str, default='1h',
                       help='K线周期: 1m/5m/15m/1h/4h')
    parser.add_argument('--test', action='store_true',
                       help='测试连接')
    
    args = parser.parse_args()
    setup_logging()
    
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    if args.test:
        test_connection(symbols)
    else:
        run_realtime(symbols, args.interval)


if __name__ == '__main__':
    main()
