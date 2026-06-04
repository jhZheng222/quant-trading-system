#!/bin/bash
# 量化交易系统停止脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# PID文件目录
PID_DIR="$PROJECT_DIR/pids"

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

# 停止服务
stop_service() {
    local service=$1
    local pid_file="$PID_DIR/${service}.pid"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            print_info "停止 $service (PID: $pid)..."
            kill $pid
            sleep 1
            
            # 检查是否已停止
            if ps -p $pid > /dev/null 2>&1; then
                print_warn "$service 未响应，强制终止..."
                kill -9 $pid
            fi
            
            print_info "$service 已停止"
        else
            print_warn "$service 未运行"
        fi
        
        rm -f "$pid_file"
    else
        print_warn "$service PID文件不存在"
    fi
}

# 主函数
main() {
    print_info "=========================================="
    print_info "量化交易系统停止"
    print_info "=========================================="
    
    # 停止服务（按依赖顺序反序停止）
    stop_service "monitor_dashboard"
    stop_service "trade_executor"
    stop_service "strategy_engine"
    stop_service "data_collector"
    
    print_info "=========================================="
    print_info "所有服务已停止"
    print_info "=========================================="
}

# 执行主函数
main