#!/bin/bash
# 检查并发送飞书通知

NOTIFICATION_DIR="/Users/zhengxiaoyu/quant-trading-system/data/notifications"

# 检查目录是否存在
if [ ! -d "$NOTIFICATION_DIR" ]; then
    exit 0
fi

# 查看待发送的通知
PENDING_FILES=$(ls "$NOTIFICATION_DIR"/pending_*.txt 2>/dev/null)

if [ -z "$PENDING_FILES" ]; then
    exit 0
fi

# 输出通知内容（由Hermes发送）
for file in $PENDING_FILES; do
    if [ -f "$file" ]; then
        cat "$file"
        echo "---FILE_END---"
        # 重命名为已发送
        mv "$file" "${file%.txt}.sent"
    fi
done