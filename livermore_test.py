#!/usr/bin/env python3
"""
量化交易系统 — 通用测试脚本
============================

所有策略共用，参数从 test_config.json 读取。

用法：
    python livermore_test.py                    # 运行一次分析
    python livermore_test.py --report           # 生成报告
    python livermore_test.py --status           # 查看状态
    python livermore_test.py --config           # 查看当前配置
    python livermore_test.py --set balance 20   # 修改参数
    python livermore_test.py --set leverage 20
    python livermore_test.py --set symbols DOGEUSDT,PEPEUSDT,SHIBUSDT
    python livermore_test.py --set end_date 2026-06-15
    python livermore_test.py --reset            # 重置测试
"""

import sys
import os
import json
import argparse
from datetime import datetime
from loguru import logger

# 确保项目路径在sys.path中
sys.path.insert(0, os.path.dirname(__file__))

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "test_config.json")
DB_DIR = os.path.join(os.path.dirname(__file__), "data")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")

# 策略注册表
STRATEGIES = {
    'livermore': 'core.engine.livermore_engine.LivermoreEngine',
}


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        config = {
            "test_name": "量化交易测试",
            "test_id": "quant_test",
            "initial_balance": 10.0,
            "symbols": ["DOGEUSDT", "PEPEUSDT"],
            "leverage": 10,
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "end_date": "",
            "interval_minutes": 60,
            "daily_report_hour": 22,
            "strategy": "livermore",
            "adaptive": True,
            "notes": ""
        }
        save_config(config)
        return config
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def save_config(config: dict):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_db_path(config: dict) -> str:
    os.makedirs(DB_DIR, exist_ok=True)
    return os.path.join(DB_DIR, f"{config['test_id']}.db")


def setup_logging(config: dict):
    os.makedirs(LOG_DIR, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
    logger.add(os.path.join(LOG_DIR, f"{config['test_id']}.log"),
               rotation="1 day", retention="10 days", level="DEBUG")


def create_engine(config: dict):
    """根据配置创建引擎实例"""
    strategy_name = config.get('strategy', 'livermore')
    strategy_path = STRATEGIES.get(strategy_name)
    if not strategy_path:
        logger.error(f"未知策略: {strategy_name}，可用: {list(STRATEGIES.keys())}")
        sys.exit(1)

    # 动态导入
    module_path, class_name = strategy_path.rsplit('.', 1)
    import importlib
    module = importlib.import_module(module_path)
    engine_class = getattr(module, class_name)

    db_path = get_db_path(config)
    return engine_class(
        initial_balance=config['initial_balance'],
        db_path=db_path,
        config=config
    )


def check_test_period(config: dict) -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    if config.get("start_date") and today < config["start_date"]:
        logger.info(f"测试尚未开始（开始日期: {config['start_date']}）")
        return False
    if config.get("end_date") and today > config["end_date"]:
        logger.info(f"测试已结束（结束日期: {config['end_date']}）")
        return False
    return True


def run_analysis(config: dict):
    if not check_test_period(config):
        return

    engine = create_engine(config)
    symbols = config['symbols']
    now = datetime.now()

    logger.info(f"{'='*40}")
    logger.info(f"⏰ {config['test_name']} | {now.strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"   策略: {config['strategy']} | 交易对: {', '.join(symbols)} | 杠杆: {config['leverage']}x")
    logger.info(f"{'='*40}")

    engine.run_once(symbols)


def generate_report(config: dict) -> str:
    engine = create_engine(config)
    now = datetime.now()
    start = datetime.strptime(config["start_date"], "%Y-%m-%d")
    test_day = (now - start).days + 1

    total_days = "?"
    if config.get("end_date"):
        end = datetime.strptime(config["end_date"], "%Y-%m-%d")
        total_days = (end - start).days + 1

    total_value = engine.balance
    for pos in engine.positions.values():
        if pos.stage not in ['empty', 'stopped']:
            total_value += pos.cost

    pnl = total_value - engine.initial_balance
    pnl_pct = pnl / engine.initial_balance * 100

    win_rate = engine.winning_trades / max(1, engine.total_trades) * 100

    # 持仓明细
    pos_lines = []
    for sym, pos in engine.positions.items():
        if pos.stage not in ['empty', 'stopped']:
            pos_lines.append(f"| {sym} | {pos.side} | {pos.strategy} | {pos.avg_price:.6f} | {pos.stop_loss:.6f} |")
    pos_table = "\n".join(pos_lines) if pos_lines else "| 无 | - | - | - | - |"

    report = f"""# 📊 {config['test_name']} — 每日报告

**日期**: {now.strftime('%Y-%m-%d %H:%M')}
**测试进度**: 第{test_day}天/{total_days}天
**策略**: {config['strategy']}

## ⚙️ 测试配置
| 参数 | 值 |
|------|-----|
| 初始资金 | {config['initial_balance']} U |
| 交易对 | {', '.join(config['symbols'])} |
| 杠杆 | {config['leverage']}x |
| 自适应 | {'是' if config.get('adaptive') else '否'} |

## 💰 账户状态
| 指标 | 数值 |
|------|------|
| 当前余额 | {engine.balance:.4f} U |
| 总价值 | {total_value:.4f} U |
| 总盈亏 | {pnl:+.4f} U ({pnl_pct:+.2f}%) |

## 📈 交易统计
| 指标 | 数值 |
|------|------|
| 总交易 | {engine.total_trades} |
| 胜率 | {win_rate:.0f}% |
| 总盈亏 | {engine.total_pnl:+.4f} U |

## 📊 当前持仓
| 交易对 | 方向 | 策略 | 均价 | 止损 |
|--------|------|------|------|------|
{pos_table}

---
*配置: {CONFIG_PATH}*
*数据库: {get_db_path(config)}*
"""

    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, f"{config['test_id']}_{now.strftime('%Y%m%d')}.md")
    with open(report_path, 'w') as f:
        f.write(report)

    logger.info(f"报告已保存: {report_path}")
    return report


def show_status(config: dict):
    engine = create_engine(config)
    engine.print_report()


def show_config(config: dict):
    print(f"\n📋 当前配置: {config.get('test_name', '未命名')}")
    print("=" * 40)
    for k, v in config.items():
        if k != "notes":
            print(f"  {k}: {v}")
    print("=" * 40)
    print(f"\n💡 修改: python {os.path.basename(__file__)} --set <参数> <值>")
    print(f"📋 可用策略: {', '.join(STRATEGIES.keys())}")


def set_param(config: dict, key: str, value: str):
    if key in ("initial_balance", "leverage"):
        value = float(value) if '.' in value else int(value)
    elif key in ("interval_minutes", "daily_report_hour"):
        value = int(value)
    elif key == "adaptive":
        value = value.lower() in ("true", "1", "yes")
    elif key == "symbols":
        value = [s.strip() for s in value.split(',')]
    elif key == "strategy":
        if value not in STRATEGIES:
            print(f"❌ 未知策略: {value}")
            print(f"   可用: {', '.join(STRATEGIES.keys())}")
            return

    old = config.get(key)
    config[key] = value
    save_config(config)
    print(f"✅ {key}: {old} → {value}")


def reset_test(config: dict):
    db_path = get_db_path(config)
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✅ 数据库已删除: {db_path}")
    config["start_date"] = datetime.now().strftime("%Y-%m-%d")
    save_config(config)
    print(f"✅ 测试已重置 | 资金: {config['initial_balance']}U | 策略: {config['strategy']}")


def main():
    parser = argparse.ArgumentParser(description='量化交易系统 — 通用测试脚本')
    parser.add_argument('--run', action='store_true', default=True, help='运行一次分析')
    parser.add_argument('--report', action='store_true', help='生成每日报告')
    parser.add_argument('--status', action='store_true', help='查看当前状态')
    parser.add_argument('--config', action='store_true', help='查看当前配置')
    parser.add_argument('--set', nargs=2, metavar=('KEY', 'VALUE'), help='修改参数')
    parser.add_argument('--reset', action='store_true', help='重置测试')

    args = parser.parse_args()
    config = load_config()
    setup_logging(config)

    if args.config:
        show_config(config)
    elif args.set:
        set_param(config, args.set[0], args.set[1])
    elif args.reset:
        reset_test(config)
    elif args.status:
        show_status(config)
    elif args.report:
        report = generate_report(config)
        print(report)
    else:
        run_analysis(config)


if __name__ == '__main__':
    main()
