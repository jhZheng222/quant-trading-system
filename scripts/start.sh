#!/bin/bash
# 量化交易系统启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# 日志目录
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# PID文件目录
PID_DIR="$PROJECT_DIR/pids"
mkdir -p "$PID_DIR"

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python环境
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python3未安装"
        exit 1
    fi
    
    # 检查虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
        print_info "已激活虚拟环境"
    fi
}

# 检查依赖
check_dependencies() {
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt -q
        print_info "依赖检查完成"
    fi
}

# 启动数据采集服务
start_data_collector() {
    print_info "启动数据采集服务..."
    nohup python3 -m core.data.collector > "$LOG_DIR/data_collector.log" 2>&1 &
    echo $! > "$PID_DIR/data_collector.pid"
    print_info "数据采集服务已启动 (PID: $(cat $PID_DIR/data_collector.pid))"
}

# 启动策略引擎
start_strategy_engine() {
    print_info "启动策略引擎..."
    nohup python3 -m core.strategy.engine > "$LOG_DIR/strategy_engine.log" 2>&1 &
    echo $! > "$PID_DIR/strategy_engine.pid"
    print_info "策略引擎已启动 (PID: $(cat $PID_DIR/strategy_engine.pid))"
}

# 启动交易执行服务
start_trade_executor() {
    print_info "启动交易执行服务..."
    nohup python3 -m core.exchange.executor > "$LOG_DIR/trade_executor.log" 2>&1 &
    echo $! > "$PID_DIR/trade_executor.pid"
    print_info "交易执行服务已启动 (PID: $(cat $PID_DIR/trade_executor.pid))"
}

# 启动监控面板
start_monitor_dashboard() {
    print_info "启动监控面板..."
    nohup python3 -m core.monitor.dashboard > "$LOG_DIR/monitor_dashboard.log" 2>&1 &
    echo $! > "$PID_DIR/monitor_dashboard.pid"
    print_info "监控面板已启动 (PID: $(cat $PID_DIR/monitor_dashboard.pid))"
}

# 主函数
main() {
    print_info "=========================================="
    print_info "量化交易系统启动"
    print_info "=========================================="
    
    # 检查环境
    check_python
    check_dependencies
    
    # 启动服务
    start_data_collector
    start_strategy_engine
    start_trade_executor
    start_monitor_dashboard
    
    print_info "=========================================="
    print_info "所有服务已启动"
    print_info "=========================================="
    
    # 显示服务状态
    show_status
}

# 显示服务状态
show_status() {
    echo ""
    print_info "服务状态:"
    echo "----------------------------------------"
    
    for service in data_collector strategy_engine trade_executor monitor_dashboard; do
        pid_file="$PID_DIR/${service}.pid"
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if ps -p $pid > /dev/null 2>&1; then
                echo -e "  ${GREEN}●${NC} $service (PID: $pid)"
            else
                echo -e "  ${RED}●${NC} $service (未运行)"
            fi
        else
            echo -e "  ${YELLOW}●${NC} $service (未启动)"
        fi
    done
    
    echo "----------------------------------------"
}

# 执行主函数
main