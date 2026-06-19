#!/bin/bash
# 量化交易系统 v3.0 管理脚本

cd /Users/zhengxiaoyu/quant-trading-system
source venv/bin/activate

case "$1" in
    start)
        echo "🚀 启动量化交易系统..."
        mkdir -p logs data
        nohup python run_live.py > logs/live_test.log 2>&1 &
        echo $! > data/live_test.pid
        sleep 2
        if ps -p $(cat data/live_test.pid) > /dev/null 2>&1; then
            echo "✅ 已启动 (PID: $(cat data/live_test.pid))"
        else
            echo "❌ 启动失败，查看日志: bash manage.sh logs"
        fi
        ;;
    stop)
        if [ -f data/live_test.pid ]; then
            PID=$(cat data/live_test.pid)
            if ps -p $PID > /dev/null 2>&1; then
                kill $PID
                echo "✅ 已停止 (PID: $PID)"
            else
                echo "⚠️ 进程不存在"
            fi
            rm -f data/live_test.pid
        else
            echo "⚠️ 未找到PID文件"
        fi
        ;;
    status)
        if [ -f data/live_test.pid ]; then
            PID=$(cat data/live_test.pid)
            if ps -p $PID > /dev/null 2>&1; then
                echo "✅ 运行中 (PID: $PID)"
                echo ""
                echo "📊 最近日志:"
                tail -20 logs/live_test.log
            else
                echo "⚠️ 进程已退出"
            fi
        else
            echo "⚠️ 未运行"
        fi
        ;;
    logs)
        tail -50 logs/live_test.log
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    *)
        echo "用法: $0 {start|stop|status|logs|restart}"
        exit 1
        ;;
esac
