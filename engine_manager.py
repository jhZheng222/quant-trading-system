#!/usr/bin/env python3
"""
实时引擎管理脚本
==============

启动和管理实时交易引擎

用法：
    python engine_manager.py start              # 启动模拟交易
    python engine_manager.py start --live       # 启动实盘交易
    python engine_manager.py stop               # 停止引擎
    python engine_manager.py status             # 查看状态
    python engine_manager.py logs               # 查看日志
"""

import sys
import os
import signal
import json
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.realtime.engine_v2 import init_engine, get_engine

# 配置
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config', 'engine_config.json')
PID_FILE = os.path.join(os.path.dirname(__file__), 'config', 'engine.pid')

DEFAULT_CONFIG = {
    'config_name': 'optimized_DOGEUSDT_30d',
    'mode': 'simulation',
    'data_url': 'ws://localhost:8765'
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


def start_engine(live: bool = False):
    """启动引擎"""
    import asyncio
    
    config = load_config()
    
    # 如果是实盘模式
    if live:
        config['mode'] = 'live'
        save_config(config)
    
    print("=" * 60)
    print("⚡ 启动实时引擎")
    print("=" * 60)
    print(f"\n模式: {'实盘' if config['mode'] == 'live' else '模拟'}")
    print(f"配置: {config['config_name']}")
    print(f"数据源: {config['data_url']}")
    print("\n⏳ 正在启动...")
    
    # 初始化引擎
    engine = init_engine(
        config['config_name'],
        config['mode'],
        config['data_url']
    )
    
    # 启动引擎
    engine.start()
    
    # 保存PID
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    print("✅ 引擎已启动")
    print("\n按 Ctrl+C 停止引擎\n")
    
    # 信号处理
    def signal_handler(sig, frame):
        print("\n正在停止引擎...")
        engine.stop()
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 主循环
    try:
        while True:
            time.sleep(30)
            print(engine.format_status())
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


def stop_engine():
    """停止引擎"""
    if not os.path.exists(PID_FILE):
        print("❌ 引擎未运行")
        return
    
    with open(PID_FILE, 'r') as f:
        pid = int(f.read().strip())
    
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"✅ 引擎已停止 (PID: {pid})")
        os.remove(PID_FILE)
    except ProcessLookupError:
        print("❌ 进程不存在")
        os.remove(PID_FILE)
    except Exception as e:
        print(f"❌ 停止失败: {e}")


def show_status():
    """显示引擎状态"""
    print("=" * 60)
    print("⚡ 实时引擎状态")
    print("=" * 60)
    
    # 检查PID文件
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # 检查进程是否存在
        try:
            os.kill(pid, 0)
            print(f"\n✅ 引擎运行中 (PID: {pid})")
        except ProcessLookupError:
            print("\n❌ 引擎未运行 (PID文件存在但进程不存在)")
            os.remove(PID_FILE)
    else:
        print("\n❌ 引擎未运行")
    
    # 显示配置
    config = load_config()
    print(f"\n📋 配置:")
    print(f"   模式: {'实盘' if config['mode'] == 'live' else '模拟'}")
    print(f"   策略: {config['config_name']}")
    print(f"   数据源: {config['data_url']}")
    
    # 显示策略参数
    from core.config.strategy_config import StrategyConfig
    config_manager = StrategyConfig()
    params = config_manager.load_params(config['config_name'])
    
    if params:
        print(f"\n⚙️  策略参数:")
        print(f"   止损: {params['stop_loss_pct']*100:.0f}%")
        print(f"   止盈: {params['take_profit_pct']*100:.0f}%")
        print(f"   买入阈值: {params['buy_threshold']}")
        print(f"   卖出阈值: {params['sell_threshold']}")
        print(f"   仓位: {params['position_size']*100:.0f}%")
    
    print("\n" + "=" * 60)
    print("\n管理命令:")
    print("  python engine_manager.py start          # 启动模拟交易")
    print("  python engine_manager.py start --live   # 启动实盘交易")
    print("  python engine_manager.py stop           # 停止引擎")
    print("  python engine_manager.py config         # 修改配置")


def update_config():
    """更新配置"""
    config = load_config()
    
    print("当前配置:")
    print(json.dumps(config, indent=2))
    
    print("\n输入新配置（直接回车保持不变）:")
    
    config_name = input(f"策略配置 [{config['config_name']}]: ").strip()
    if config_name:
        config['config_name'] = config_name
    
    mode = input(f"模式 (simulation/live) [{config['mode']}]: ").strip()
    if mode in ['simulation', 'live']:
        config['mode'] = mode
    
    data_url = input(f"数据源 [{config['data_url']}]: ").strip()
    if data_url:
        config['data_url'] = data_url
    
    save_config(config)
    print("\n✅ 配置已保存")


def main():
    if len(sys.argv) < 2:
        print("用法: python engine_manager.py {start|stop|status|config}")
        print("\n选项:")
        print("  start          启动模拟交易")
        print("  start --live   启动实盘交易")
        print("  stop           停止引擎")
        print("  status         查看状态")
        print("  config         修改配置")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'start':
        live = '--live' in sys.argv
        start_engine(live)
    elif command == 'stop':
        stop_engine()
    elif command == 'status':
        show_status()
    elif command == 'config':
        update_config()
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
