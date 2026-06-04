#!/bin/bash
# 量化交易系统状态检查脚本

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

# 日志目录
LOG_DIR="$PROJECT_DIR/logs"

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

# 检查服务状态
check_service() {
    local service=$1
    local pid_file="$PID_DIR/${service}.pid"
    local log_file="$LOG_DIR/${service}.log"
    
    echo -n "  $service: "
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${GREEN}运行中${NC} (PID: $pid)"
            
            # 显示资源使用
            ps -p $pid -o %cpu,%mem,etime | tail -1 | awk '{printf "    CPU: %s, 内存: %s, 运行时间: %s\n", $1, $2, $3}'
            
            # 显示最后日志
            if [ -f "$log_file" ]; then
                echo "    最近日志:"
                tail -3 "$log_file" | sed 's/^/      /'
            fi
        else
            echo -e "${RED}已停止${NC} (PID文件存在但进程不存在)"
        fi
    else
        echo -e "${YELLOW}未启动${NC}"
    fi
}

# 检查系统资源
check_system_resources() {
    echo ""
    print_info "系统资源:"
    echo "----------------------------------------"
    
    # CPU使用率
    cpu_usage=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
    echo -n "  CPU使用率: "
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        echo -e "${RED}${cpu_usage}%${NC}"
    elif (( $(echo "$cpu_usage > 60" | bc -l) )); then
        echo -e "${YELLOW}${cpu_usage}%${NC}"
    else
        echo -e "${GREEN}${cpu_usage}%${NC}"
    fi
    
    # 内存使用率
    memory_pressure=$(memory_pressure | grep "System-wide memory free percentage" | awk '{print $5}' | sed 's/%//')
    memory_usage=$((100 - memory_pressure))
    echo -n "  内存使用率: "
    if [ $memory_usage -gt 85 ]; then
        echo -e "${RED}${memory_usage}%${NC}"
    elif [ $memory_usage -gt 70 ]; then
        echo -e "${YELLOW}${memory_usage}%${NC}"
    else
        echo -e "${GREEN}${memory_usage}%${NC}"
    fi
    
    # 磁盘使用率
    disk_usage=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
    echo -n "  磁盘使用率: "
    if [ $disk_usage -gt 90 ]; then
        echo -e "${RED}${disk_usage}%${NC}"
    elif [ $disk_usage -gt 80 ]; then
        echo -e "${YELLOW}${disk_usage}%${NC}"
    else
        echo -e "${GREEN}${disk_usage}%${NC}"
    fi
    
    echo "----------------------------------------"
}

# 检查数据库
check_database() {
    echo ""
    print_info "数据库状态:"
    echo "----------------------------------------"
    
    db_file="$PROJECT_DIR/data/trading.db"
    if [ -f "$db_file" ]; then
        db_size=$(du -h "$db_file" | awk '{print $1}')
        echo "  数据库文件: $db_size"
        
        # 检查表数量
        table_count=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "N/A")
        echo "  表数量: $table_count"
        
        # 检查数据量
        echo "  数据统计:"
        for table in kline funding_rate open_interest trade_signals orders; do
            count=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "0")
            echo "    $table: $count 条记录"
        done
    else
        echo -e "  ${YELLOW}数据库文件不存在${NC}"
    fi
    
    echo "----------------------------------------"
}

# 检查网络连接
check_network() {
    echo ""
    print_info "网络连接:"
    echo "----------------------------------------"
    
    # 检查OKX API
    echo -n "  OKX API: "
    if curl -s --connect-timeout 5 "https://www.okx.com/api/v5/public/time" > /dev/null; then
        echo -e "${GREEN}正常${NC}"
    else
        echo -e "${RED}无法连接${NC}"
    fi
    
    # 检查WebSocket
    echo -n "  OKX WebSocket: "
    if curl -s --connect-timeout 5 "wss://ws.okx.com:8443/ws/v5/public" > /dev/null 2>&1; then
        echo -e "${GREEN}正常${NC}"
    else
        echo -e "${YELLOW}需要测试${NC}"
    fi
    
    echo "----------------------------------------"
}

# 主函数
main() {
    echo ""
    print_info "=========================================="
    print_info "量化交易系统状态检查"
    print_info "=========================================="
    echo ""
    
    # 检查服务状态
    print_info "服务状态:"
    echo "----------------------------------------"
    check_service "data_collector"
    check_service "strategy_engine"
    check_service "trade_executor"
    check_service "monitor_dashboard"
    echo "----------------------------------------"
    
    # 检查系统资源
    check_system_resources
    
    # 检查数据库
    check_database
    
    # 检查网络
    check_network
    
    echo ""
    print_info "=========================================="
}

# 执行主函数
main