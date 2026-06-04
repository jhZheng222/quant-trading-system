#!/bin/bash
# 实时交易引擎启动脚本
# 用于launchd服务管理

set -e

# 项目目录
PROJECT_DIR="/Users/zhengxiaoyu/quant-trading-system"
cd "$PROJECT_DIR"

# 激活虚拟环境
source venv/bin/activate

# 创建logs目录（如果不存在）
mkdir -p logs

# 启动参数
SYMBOLS="${1:-DOGEUSDT,PEPEUSDT}"
INTERVAL="${2:-1h}"

echo "$(date): 启动实时交易引擎..."
echo "交易对: $SYMBOLS"
echo "周期: $INTERVAL"

# 启动实时引擎
exec python realtime.py --symbols "$SYMBOLS" --interval "$INTERVAL"