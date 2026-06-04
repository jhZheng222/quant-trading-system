"""
测试配置文件
"""
import sys
import os
import tempfile
import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine.livermore_engine import LivermoreEngine
from core.storage.sqlite_storage import SQLiteStorage
from core.risk.risk_manager import RiskManager


@pytest.fixture
def db_path():
    """创建临时数据库路径"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    yield path
    # 清理
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def storage(db_path):
    """创建测试存储实例"""
    return SQLiteStorage(db_path)


@pytest.fixture
def engine(db_path):
    """创建测试引擎实例"""
    return LivermoreEngine(initial_balance=100.0, db_path=db_path)


@pytest.fixture
def risk_manager():
    """创建测试风控实例"""
    return RiskManager(initial_balance=100.0)


@pytest.fixture
def sample_klines():
    """示例K线数据"""
    return [
        [1625097600000, "0.09", "0.095", "0.088", "0.092", "1000"],
        [1625101200000, "0.092", "0.096", "0.091", "0.094", "1200"],
        [1625104800000, "0.094", "0.097", "0.093", "0.095", "800"],
    ]


@pytest.fixture
def sample_signal():
    """示例信号"""
    from core.strategy.multi_strategy import StrategySignal, StrategyType
    return StrategySignal(
        strategy=StrategyType.LIVERMORE,
        action="buy",
        confidence=0.65,
        reason="测试信号"
    )
