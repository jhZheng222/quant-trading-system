"""
量化交易系统配置
"""
import os
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/trading.db")

# Gate.io API配置
class GateConfig(BaseModel):
    """Gate.io交易所配置"""
    api_key: str = os.getenv("GATE_API_KEY", "")
    secret_key: str = os.getenv("GATE_SECRET_KEY", "")
    sandbox: bool = os.getenv("GATE_SANDBOX", "true").lower() == "true"
    
    # 实盘API端点
    production_url: str = "https://api.gateio.ws/api/v4"
    
    # 模拟盘API端点
    sandbox_url: str = "https://fx-api-testnet.gateio.ws/api/v4"
    
    # WebSocket端点
    ws_production: str = "wss://fx-ws.gateio.ws/v4/ws/usdt"
    ws_sandbox: str = "wss://fx-ws-testnet.gateio.ws/v4/ws/usdt"
    
    # 请求限制
    rate_limit: int = 10  # 每秒请求数
    timeout: int = 30     # 请求超时（秒）

# 交易配置（10U小资金版）
class TradingConfig(BaseModel):
    """交易参数配置"""
    # 交易对
    symbols: list = ["DOGE/USDT", "PEPE/USDT"]
    
    # 初始资金
    initial_capital: float = 10.0  # 10U
    
    # 杠杆设置（小资金需要高杠杆）
    leverage: dict = {
        "DOGE/USDT": 30,  # 30倍杠杆
        "PEPE/USDT": 20   # 20倍杠杆
    }
    
    # 仓位设置（小资金全仓操作）
    position_size: float = 1.0  # 100%仓位
    
    # 风控参数（严格止损）
    stop_loss_pct: float = 0.03    # 3%止损
    take_profit_pct: float = 0.06  # 6%止盈
    max_daily_loss: float = 0.30   # 单日最大亏损30%
    max_daily_trades: int = 3      # 每天最多3次交易
    
    # 手续费
    trading_fee: float = 0.0005  # 0.05%手续费

# 策略配置
class StrategyConfig(BaseModel):
    """策略参数配置"""
    # 趋势策略参数
    trend: dict = {
        "ema_short": 20,
        "ema_long": 50,
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "bb_period": 20,
        "bb_std": 2
    }
    
    # 事件策略参数
    event: dict = {
        "whale_threshold": 1000000,  # 大额转账阈值（USDT）
        "social_multiplier": 3,      # 社交热度倍数阈值
        "funding_rate_threshold": 0.001  # 资金费率异常阈值
    }
    
    # 小资金专用参数
    small_capital: dict = {
        "min_profit_target": 0.5,  # 最小盈利目标0.5U
        "max_loss_per_trade": 0.3, # 单笔最大亏损0.3U
        "quick_profit": True,      # 快进快出模式
    }

# 监控配置
class MonitorConfig(BaseModel):
    """监控报警配置"""
    # 飞书机器人
    feishu_webhook: str = os.getenv("FEISHU_WEBHOOK", "")
    
    # 企业微信机器人
    wecom_webhook: str = os.getenv("WECOM_WEBHOOK", "")
    
    # 报警阈值
    cpu_threshold: float = 80.0
    memory_threshold: float = 85.0
    disk_threshold: float = 90.0
    
    # 交易报警
    daily_loss_alert: float = 0.20  # 20%亏损预警
    leverage_alert: float = 25.0    # 杠杆预警

# 日志配置
class LogConfig(BaseModel):
    """日志配置"""
    log_dir: str = str(BASE_DIR / "logs")
    log_level: str = "INFO"
    log_rotation: str = "1 day"
    log_retention: str = "30 days"
    log_compression: str = "zip"

# 全局配置实例
gate_config = GateConfig()
trading_config = TradingConfig()
strategy_config = StrategyConfig()
monitor_config = MonitorConfig()
log_config = LogConfig()