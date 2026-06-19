"""错误码系统测试"""
import pytest
from core.errors import (
    TradingError,
    DataFetchError,
    WebSocketDisconnected,
    DataParseError,
    StrategyNotFound,
    InsufficientData,
    OrderFailed,
    InsufficientBalance,
    ExchangeError,
    RiskLimitExceeded,
    DailyLossHit,
    ConfigError,
    ERROR_CODES,
)


class TestErrorCodes:
    """测试错误码定义"""

    def test_trading_error_basic(self):
        """基础异常"""
        err = TradingError(1001, "test error")
        assert err.code == 1001
        assert "test error" in str(err)

    def test_data_fetch_error(self):
        """数据获取异常"""
        err = DataFetchError(symbol="DOGEUSDT", detail="timeout")
        assert err.code == 1001
        assert "DOGEUSDT" in str(err)

    def test_websocket_disconnected(self):
        """WebSocket断开"""
        err = WebSocketDisconnected(symbol="PEPEUSDT")
        assert err.code == 1002

    def test_strategy_not_found(self):
        """策略不存在"""
        err = StrategyNotFound(name="magic_strategy")
        assert err.code == 2001

    def test_insufficient_data(self):
        """数据不足"""
        err = InsufficientData(strategy="livermore", required=100, actual=10)
        assert err.code == 2002
        assert err.details["required"] == 100

    def test_order_failed(self):
        """下单失败"""
        err = OrderFailed(symbol="DOGEUSDT", reason="insufficient margin")
        assert err.code == 3001

    def test_insufficient_balance(self):
        """余额不足"""
        err = InsufficientBalance(required=100.0, available=50.0)
        assert err.code == 3002

    def test_exchange_error(self):
        """交易所异常"""
        err = ExchangeError(exchange="okx", method="create_order", detail="rate limit")
        assert err.code == 3003

    def test_risk_limit_exceeded(self):
        """风控限制"""
        err = RiskLimitExceeded(rule="max_leverage", value=50, limit=30)
        assert err.code == 4001

    def test_daily_loss_hit(self):
        """当日亏损上限"""
        err = DailyLossHit(loss=-35.0, limit=-30.0)
        assert err.code == 4002

    def test_config_error(self):
        """配置错误"""
        err = ConfigError(key="api_key", reason="not found")
        assert err.code == 9001

    def test_error_codes_completeness(self):
        """所有错误码都已注册"""
        from core.errors import (
            DataFetchError, WebSocketDisconnected, DataParseError,
            StrategyNotFound, InsufficientData, SignalGenerationError,
            OrderFailed, InsufficientBalance, ExchangeError,
            RiskLimitExceeded, DailyLossHit, PositionLimitExceeded,
            NotificationFailed, MonitorError, ConfigError,
        )
        # 统计已定义的异常类数量
        defined = [
            DataFetchError, WebSocketDisconnected, DataParseError,
            StrategyNotFound, InsufficientData, SignalGenerationError,
            OrderFailed, InsufficientBalance, ExchangeError,
            RiskLimitExceeded, DailyLossHit, PositionLimitExceeded,
            NotificationFailed, MonitorError, ConfigError,
        ]
        for exc_cls in defined:
            assert exc_cls().code in ERROR_CODES, f"{exc_cls.__name__}.code not in ERROR_CODES"
        assert len(ERROR_CODES) == len(defined), "ERROR_CODES mismatch"

    def test_error_to_dict(self):
        """异常转字典"""
        err = TradingError(1001, "test", {"key": "val"})
        assert "1001" in str(err)
        assert "test" in str(err)
