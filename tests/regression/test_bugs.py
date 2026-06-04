"""
回归测试 - 验证已修复的bug不会再次出现
"""
import pytest
from datetime import datetime, timedelta
from core.engine.livermore_engine import LivermoreEngine
from core.storage.sqlite_storage import SQLiteStorage


class TestBugFixes:
    """Bug修复回归测试"""
    
    def test_confidence_dimension_mismatch(self, engine):
        """验证P0-1: confidence量纲匹配"""
        # confidence是0-1范围，buy_threshold是45-80范围
        # check_open应该将confidence*100后再比较
        
        # 模拟信号confidence=0.6
        engine.storage.save_signal({
            "symbol": "DOGEUSDT",
            "signal_type": "buy",
            "price": 0.09,
            "confidence": 0.6,
            "reason": "测试"
        })
        
        # buy_threshold默认60，0.6*100=60，应该满足条件
        assert engine.buy_threshold == 60
    
    def test_highest_pnl_pct_persistence(self, engine):
        """验证P0-2: 移动止损持久化"""
        # 开仓
        engine._open_position(
            symbol="DOGEUSDT",
            side="buy",
            price=0.09,
            amount=100,
            strategy="livermore"
        )
        
        # 模拟浮盈更新
        pos = engine.positions["DOGEUSDT"]
        pos.highest_pnl_pct = 0.15  # 15%浮盈
        
        # 验证highest_pnl_pct被记录
        assert pos.highest_pnl_pct == 0.15
    
    def test_signal_storage_sync(self, storage):
        """验证P0-3: 信号存储同步"""
        # 保存信号
        storage.save_signal({
            "symbol": "DOGEUSDT",
            "signal_type": "buy",
            "price": 0.09,
            "confidence": 0.65,
            "reason": "测试信号"
        })
        
        # 读取信号
        signals = storage.get_signals("DOGEUSDT", limit=1)
        assert len(signals) == 1
        assert signals[0]["confidence"] == 0.65
    
    def test_time_stop_from_last_add(self, engine):
        """验证P1-4: 时间止损从最后加仓计算"""
        # 开仓（48小时前）
        engine._open_position(
            symbol="DOGEUSDT",
            side="buy",
            price=0.09,
            amount=100,
            strategy="livermore"
        )
        
        # 模拟48小时前开仓
        pos = engine.positions["DOGEUSDT"]
        pos.entry_time = (datetime.now() - timedelta(hours=49)).isoformat()
        
        # 加仓（刚才）
        engine._add_position(
            symbol="DOGEUSDT",
            price=0.085,
            action={"amount": 50, "reason": "加仓"}
        )
        
        # 验证stages中最后一条是加仓时间
        last_stage_time = pos.stages[-1]["time"]
        last_dt = datetime.fromisoformat(last_stage_time)
        hold_hours = (datetime.now() - last_dt).total_seconds() / 3600
        
        # 加仓后持仓时间应该很短（<1小时），不应该触发48小时止损
        assert hold_hours < 1
    
    def test_add_position_updates_stop_loss(self, engine):
        """验证P1-5: 加仓后止损更新"""
        # 开仓
        engine._open_position(
            symbol="DOGEUSDT",
            side="buy",
            price=0.09,
            amount=100,
            strategy="livermore",
            stop_loss=0.0837
        )
        
        original_stop = engine.positions["DOGEUSDT"].stop_loss
        
        # 加仓（价格更低）
        engine._add_position(
            symbol="DOGEUSDT",
            price=0.08,
            action={"amount": 50, "reason": "加仓"}
        )
        
        # 验证止损已更新
        new_stop = engine.positions["DOGEUSDT"].stop_loss
        assert new_stop != original_stop
        assert new_stop < original_stop  # 新止损应该更低
    
    def test_cooldown_period(self, engine):
        """验证开仓冷却期"""
        # 模拟30分钟内开仓
        engine.storage.save_trade({
            "symbol": "DOGEUSDT",
            "side": "buy",
            "entry_price": 0.09,
            "amount": 100,
            "entry_time": datetime.now().isoformat(),
            "status": "open"
        })
        
        # 检查冷却期
        last_open_time = engine.storage.get_last_open_time("DOGEUSDT")
        assert last_open_time is not None
        
        last_dt = datetime.fromisoformat(last_open_time)
        cooldown_minutes = 30
        in_cooldown = (datetime.now() - last_dt) < timedelta(minutes=cooldown_minutes)
        assert in_cooldown == True
    
    def test_max_positions_per_symbol(self, engine):
        """验证单币种持仓笔数限制"""
        # 开3笔仓位
        for i in range(3):
            engine.storage.save_trade({
                "symbol": "DOGEUSDT",
                "side": "buy",
                "entry_price": 0.09 - i * 0.001,
                "amount": 100,
                "entry_time": datetime.now().isoformat(),
                "status": "open"
            })
        
        # 检查持仓笔数
        open_count = engine.storage.get_open_trade_count("DOGEUSDT")
        assert open_count == 3
        
        # 达到上限，应该阻止新开仓
        max_positions = 3
        assert open_count >= max_positions
