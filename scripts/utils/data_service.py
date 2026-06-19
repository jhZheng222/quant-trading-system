#!/usr/bin/env python3
"""
数据服务管理脚本
==============

启动和管理WebSocket数据转发服务

用法：
    python data_service.py start          # 启动服务
    python data_service.py stop           # 停止服务
    python data_service.py status         # 查看状态
    python data_service.py test           # 测试连接
"""

import sys
import os
import signal
import json
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.data.websocket_service import init_data_service, DataClient

# 配置
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config', 'data_service.json')
PID_FILE = os.path.join(os.path.dirname(__file__), 'config', 'data_service.pid')

DEFAULT_CONFIG = {
    'symbols': ['DOGEUSDT', 'PEPEUSDT'],
    'intervals': ['1h', '15m'],
    'host': 'localhost',
    'port': 8765
}


def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG


def save_config(config):
    """保存配置"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def start_service():
    """启动数据服务"""
    import asyncio
    import threading
    
    config = load_config()
    
    print("=" * 60)
    print("📡 启动数据服务")
    print("=" * 60)
    print(f"\n交易对: {', '.join(config['symbols'])}")
    print(f"周期: {', '.join(config['intervals'])}")
    print(f"地址: ws://{config['host']}:{config['port']}")
    print("\n⏳ 正在启动...")
    
    # 初始化服务
    forwarder, data_source = init_data_service(
        config['symbols'],
        config['intervals'],
        config['host'],
        config['port']
    )
    
    # 启动数据源
    data_source.start()
    
    # 保存PID
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    print("✅ 数据源已启动")
    
    # 启动转发服务
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def run():
        await forwarder.start()
        print(f"✅ 转发服务已启动: ws://{config['host']}:{config['port']}")
        print("\n按 Ctrl+C 停止服务\n")
        
        # 保持运行
        try:
            await asyncio.Future()  # 永远等待
        except asyncio.CancelledError:
            pass
    
    # 信号处理
    def signal_handler(sig, frame):
        print("\n正在停止服务...")
        forwarder.stop()
        data_source.stop()
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        loop.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        pass
    finally:
        forwarder.stop()
        data_source.stop()
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


def stop_service():
    """停止数据服务"""
    if not os.path.exists(PID_FILE):
        print("❌ 服务未运行")
        return
    
    with open(PID_FILE, 'r') as f:
        pid = int(f.read().strip())
    
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"✅ 服务已停止 (PID: {pid})")
        os.remove(PID_FILE)
    except ProcessLookupError:
        print("❌ 进程不存在")
        os.remove(PID_FILE)
    except Exception as e:
        print(f"❌ 停止失败: {e}")


def show_status():
    """显示服务状态"""
    print("=" * 60)
    print("📊 数据服务状态")
    print("=" * 60)
    
    # 检查PID文件
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # 检查进程是否存在
        try:
            os.kill(pid, 0)
            print(f"\n✅ 服务运行中 (PID: {pid})")
        except ProcessLookupError:
            print("\n❌ 服务未运行 (PID文件存在但进程不存在)")
            os.remove(PID_FILE)
    else:
        print("\n❌ 服务未运行")
    
    # 显示配置
    config = load_config()
    print(f"\n📋 配置:")
    print(f"   交易对: {', '.join(config['symbols'])}")
    print(f"   周期: {', '.join(config['intervals'])}")
    print(f"   地址: ws://{config['host']}:{config['port']}")
    
    print("=" * 60)


def test_connection():
    """测试连接"""
    import asyncio
    
    config = load_config()
    url = f"ws://{config['host']}:{config['port']}"
    
    print(f"测试连接: {url}")
    
    async def test():
        client = DataClient(url)
        
        received = False
        
        def on_ticker(symbol, ticker):
            nonlocal received
            received = True
            print(f"✅ 收到数据: {symbol} = ${ticker['price']:.6f}")
        
        client.on_ticker = on_ticker
        client.start()
        
        # 等待数据
        for _ in range(10):
            if received:
                break
            await asyncio.sleep(1)
        
        client.stop()
        
        if not received:
            print("❌ 未收到数据，请检查服务是否启动")
            return False
        
        return True
    
    result = asyncio.run(test())
    return result


def update_config():
    """更新配置"""
    config = load_config()
    
    print("当前配置:")
    print(json.dumps(config, indent=2))
    
    print("\n输入新配置（直接回车保持不变）:")
    
    symbols = input(f"交易对 [{', '.join(config['symbols'])}]: ").strip()
    if symbols:
        config['symbols'] = [s.strip().upper() for s in symbols.split(',')]
    
    intervals = input(f"周期 [{', '.join(config['intervals'])}]: ").strip()
    if intervals:
        config['intervals'] = [i.strip() for i in intervals.split(',')]
    
    port = input(f"端口 [{config['port']}]: ").strip()
    if port:
        config['port'] = int(port)
    
    save_config(config)
    print("\n✅ 配置已保存")


def main():
    if len(sys.argv) < 2:
        print("用法: python data_service.py {start|stop|status|test|config}")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'start':
        start_service()
    elif command == 'stop':
        stop_service()
    elif command == 'status':
        show_status()
    elif command == 'test':
        test_connection()
    elif command == 'config':
        update_config()
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
