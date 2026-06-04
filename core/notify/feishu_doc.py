"""
飞书文档记录模块
将交易记录写入飞书智能文档
"""
import requests
import json
from datetime import datetime
from typing import Dict, Optional
from loguru import logger
import os


class FeishuDocWriter:
    """飞书文档写入器"""
    
    def __init__(self, doc_token: str = None, webhook_url: str = None):
        """初始化飞书文档写入器
        
        Args:
            doc_token: 飞书文档token
            webhook_url: 飞书机器人webhook URL
        """
        self.doc_token = doc_token
        self.webhook_url = webhook_url or os.getenv('FEISHU_WEBHOOK', '')
        
        logger.info("飞书文档写入器初始化完成")
    
    def format_trade_message(self, trade: Dict) -> str:
        """格式化交易消息
        
        Args:
            trade: 交易数据
            
        Returns:
            格式化的消息
        """
        symbol = trade.get('symbol', 'UNKNOWN')
        side = trade.get('side', 'unknown')
        entry_price = trade.get('entry_price', 0)
        exit_price = trade.get('exit_price', 0)
        pnl = trade.get('pnl', 0)
        pnl_pct = trade.get('pnl_pct', 0)
        reason = trade.get('reason', '未知')
        timestamp = trade.get('exit_time', trade.get('entry_time', datetime.now().isoformat()))
        
        # 价格格式化
        def format_price(price):
            if price < 0.0001:
                return f"${price:.10f}"
            elif price < 0.01:
                return f"${price:.8f}"
            elif price < 1:
                return f"${price:.6f}"
            else:
                return f"${price:.4f}"
        
        # 盈亏符号
        pnl_sign = "+" if pnl >= 0 else ""
        emoji = "🟢" if pnl >= 0 else "🔴"
        
        # 方向
        side_cn = "买入" if side == "buy" else "卖出"
        
        message = f"""
{emoji} **模拟交易记录**

**时间**: {timestamp[:19]}
**币种**: {symbol}
**方向**: {side_cn}
**入场价**: {format_price(entry_price)}
**出场价**: {format_price(exit_price)}
**盈亏**: {pnl_sign}{pnl:.4f}U ({pnl_sign}{pnl_pct:.2f}%)
**原因**: {reason}
"""
        return message.strip()
    
    def send_to_webhook(self, message: str) -> bool:
        """通过webhook发送到飞书
        
        Args:
            message: 消息内容
            
        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            logger.warning("飞书webhook未配置")
            return False
        
        try:
            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "📊 量化交易系统 - 交易记录"
                        },
                        "template": "blue"
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": message
                        }
                    ]
                }
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    logger.info("飞书消息发送成功")
                    return True
                else:
                    logger.error(f"飞书消息发送失败: {result}")
                    return False
            else:
                logger.error(f"飞书消息发送失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"飞书消息发送异常: {e}")
            return False
    
    def record_trade(self, trade: Dict) -> bool:
        """记录交易到飞书
        
        Args:
            trade: 交易数据
            
        Returns:
            是否记录成功
        """
        message = self.format_trade_message(trade)
        
        # 发送到飞书
        success = self.send_to_webhook(message)
        
        if success:
            logger.info(f"交易已记录到飞书: {trade.get('symbol')} {trade.get('side')}")
        else:
            logger.warning(f"飞书记录失败，交易数据: {trade}")
        
        return success
    
    def record_daily_summary(self, account: Dict) -> bool:
        """记录每日总结到飞书
        
        Args:
            account: 账户数据
            
        Returns:
            是否记录成功
        """
        balance = account.get('balance', 0)
        total_pnl = account.get('total_pnl', 0)
        total_trades = account.get('total_trades', 0)
        win_rate = account.get('win_rate', 0)
        
        pnl_sign = "+" if total_pnl >= 0 else ""
        emoji = "📈" if total_pnl >= 0 else "📉"
        
        message = f"""
{emoji} **每日交易总结**

**日期**: {datetime.now().strftime('%Y-%m-%d')}
**当前余额**: {balance:.4f}U
**总盈亏**: {pnl_sign}{total_pnl:.4f}U
**总交易**: {total_trades} 笔
**胜率**: {win_rate:.1f}%
"""
        return self.send_to_webhook(message.strip())


# 使用示例
if __name__ == '__main__':
    writer = FeishuDocWriter()
    
    # 测试交易记录
    test_trade = {
        'symbol': 'DOGEUSDT',
        'side': 'buy',
        'entry_price': 0.101,
        'exit_price': 0.107,
        'pnl': 0.3,
        'pnl_pct': 5.94,
        'reason': '止盈',
        'exit_time': datetime.now().isoformat()
    }
    
    print("格式化消息:")
    print(writer.format_trade_message(test_trade))