#!/usr/bin/env python3
"""
利弗莫尔策略 — 一周实盘测试
============================

用生产数据持续运行，记录每笔交易和每日表现。
测试期：2026-06-01 ~ 2026-06-08

数据存储：
- data/livermore_weekly.db  — 交易和快照
- logs/livermore_weekly.log — 运行日志
"""

import sys
import json
from datetime import datetime
from loguru import logger

from core.simulation.engine_livermore_v2 import LivermoreEngineV2
from core.storage.sqlite_storage import SQLiteStorage


# 配置
INITIAL_BALANCE = 10.0  # 10U
SYMBOLS = ['DOGEUSDT', 'PEPEUSDT']
DB_PATH = "data/livermore_weekly.db"


def setup_logging():
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
    logger.add("logs/livermore_weekly.log", rotation="1 day", retention="10 days", level="DEBUG")


def run_cycle(engine: LivermoreEngineV2):
    """运行一个分析周期"""
    now = datetime.now()
    logger.info(f"{'='*40}")
    logger.info(f"⏰ 分析周期: {now.strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"{'='*40}")
    
    engine.run_once(SYMBOLS)


def generate_daily_report(engine: LivermoreEngineV2) -> str:
    """生成每日报告"""
    now = datetime.now()
    
    # 计算总价值
    total_value = engine.balance
    if engine.strategy:
        for pos in engine.strategy.positions.values():
            from core.strategy.livermore import LivermoreStage
            if pos.stage not in [LivermoreStage.EMPTY, LivermoreStage.STOPPED]:
                total_value += pos.total_cost
    
    pnl = total_value - engine.initial_balance
    pnl_pct = pnl / engine.initial_balance * 100
    
    # 表现指标
    perf = engine.optimizer.calc_performance(engine.trade_history)
    
    report = f"""
# 📊 利弗莫尔策略每日报告
**日期**: {now.strftime('%Y-%m-%d %H:%M')}
**测试天数**: 第{(now - datetime(2026, 6, 1)).days + 1}天/7天

## 💰 账户状态
| 指标 | 数值 |
|------|------|
| 初始资金 | {engine.initial_balance:.4f} U |
| 当前余额 | {engine.balance:.4f} U |
| 总价值 | {total_value:.4f} U |
| 总盈亏 | {pnl:+.4f} U ({pnl_pct:+.2f}%) |

## 📈 交易统计
| 指标 | 数值 |
|------|------|
| 总交易 | {engine.strategy.total_trades if engine.strategy else 0} |
| 胜率 | {perf.win_rate*100:.0f}% |
| 利润因子 | {perf.profit_factor:.2f} |
| 最大回撤 | {perf.max_drawdown*100:.1f}% |
| 连续亏损 | {perf.consecutive_losses}次 |

## 📊 持仓明细
{engine.strategy.get_position_summary() if engine.strategy else '无持仓'}

## 🧠 市场状态
当前自适应参数基于最近一次市场检测。
"""
    return report


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='利弗莫尔一周实盘测试')
    parser.add_argument('--once', action='store_true', help='运行一次')
    parser.add_argument('--report', action='store_true', help='生成每日报告')
    parser.add_argument('--status', action='store_true', help='查看当前状态')
    args = parser.parse_args()
    
    setup_logging()
    
    engine = LivermoreEngineV2(initial_balance=INITIAL_BALANCE, db_path=DB_PATH)
    
    if args.status:
        print(engine.get_report())
        return
    
    if args.report:
        report = generate_daily_report(engine)
        print(report)
        # 保存报告
        report_path = f"reports/livermore_{datetime.now().strftime('%Y%m%d')}.md"
        import os
        os.makedirs("reports", exist_ok=True)
        with open(report_path, 'w') as f:
            f.write(report)
        logger.info(f"报告已保存: {report_path}")
        return
    
    # 运行一次分析
    run_cycle(engine)


if __name__ == '__main__':
    main()
