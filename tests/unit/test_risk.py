"""
风控模块单元测试
"""
import pytest
from core.risk.risk_manager import RiskManager


class TestRiskManager:
    """风控管理器测试"""
    
    def test_init(self, risk_manager):
        """测试初始化"""
        assert risk_manager.initial_balance == 100.0
        assert risk_manager.max_single_position == 0.30
        assert risk_manager.max_margin_usage == 0.50
    
    def test_check_open_allowed_normal(self, risk_manager):
        """测试正常开仓检查"""
        positions = {}
        result = risk_manager.check_open_allowed(
            symbol="DOGEUSDT",
            side="buy",
            amount=100,
            price=0.09,
            balance=100.0,
            positions=positions,
            leverage=10
        )
        assert result["allowed"] == True
    
    def test_check_open_allowed_margin_exceeded(self, risk_manager):
        """测试保证金超额"""
        # 模拟已有持仓，保证金使用率超过50%
        positions = {
            "DOGEUSDT": {"symbol": "DOGEUSDT", "side": "buy", "cost": 60.0, "stage": "open"}
        }
        result = risk_manager.check_open_allowed(
            symbol="PEPEUSDT",
            side="buy",
            amount=100,
            price=0.000003,
            balance=100.0,
            positions=positions,
            leverage=10
        )
        assert result["allowed"] == False
        assert "保证金" in result["reason"]
    
    def test_check_open_allowed_single_position(self, risk_manager):
        """测试单币种仓位限制"""
        # 模拟DOGE仓位已超过30%
        positions = {
            "DOGEUSDT": {"symbol": "DOGEUSDT", "side": "buy", "cost": 35.0, "stage": "open"}
        }
        result = risk_manager.check_open_allowed(
            symbol="DOGEUSDT",
            side="buy",
            amount=100,
            price=0.09,
            balance=100.0,
            positions=positions,
            leverage=10
        )
        assert result["allowed"] == False
        assert "仓位" in result["reason"]
    
    def test_record_trade_result(self, risk_manager):
        """测试记录交易结果"""
        # 记录盈利
        risk_manager.record_trade_result(10.0)
        assert risk_manager.consecutive_losses == 0
        
        # 记录亏损
        risk_manager.record_trade_result(-5.0)
        assert risk_manager.consecutive_losses == 1
    
    def test_consecutive_loss_pause(self, risk_manager):
        """测试连续亏损暂停"""
        # 连续3次亏损
        for _ in range(3):
            risk_manager.record_trade_result(-10.0)
        
        # 应该触发暂停
        positions = {}
        result = risk_manager.check_open_allowed(
            symbol="DOGEUSDT",
            side="buy",
            amount=100,
            price=0.09,
            balance=100.0,
            positions=positions,
            leverage=10
        )
        assert result["allowed"] == False
        assert "暂停" in result["reason"]
