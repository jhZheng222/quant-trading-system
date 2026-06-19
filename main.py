#!/usr/bin/env python3
"""
quant-trading-system — 量化交易系统
====================================

唯一入口。所有操作通过子命令执行。

用法:
    python main.py start              # 启动交易引擎
    python main.py stop               # 停止交易引擎
    python main.py status             # 查看系统状态
    python main.py positions          # 查看持仓
    python main.py history            # 查看交易历史
    python main.py backtest           # 运行回测
    python main.py simulate           # 模拟交易
    python main.py cli                # 交互式 CLI（旧版）
"""

import sys
import os
import argparse
from pathlib import Path

# 确保项目根目录在 sys.path 中
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from loguru import logger
from config.settings import log_config


def setup_logging():
    """配置日志"""
    log_dir = Path(log_config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "trading_{time:YYYY-MM-DD}.log",
        rotation=log_config.log_rotation,
        retention=log_config.log_retention,
        compression=log_config.log_compression,
        level=log_config.log_level,
    )


def cmd_start(args):
    """启动交易引擎"""
    from core.engine.livermore_engine import LivermoreEngine
    
    sandbox = not args.live
    if sandbox:
        print("🟡 启动模拟盘交易...")
    else:
        print("🔴 启动实盘交易（请注意风险！）...")
    
    engine = LivermoreEngine(sandbox=sandbox)
    engine.start()


def cmd_stop(args):
    """停止交易引擎"""
    print("停止功能待实现")
    # from scripts.live.stop_trading import stop_engine
    # stop_engine()


def cmd_status(args):
    """查看系统状态"""
    print("📊 量化交易系统状态")
    print("=" * 40)
    
    # 检查 PID 文件
    pid_files = list(Path("data").glob("*.pid"))
    if pid_files:
        for pf in pid_files:
            pid = pf.read_text().strip()
            print(f"  ✅ {pf.stem} 运行中 (PID: {pid})")
    else:
        print("  ⚪ 无运行中的交易引擎")
    
    print(f"  根目录: {BASE_DIR}")
    
    # 检查数据库
    db_path = BASE_DIR / "data" / "trading.db"
    if db_path.exists():
        size = db_path.stat().st_size / 1024
        print(f"  数据库: trading.db ({size:.0f} KB)")
    
    # 显示配置文件状态
    env_path = BASE_DIR / ".env"
    print(f"  环境变量: {'✅ 已配置' if env_path.exists() else '❌ 未配置'}")
    
    print("=" * 40)


def cmd_positions(args):
    """查看持仓"""
    from cli import main as cli_main
    sys.argv = ["cli.py", "positions"]
    if args.live:
        sys.argv.append("--live")
    cli_main()


def cmd_history(args):
    """查看交易历史"""
    from cli import main as cli_main
    sys.argv = ["cli.py", "history"]
    cli_main()


def cmd_backtest(args):
    """运行回测"""
    print("回测功能待整合")
    # from scripts.backtest.run_backtest import run
    # run(strategy=args.strategy, symbol=args.symbol)


def cmd_simulate(args):
    """运行模拟交易"""
    print("模拟交易功能待整合")
    # from scripts.simulate import run_simulation
    # run_simulation()


def main():
    """主入口"""
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description="quant-trading-system — 量化交易系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py start              # 启动模拟盘交易
  python main.py start --live       # 启动实盘交易
  python main.py stop               # 停止交易
  python main.py status             # 查看状态
  python main.py positions          # 查看持仓
  python main.py history            # 查看历史交易
  python main.py backtest           # 运行回测
  python main.py backtest --strategy livermore --symbol DOGEUSDT
        """,
    )
    
    sub = parser.add_subparsers(dest="command", help="子命令")
    
    # start
    p_start = sub.add_parser("start", help="启动交易引擎")
    p_start.add_argument("--live", action="store_true", help="实盘模式（默认模拟盘）")
    p_start.set_defaults(func=cmd_start)
    
    # stop
    p_stop = sub.add_parser("stop", help="停止交易引擎")
    p_stop.set_defaults(func=cmd_stop)
    
    # status
    p_status = sub.add_parser("status", help="查看系统状态")
    p_status.set_defaults(func=cmd_status)
    
    # positions
    p_pos = sub.add_parser("positions", help="查看持仓")
    p_pos.add_argument("--live", action="store_true", help="实时盈亏")
    p_pos.set_defaults(func=cmd_positions)
    
    # history
    p_hist = sub.add_parser("history", help="查看交易历史")
    p_hist.set_defaults(func=cmd_history)
    
    # backtest
    p_bt = sub.add_parser("backtest", help="运行回测")
    p_bt.add_argument("--strategy", default="livermore", help="策略名称")
    p_bt.add_argument("--symbol", default="DOGEUSDT", help="交易对")
    p_bt.set_defaults(func=cmd_backtest)
    
    # simulate
    p_sim = sub.add_parser("simulate", help="运行模拟交易")
    p_sim.set_defaults(func=cmd_simulate)
    
    # cli (旧版入口)
    p_cli = sub.add_parser("cli", help="旧版交互式 CLI")
    def run_cli(a):
        with open("cli.py") as f:
            exec(f.read())
    p_cli.set_defaults(func=run_cli)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
