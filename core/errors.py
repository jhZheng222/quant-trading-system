#!/usr/bin/env python3
"""
量化交易系统 — 统一错误码
==========================

所有模块使用统一错误码，按模块划分区间：
- 1xxx: 数据层
- 2xxx: 策略层
- 3xxx: 执行层
- 4xxx: 风控层
- 5xxx: 通知/监控
- 9xxx: 系统级
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TradingError(Exception):
    """交易系统异常基类"""
    code: int
    message: str
    details: Optional[dict] = None
    
    def __str__(self):
        if self.details:
            return f"[{self.code}] {self.message} | {self.details}"
        return f"[{self.code}] {self.message}"


# ===== 数据层 (1xxx) =====
class DataFetchError(TradingError):
    """数据获取失败"""
    def __init__(self, symbol: str = None, detail: str = None):
        super().__init__(1001, f"数据获取失败: {symbol}", {"symbol": symbol, "detail": detail})


class WebSocketDisconnected(TradingError):
    """WebSocket 断开"""
    def __init__(self, symbol: str = None):
        super().__init__(1002, f"WebSocket 断开: {symbol}", {"symbol": symbol})


class DataParseError(TradingError):
    """数据解析失败"""
    def __init__(self, source: str = None):
        super().__init__(1003, f"数据解析失败: {source}", {"source": source})


# ===== 策略层 (2xxx) =====
class StrategyNotFound(TradingError):
    """策略不存在"""
    def __init__(self, name: str = None):
        super().__init__(2001, f"策略不存在: {name}", {"name": name})


class InsufficientData(TradingError):
    """数据不足以执行策略"""
    def __init__(self, strategy: str = None, required: int = None, actual: int = None):
        super().__init__(2002, f"数据不足: {strategy}", {"strategy": strategy, "required": required, "actual": actual})


class SignalGenerationError(TradingError):
    """信号生成异常"""
    def __init__(self, strategy: str = None, reason: str = None):
        super().__init__(2003, f"信号生成异常: {strategy}", {"strategy": strategy, "reason": reason})


# ===== 执行层 (3xxx) =====
class OrderFailed(TradingError):
    """下单失败"""
    def __init__(self, symbol: str = None, reason: str = None):
        super().__init__(3001, f"下单失败: {symbol}", {"symbol": symbol, "reason": reason})


class InsufficientBalance(TradingError):
    """余额不足"""
    def __init__(self, required: float = None, available: float = None):
        super().__init__(3002, "余额不足", {"required": required, "available": available})


class ExchangeError(TradingError):
    """交易所接口异常"""
    def __init__(self, exchange: str = None, method: str = None, detail: str = None):
        super().__init__(3003, f"交易所异常: {exchange}.{method}", {"exchange": exchange, "method": method, "detail": detail})


# ===== 风控层 (4xxx) =====
class RiskLimitExceeded(TradingError):
    """风控限制"""
    def __init__(self, rule: str = None, value: float = None, limit: float = None):
        super().__init__(4001, f"风控限制: {rule}", {"rule": rule, "value": value, "limit": limit})


class DailyLossHit(TradingError):
    """当日亏损已达上限"""
    def __init__(self, loss: float = None, limit: float = None):
        super().__init__(4002, "当日亏损已达上限", {"loss": loss, "limit": limit})


class PositionLimitExceeded(TradingError):
    """持仓数量超限"""
    def __init__(self, current: int = None, limit: int = None):
        super().__init__(4003, "持仓数量超限", {"current": current, "limit": limit})


# ===== 通知/监控 (5xxx) =====
class NotificationFailed(TradingError):
    """通知发送失败"""
    def __init__(self, channel: str = None, reason: str = None):
        super().__init__(5001, f"通知发送失败: {channel}", {"channel": channel, "reason": reason})


class MonitorError(TradingError):
    """监控异常"""
    def __init__(self, module: str = None, detail: str = None):
        super().__init__(5002, f"监控异常: {module}", {"module": module, "detail": detail})


# ===== 系统级 (9xxx) =====
class ConfigError(TradingError):
    """配置错误"""
    def __init__(self, key: str = None, reason: str = None):
        super().__init__(9001, f"配置错误: {key}", {"key": key, "reason": reason})


# 错误码汇总
ERROR_CODES = {
    1001: "数据获取失败",
    1002: "WebSocket 断开",
    1003: "数据解析失败",
    2001: "策略不存在",
    2002: "数据不足以执行策略",
    2003: "信号生成异常",
    3001: "下单失败",
    3002: "余额不足",
    3003: "交易所接口异常",
    4001: "风控限制",
    4002: "当日亏损已达上限",
    4003: "持仓数量超限",
    5001: "通知发送失败",
    5002: "监控异常",
    9001: "配置错误",
}
