#!/bin/bash
# 实时交易引擎管理脚本

PLIST_NAME="com.quant.realtime"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
PROJECT_DIR="/Users/zhengxiaoyu/quant-trading-system"

case "$1" in
    start)
        echo "启动实时交易引擎..."
        launchctl start "$PLIST_NAME"
        sleep 2
        launchctl list | grep "$PLIST_NAME"
        ;;
    stop)
        echo "停止实时交易引擎..."
        launchctl stop "$PLIST_NAME"
        ;;
    restart)
        echo "重启实时交易引擎..."
        launchctl stop "$PLIST_NAME"
        sleep 2
        launchctl start "$PLIST_NAME"
        sleep 2
        launchctl list | grep "$PLIST_NAME"
        ;;
    status)
        echo "=== 服务状态 ==="
        launchctl list | grep "$PLIST_NAME" || echo "服务未加载"
        echo ""
        echo "=== 进程状态 ==="
        ps aux | grep realtime.py | grep -v grep || echo "进程未运行"
        echo ""
        echo "=== 最新日志 ==="
        tail -5 "$PROJECT_DIR/logs/launchd_stderr.log" 2>/dev/null || echo "无日志文件"
        ;;
    logs)
        echo "=== 标准输出日志 ==="
        tail -20 "$PROJECT_DIR/logs/launchd_stdout.log" 2>/dev/null || echo "无日志文件"
        echo ""
        echo "=== 错误日志 ==="
        tail -20 "$PROJECT_DIR/logs/launchd_stderr.log" 2>/dev/null || echo "无日志文件"
        ;;
    unload)
        echo "卸载服务..."
        launchctl unload "$PLIST_PATH"
        ;;
    load)
        echo "加载服务..."
        launchctl load "$PLIST_PATH"
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs|load|unload}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动服务"
        echo "  stop    - 停止服务"
        echo "  restart - 重启服务"
        echo "  status  - 查看状态"
        echo "  logs    - 查看日志"
        echo "  load    - 加载服务（开机自启）"
        echo "  unload  - 卸载服务（取消开机自启）"
        exit 1
        ;;
esac