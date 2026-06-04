"""
飞书通知模块
使用Hermes send_message发送交易通知
"""
from datetime import datetime
from typing import Dict
from loguru import logger


class FeishuNotifier:
    """飞书通知器"""
    
    def __init__(self):
        """初始化通知器"""
        logger.info("飞书通知器初始化完成")
    
    def format_trade_message(self, trade: Dict) -> str:
        """格式化交易消息"""
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
        
        message = f"""{emoji} **模拟交易记录**

**时间**: {timestamp[:19]}
**币种**: {symbol}
**方向**: {side_cn}
**入场价**: {format_price(entry_price)}
**出场价**: {format_price(exit_price)}
**盈亏**: {pnl_sign}{pnl:.4f}U ({pnl_sign}{pnl_pct:.2f}%)
**原因**: {reason}"""
        
        return message.strip()
    
    def format_daily_summary(self, account: Dict) -> str:
        """格式化每日总结"""
        balance = account.get('balance', 0)
        total_pnl = account.get('total_pnl', 0)
        total_trades = account.get('total_trades', 0)
        win_rate = account.get('win_rate', 0)
        
        pnl_sign = "+" if total_pnl >= 0 else ""
        emoji = "📈" if total_pnl >= 0 else "📉"
        
        message = f"""{emoji} **每日交易总结**

**日期**: {datetime.now().strftime('%Y-%m-%d')}
**当前余额**: {balance:.4f}U
**总盈亏**: {pnl_sign}{total_pnl:.4f}U
**总交易**: {total_trades} 笔
**胜率**: {win_rate:.1f}%"""
        
        return message.strip()


# 全局实例
notifier = FeishuNotifier()