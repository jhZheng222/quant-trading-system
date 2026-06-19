#!/usr/bin/env python3
"""
量化交易系统 - 交易通知脚本
当有交易信号时发送钉钉通知
"""

import sys
import os
import json
import requests
from datetime import datetime
from loguru import logger

sys.path.insert(0, os.path.dirname(__file__))


def send_dingtalk_message(title: str, content: str):
    """发送钉钉消息"""
    # 使用 Hermes 的 send_message 功能
    # 这里简化为打印日志，实际由 cronjob 处理
    logger.info(f"📢 {title}: {content}")


def check_and_notify():
    """检查交易状态并通知"""
    log_file = "logs/live_test.log"
    
    if not os.path.exists(log_file):
        return
    
    # 读取最近的日志
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    # 检查是否有新的交易信号
    recent_lines = lines[-50:] if len(lines) > 50 else lines
    
    for line in recent_lines:
        if "📈 开仓" in line or "📉 平仓" in line or "📈 加仓" in line:
            # 提取交易信息
            logger.info(f"🔔 交易信号: {line.strip()}")
            return True
    
    return False


def main():
    """主函数"""
    logger.info("📊 检查量化交易状态...")
    
    # 检查引擎状态
    pid_file = "data/live_test.pid"
    if os.path.exists(pid_file):
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        try:
            os.kill(pid, 0)
            logger.info(f"✅ 引擎运行中 (PID: {pid})")
        except:
            logger.warning("⚠️ 引擎未运行")
            return
    else:
        logger.warning("⚠️ 未找到PID文件")
        return
    
    # 检查交易日志
    if check_and_notify():
        logger.info("📢 发现新交易信号！")
    else:
        logger.info("📊 暂无新交易信号")


if __name__ == "__main__":
    main()
