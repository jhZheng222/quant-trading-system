"""
持仓管理集成测试
"""
import pytest
from core.engine.livermore_engine import LivermoreEngine


class TestPositionManagement:
    """持仓管理测试"""
    
    def test_open_position(self, engine):
        """测试开仓"""
        # 开仓
        engine._open_position(
            symbol="DOGEUSDT",
            side="buy",
            price=0.09,
            amount=100,
            strategy="livermore",
            stop_loss=0.0837,
            take_profit=0.108
        )
        
        # 验证持仓
        assert "DOGEUSDT" in engine.positions
        pos = engine.positions["DOGEUSDT"]
        assert pos.side == "buy"
        assert pos.amount == 100
        assert pos.stop_loss == 0.0837
    
    def test_add_position_updates_stop_loss(self, engine):
        """测试加仓后止损更新"""
        # 首次开仓
        engine._open_position(
            symbol="DOGEUSDT",
            side="buy",
            price=0.09,
            amount=100,
            strategy="livermore",
            stop_loss=0.0837
        )
        
        # 加仓
        engine._add_position(
            symbol="DOGEUSDT",
            price=0.08,
            action={"amount": 50, "reason": "浮盈加仓"}
        )
        
        # 验证止损已更新（基于新均价）
        pos = engine.positions["DOGEUSDT"]
        assert pos.stop_loss != 0.0837  # 止损应该已更新
        assert pos.stop_loss < 0.0837   # 新止损应该更低（因为均价降低了）
    
    def test_close_position(self, engine):
        """测试平仓"""
        # 开仓
        engine._open_position(
            symbol="DOGEUSDT",
            side="buy",
            price=0.09,
            amount=100,
            strategy="livermore"
        )
        
        # 平仓
        engine._close_position(
            symbol="DOGEUSDT",
            price=0.095,
            reason="止盈"
        )
        
        # 验证
        assert engine.positions["DOGEUSDT"].stage == "stopped"
        assert engine.total_pnl > 0  # 应该盈利
    
    def test_multiple_positions_different_symbols(self, engine):
        """测试多币种持仓"""
        # 开DOGE仓位
        engine._open_position(
            symbol="DOGEUSDT",
            side="buy",
            price=0.09,
            amount=100,
            strategy="livermore"
        )
        
        # 开PEPE仓位
        engine._open_position(
            symbol="PEPEUSDT",
            side="buy",
            price=0.000003,
            amount=1000000,
            strategy="livermore"
        )
        
        # 验证两个仓位都存在
        assert "DOGEUSDT" in engine.positions
        assert "PEPEUSDT" in engine.positions
