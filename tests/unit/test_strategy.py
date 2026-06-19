"""策略模块测试"""
import pytest
import numpy as np
from datetime import datetime, timedelta


def _make_klines(count=100, base_price=0.1):
    """生成模拟 K 线数据"""
    klines = []
    price = base_price
    for i in range(count):
        ts = int((datetime.now() - timedelta(hours=count - i)).timestamp() * 1000)
        high = price * (1 + np.random.uniform(-0.02, 0.02))
        low = price * (1 + np.random.uniform(-0.02, 0.02))
        close = price * (1 + np.random.uniform(-0.01, 0.01))
        volume = np.random.uniform(100000, 10000000)
        klines.append({
            "timestamp": ts,
            "open": price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })
        price = close
    return klines


class TestLivermoreStrategy:
    """利弗莫尔策略"""

    def test_import(self):
        """可以导入"""
        from core.strategy.livermore import LivermoreStage
        assert LivermoreStage.EMPTY.value == "empty"

    def test_config_and_stages(self):
        """配置和阶段枚举正确"""
        from core.strategy.livermore import LivermoreConfig, LivermoreStage
        cfg = LivermoreConfig()
        assert cfg.trigger_pct == 0.05
        assert cfg.stop_pct == 0.07
        assert LivermoreStage.EMPTY.value == "empty"
        assert LivermoreStage.FULL.value == "full"


class TestBollingerStrategy:
    """布林带策略"""

    def test_import(self):
        """可以导入"""
        from core.strategy.bollinger_strategy import BollingerStrategy
        assert hasattr(BollingerStrategy, "analyze")


class TestEMARsiStrategy:
    """EMA+RSI 策略"""

    def test_import(self):
        """可以导入"""
        from core.strategy.ema_rsi_strategy import EMARsiStrategy
        assert hasattr(EMARsiStrategy, "analyze")


class TestMultiStrategy:
    """多策略管理"""

    def test_import(self):
        """可以导入"""
        from core.strategy._multi_strategy_v1 import MarketRegime
        assert len(MarketRegime) >= 3

    def test_compatibility_import(self):
        """旧 core.strategies 兼容导入"""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from core.strategies import BollingerStrategy as BS
            assert BS is not None


class TestErrors:
    """新建错误码系统"""

    def test_error_codes(self):
        from core.errors import (
            DataFetchError, OrderFailed, RiskLimitExceeded, ERROR_CODES
        )
        assert DataFetchError(symbol="DOGE").code == 1001
        assert OrderFailed(symbol="DOGE").code == 3001
        assert RiskLimitExceeded().code == 4001
        assert len(ERROR_CODES) >= 10


class TestMainEntry:
    """统一入口"""

    def test_help_works(self):
        """main.py --help 可运行"""
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            capture_output=True, text=True
        )
        assert "usage" in result.stdout or result.returncode == 0
