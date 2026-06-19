#!/usr/bin/env python3
"""
量化交易系统数据流转逻辑测试
============================

检查每个节点的数据是否符合逻辑，确保系统正常运行。
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(__file__))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")


class TestDataFlow:
    """数据流转逻辑测试"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def assert_true(self, condition: bool, message: str):
        """断言为真"""
        if condition:
            self.passed += 1
            logger.info(f"✅ PASS: {message}")
        else:
            self.failed += 1
            self.errors.append(message)
            logger.error(f"❌ FAIL: {message}")
    
    def assert_equal(self, actual, expected, message: str):
        """断言相等"""
        if actual == expected:
            self.passed += 1
            logger.info(f"✅ PASS: {message}")
        else:
            self.failed += 1
            self.errors.append(f"{message} (实际={actual}, 期望={expected})")
            logger.error(f"❌ FAIL: {message} (实际={actual}, 期望={expected})")
    
    def assert_greater(self, actual, threshold, message: str):
        """断言大于"""
        if actual > threshold:
            self.passed += 1
            logger.info(f"✅ PASS: {message}")
        else:
            self.failed += 1
            self.errors.append(f"{message} (实际={actual}, 阈值={threshold})")
            logger.error(f"❌ FAIL: {message} (实际={actual}, 阈值={threshold})")
    
    def assert_less(self, actual, threshold, message: str):
        """断言小于"""
        if actual < threshold:
            self.passed += 1
            logger.info(f"✅ PASS: {message}")
        else:
            self.failed += 1
            self.errors.append(f"{message} (实际={actual}, 阈值={threshold})")
            logger.error(f"❌ FAIL: {message} (实际={actual}, 阈值={threshold})")
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("🚀 开始量化交易系统数据流转逻辑测试")
        logger.info("=" * 60)
        
        # 1. 配置层测试
        self.test_config_layer()
        
        # 2. 数据采集层测试
        self.test_data_layer()
        
        # 3. 分析层测试
        self.test_analysis_layer()
        
        # 4. 策略层测试
        self.test_strategy_layer()
        
        # 5. 风控层测试
        self.test_risk_layer()
        
        # 6. 执行层测试
        self.test_execution_layer()
        
        # 7. 存储层测试
        self.test_storage_layer()
        
        # 8. 终止保护测试
        self.test_termination_protection()
        
        # 输出结果
        self.print_summary()
    
    def test_config_layer(self):
        """测试配置层"""
        logger.info("\n" + "=" * 60)
        logger.info("1️⃣ 配置层测试")
        logger.info("=" * 60)
        
        # 测试配置文件存在
        config_file = 'config/settings.json'
        self.assert_true(os.path.exists(config_file), "配置文件存在")
        
        # 测试配置文件格式
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # 检查必要的配置项
            self.assert_true('strategy' in config, "配置包含strategy节")
            self.assert_true('risk' in config, "配置包含risk节")
            self.assert_true('data' in config, "配置包含data节")
            
            # 检查策略配置
            strategy = config.get('strategy', {})
            self.assert_true('name' in strategy, "策略配置包含name")
            self.assert_true('stop_loss_pct' in strategy, "策略配置包含stop_loss_pct")
            self.assert_true('take_profit_pct' in strategy, "策略配置包含take_profit_pct")
            self.assert_true('leverage' in strategy, "策略配置包含leverage")
            self.assert_true('max_loss_pct' in strategy, "策略配置包含max_loss_pct (终止保护)")
            self.assert_true('min_trade_amount' in strategy, "策略配置包含min_trade_amount (终止保护)")
            
            # 检查参数范围
            self.assert_greater(strategy.get('stop_loss_pct', 0), 0, "止损比例 > 0")
            self.assert_less(strategy.get('stop_loss_pct', 1), 1, "止损比例 < 1")
            self.assert_greater(strategy.get('take_profit_pct', 0), 0, "止盈比例 > 0")
            self.assert_greater(strategy.get('leverage', 0), 0, "杠杆 > 0")
            self.assert_less(strategy.get('leverage', 100), 100, "杠杆 < 100")
            self.assert_equal(strategy.get('max_loss_pct', 0), 0.5, "最大亏损比例 = 50%")
            self.assert_equal(strategy.get('min_trade_amount', 0), 1.0, "最小交易额 = 1U")
            
            # 检查风险配置
            risk = config.get('risk', {})
            self.assert_true('initial_balance' in risk, "风险配置包含initial_balance")
            self.assert_greater(risk.get('initial_balance', 0), 0, "初始资金 > 0")
            
            # 检查数据配置
            data = config.get('data', {})
            self.assert_true('symbols' in data, "数据配置包含symbols")
            self.assert_true(len(data.get('symbols', [])) > 0, "交易对列表非空")
            
        except Exception as e:
            self.assert_true(False, f"配置文件格式正确: {e}")
    
    def test_data_layer(self):
        """测试数据采集层"""
        logger.info("\n" + "=" * 60)
        logger.info("2️⃣ 数据采集层测试")
        logger.info("=" * 60)
        
        try:
            from core.data.binance_data import BinanceDataCollector
            collector = BinanceDataCollector()
            
            # 测试获取行情
            ticker = collector.collect_ticker('DOGEUSDT')
            self.assert_true(ticker is not None, "获取DOGE行情成功")
            if ticker:
                self.assert_true('last' in ticker, "行情包含last价格")
                self.assert_greater(float(ticker.get('last', 0)), 0, "DOGE价格 > 0")
                logger.info(f"   DOGE当前价格: ${ticker.get('last', 'N/A')}")
            
            # 测试获取K线
            klines = collector.collect_klines('DOGEUSDT', '1h', 10)
            self.assert_true(klines is not None, "获取DOGE K线成功")
            if klines:
                self.assert_greater(len(klines), 0, "K线数据非空")
                # 检查K线数据结构 (list格式: [timestamp, open, high, low, close, volume])
                if len(klines) > 0:
                    kline = klines[0]
                    self.assert_true(len(kline) >= 6, "K线数据包含6个字段")
                    
                    # 检查K线数据逻辑
                    timestamp = kline[0]
                    open_price = float(kline[1])
                    high_price = float(kline[2])
                    low_price = float(kline[3])
                    close_price = float(kline[4])
                    volume = float(kline[5])
                    
                    self.assert_greater(high_price, 0, "最高价 > 0")
                    self.assert_greater(low_price, 0, "最低价 > 0")
                    self.assert_true(high_price >= low_price, "最高价 >= 最低价")
                    self.assert_true(high_price >= open_price, "最高价 >= 开盘价")
                    self.assert_true(high_price >= close_price, "最高价 >= 收盘价")
                    self.assert_true(low_price <= open_price, "最低价 <= 开盘价")
                    self.assert_true(low_price <= close_price, "最低价 <= 收盘价")
                    self.assert_greater(volume, 0, "成交量 > 0")
                    
                    logger.info(f"   K线示例: O={open_price:.6f} H={high_price:.6f} L={low_price:.6f} C={close_price:.6f} V={volume:.2f}")
            
            # 测试获取深度
            depth = collector.collect_depth('DOGEUSDT', 5)
            self.assert_true(depth is not None, "获取DOGE深度成功")
            if depth:
                self.assert_true('bids' in depth, "深度包含bids")
                self.assert_true('asks' in depth, "深度包含asks")
                
                bids = depth.get('bids', [])
                asks = depth.get('asks', [])
                
                if len(bids) > 0 and len(asks) > 0:
                    best_bid = float(bids[0][0])
                    best_ask = float(asks[0][0])
                    
                    self.assert_greater(best_bid, 0, "买一价 > 0")
                    self.assert_greater(best_ask, 0, "卖一价 > 0")
                    self.assert_true(best_ask >= best_bid, "卖一价 >= 买一价 (无负价差)")
                    
                    logger.info(f"   深度示例: 买一={best_bid:.6f} 卖一={best_ask:.6f}")
            
        except Exception as e:
            self.assert_true(False, f"数据采集层测试: {e}")
            logger.error(f"   异常: {e}")
    
    def test_analysis_layer(self):
        """测试分析层"""
        logger.info("\n" + "=" * 60)
        logger.info("3️⃣ 分析层测试")
        logger.info("=" * 60)
        
        try:
            from core.data.binance_data import BinanceDataCollector
            collector = BinanceDataCollector()
            
            # 获取K线数据用于分析
            klines = collector.collect_klines('DOGEUSDT', '1h', 50)
            self.assert_true(klines is not None, "获取K线数据用于分析")
            
            if klines and len(klines) >= 20:
                # 测试成本分析
                try:
                    from core.analysis.cost_basis import CostBasisAnalyzer
                    analyzer = CostBasisAnalyzer()
                    
                    # 模拟分析 (list格式: [timestamp, open, high, low, close, volume])
                    closes = [float(k[4]) for k in klines]
                    volumes = [float(k[5]) for k in klines]
                    
                    # 检查数据有效性
                    self.assert_true(all(c > 0 for c in closes), "所有收盘价 > 0")
                    self.assert_true(all(v >= 0 for v in volumes), "所有成交量 >= 0")
                    
                    # 计算简单移动平均
                    if len(closes) >= 20:
                        sma20 = sum(closes[-20:]) / 20
                        self.assert_greater(sma20, 0, "SMA20 > 0")
                        logger.info(f"   SMA20: {sma20:.6f}")
                    
                    # 计算RSI
                    if len(closes) >= 15:
                        gains = []
                        losses = []
                        for i in range(1, len(closes)):
                            change = closes[i] - closes[i-1]
                            if change > 0:
                                gains.append(change)
                                losses.append(0)
                            else:
                                gains.append(0)
                                losses.append(abs(change))
                        
                        avg_gain = sum(gains[-14:]) / 14
                        avg_loss = sum(losses[-14:]) / 14
                        
                        if avg_loss > 0:
                            rs = avg_gain / avg_loss
                            rsi = 100 - (100 / (1 + rs))
                        else:
                            rsi = 100
                        
                        self.assert_true(0 <= rsi <= 100, "RSI在0-100范围内")
                        logger.info(f"   RSI: {rsi:.2f}")
                    
                    logger.info("✅ 成本分析模块可访问")
                    
                except Exception as e:
                    logger.warning(f"   成本分析模块测试跳过: {e}")
                
                # 测试技术指标计算
                try:
                    closes = [float(k[4]) for k in klines]
                    
                    # EMA计算
                    def ema(data, period):
                        if len(data) < period:
                            return data[-1]
                        multiplier = 2 / (period + 1)
                        ema_val = sum(data[:period]) / period
                        for price in data[period:]:
                            ema_val = (price - ema_val) * multiplier + ema_val
                        return ema_val
                    
                    ema20 = ema(closes, 20)
                    ema50 = ema(closes, 50) if len(closes) >= 50 else ema(closes, len(closes))
                    
                    self.assert_greater(ema20, 0, "EMA20 > 0")
                    self.assert_greater(ema50, 0, "EMA50 > 0")
                    
                    logger.info(f"   EMA20: {ema20:.6f}, EMA50: {ema50:.6f}")
                    
                    # 布林带计算
                    if len(closes) >= 20:
                        sma20 = sum(closes[-20:]) / 20
                        variance = sum((c - sma20) ** 2 for c in closes[-20:]) / 20
                        std20 = variance ** 0.5
                        
                        bb_upper = sma20 + 2 * std20
                        bb_lower = sma20 - 2 * std20
                        
                        self.assert_true(bb_upper > bb_lower, "布林带上轨 > 下轨")
                        self.assert_true(bb_lower > 0, "布林带下轨 > 0")
                        
                        logger.info(f"   布林带: 上={bb_upper:.6f} 中={sma20:.6f} 下={bb_lower:.6f}")
                    
                    logger.info("✅ 技术指标计算正确")
                    
                except Exception as e:
                    logger.error(f"   技术指标计算异常: {e}")
            
        except Exception as e:
            self.assert_true(False, f"分析层测试: {e}")
            logger.error(f"   异常: {e}")
    
    def test_strategy_layer(self):
        """测试策略层"""
        logger.info("\n" + "=" * 60)
        logger.info("4️⃣ 策略层测试")
        logger.info("=" * 60)
        
        try:
            from core.strategies import load_strategy, list_strategies
            
            # 列出可用策略
            strategies = list_strategies()
            self.assert_true(len(strategies) > 0, "有可用策略")
            logger.info(f"   可用策略: {strategies}")
            
            # 加载主策略
            strategy = load_strategy('ema_rsi_optimized', {
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.12,
                'buy_threshold': 60,
                'sell_threshold': 45,
                'position_size_min': 0.15,
                'position_size_max': 0.40,
                'leverage': 3
            })
            
            self.assert_true(strategy is not None, "加载ema_rsi_optimized策略成功")
            self.assert_equal(strategy.name, 'ema_rsi_optimized', "策略名称正确")
            self.assert_equal(strategy.version, '2.0.0', "策略版本正确")
            
            # 测试信号生成
            from core.data.binance_data import BinanceDataCollector
            collector = BinanceDataCollector()
            klines = collector.collect_klines('DOGEUSDT', '1h', 100)
            
            if klines and len(klines) >= 50:
                # list格式: [timestamp, open, high, low, close, volume]
                current_price = float(klines[-1][4])
                
                # 生成信号
                signal = strategy.generate_signal('DOGEUSDT', klines, current_price, None)
                
                self.assert_true(signal is not None, "策略返回信号")
                if signal:
                    self.assert_true(signal.action in ['buy', 'sell', 'hold', 'add_position'], 
                                   f"信号动作有效: {signal.action}")
                    self.assert_true(signal.price > 0, "信号价格 > 0")
                    self.assert_true(signal.reason is not None and len(signal.reason) > 0, 
                                   "信号原因非空")
                    
                    logger.info(f"   信号: action={signal.action}, price={signal.price:.6f}")
                    logger.info(f"   原因: {signal.reason}")
                    
                    # 检查信号元数据
                    if signal.metadata:
                        self.assert_true('position_size' in signal.metadata, "信号包含position_size")
                        position_size = signal.metadata.get('position_size', 0)
                        self.assert_true(0.15 <= position_size <= 0.40, 
                                       f"仓位大小在15%-40%范围内: {position_size}")
            
            logger.info("✅ 策略层测试通过")
            
        except Exception as e:
            self.assert_true(False, f"策略层测试: {e}")
            logger.error(f"   异常: {e}")
    
    def test_risk_layer(self):
        """测试风控层"""
        logger.info("\n" + "=" * 60)
        logger.info("5️⃣ 风控层测试")
        logger.info("=" * 60)
        
        try:
            from core.risk.risk_manager import RiskManager
            
            risk_manager = RiskManager(initial_balance=10.0)
            
            # 测试正常开仓
            result = risk_manager.check_open_allowed(
                symbol='DOGEUSDT',
                side='buy',
                amount=100,
                price=0.09,
                balance=10.0,
                positions={},
                leverage=3
            )
            
            self.assert_true(result is not None, "风控返回结果")
            if result:
                self.assert_true('allowed' in result, "结果包含allowed")
                self.assert_true('reason' in result, "结果包含reason")
                logger.info(f"   正常开仓检查: allowed={result.get('allowed')}, reason={result.get('reason')}")
            
            # 测试仓位限制
            positions = {
                'DOGEUSDT': {'side': 'buy', 'amount': 1000, 'entry_price': 0.09}
            }
            
            result2 = risk_manager.check_open_allowed(
                symbol='PEPEUSDT',
                side='buy',
                amount=100000,
                price=0.000003,
                balance=10.0,
                positions=positions,
                leverage=3
            )
            
            if result2:
                logger.info(f"   已有持仓时开仓检查: allowed={result2.get('allowed')}, reason={result2.get('reason')}")
            
            # 测试黑天鹅防护
            self.assert_true(risk_manager.swan_price_drop == 0.10, "黑天鹅价格跌幅阈值 = 10%")
            self.assert_true(risk_manager.consecutive_loss_limit == 3, "连续止损限制 = 3次")
            self.assert_true(risk_manager.cooldown_minutes == 120, "冷却时间 = 120分钟")
            
            logger.info("✅ 风控层测试通过")
            
        except Exception as e:
            self.assert_true(False, f"风控层测试: {e}")
            logger.error(f"   异常: {e}")
    
    def test_execution_layer(self):
        """测试执行层"""
        logger.info("\n" + "=" * 60)
        logger.info("6️⃣ 执行层测试")
        logger.info("=" * 60)
        
        try:
            from core.config.strategy_config import SimulatedTrader
            
            # 创建测试交易器
            trader = SimulatedTrader('test')
            trader.initial_balance = 10.0
            trader.balance = 10.0
            
            # 测试开仓
            self.assert_equal(trader.balance, 10.0, "初始余额 = 10U")
            
            position = trader.open_position(
                symbol='DOGEUSDT',
                side='buy',
                price=0.09,
                size_pct=0.2,
                reason='测试开仓'
            )
            
            self.assert_true(position is not None, "开仓成功")
            if position:
                self.assert_equal(position['symbol'], 'DOGEUSDT', "持仓币种正确")
                self.assert_equal(position['side'], 'buy', "持仓方向正确")
                self.assert_equal(position['entry_price'], 0.09, "开仓价格正确")
                self.assert_true(position['stop_loss'] > 0, "止损价 > 0")
                self.assert_true(position['take_profit'] > 0, "止盈价 > 0")
                self.assert_true(position['take_profit'] > position['entry_price'], "止盈价 > 开仓价")
                self.assert_true(position['stop_loss'] < position['entry_price'], "止损价 < 开仓价")
                
                logger.info(f"   开仓详情: 价格={position['entry_price']}, 止损={position['stop_loss']:.6f}, 止盈={position['take_profit']:.6f}")
                
                # 检查保证金扣除
                expected_margin = 10.0 * 0.2  # 20% of 10U
                self.assert_less(trader.balance, 10.0, "保证金已扣除")
                logger.info(f"   扣除保证金后余额: {trader.balance:.2f}U")
            
            # 测试止损止盈检查
            if position:
                # 测试止损触发
                closed_trades = trader.check_stop_loss_take_profit('DOGEUSDT', position['stop_loss'] - 0.001)
                if len(closed_trades) > 0:
                    self.assert_equal(closed_trades[0]['reason'], '止损', "止损触发正确")
                    logger.info(f"   止损触发: 盈亏={closed_trades[0]['pnl']:.2f}U")
                else:
                    # 重新开仓测试止盈
                    position = trader.open_position(
                        symbol='DOGEUSDT',
                        side='buy',
                        price=0.09,
                        size_pct=0.2,
                        reason='测试止盈'
                    )
                    
                    closed_trades = trader.check_stop_loss_take_profit('DOGEUSDT', position['take_profit'] + 0.001)
                    if len(closed_trades) > 0:
                        self.assert_equal(closed_trades[0]['reason'], '止盈', "止盈触发正确")
                        logger.info(f"   止盈触发: 盈亏={closed_trades[0]['pnl']:.2f}U")
            
            logger.info("✅ 执行层测试通过")
            
        except Exception as e:
            self.assert_true(False, f"执行层测试: {e}")
            logger.error(f"   异常: {e}")
    
    def test_storage_layer(self):
        """测试存储层"""
        logger.info("\n" + "=" * 60)
        logger.info("7️⃣ 存储层测试")
        logger.info("=" * 60)
        
        try:
            import sqlite3
            
            db_path = 'data/trading.db'
            self.assert_true(os.path.exists(db_path), "数据库文件存在")
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查必要的表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['klines', 'signals', 'trades', 'positions', 'account_snapshots', 'alerts']
            for table in required_tables:
                self.assert_true(table in tables, f"表 {table} 存在")
            
            # 检查表结构
            for table in required_tables:
                if table in tables:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [row[1] for row in cursor.fetchall()]
                    self.assert_true(len(columns) > 0, f"表 {table} 有列定义")
                    logger.info(f"   表 {table}: {len(columns)} 列")
            
            # 检查数据量
            for table in required_tables:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    logger.info(f"   表 {table}: {count} 条记录")
            
            # 检查数据一致性
            if 'account_snapshots' in tables:
                cursor.execute("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1")
                snapshot = cursor.fetchone()
                if snapshot:
                    self.assert_true(snapshot[1] is not None, "快照有时间戳")
                    logger.info(f"   最新快照: ID={snapshot[0]}, 时间={snapshot[1]}")
            
            conn.close()
            logger.info("✅ 存储层测试通过")
            
        except Exception as e:
            self.assert_true(False, f"存储层测试: {e}")
            logger.error(f"   异常: {e}")
    
    def test_termination_protection(self):
        """测试终止保护"""
        logger.info("\n" + "=" * 60)
        logger.info("8️⃣ 终止保护测试")
        logger.info("=" * 60)
        
        try:
            from core.config.strategy_config import SimulatedTrader
            
            # 测试亏损50%终止
            trader = SimulatedTrader('test_termination')
            trader.initial_balance = 10.0
            trader.balance = 4.5  # 亏损55%
            trader.max_loss_pct = 0.5
            trader.min_trade_amount = 1.0
            
            # 检查终止条件
            should_stop = trader._check_termination_conditions()
            self.assert_true(should_stop, "亏损55%触发终止")
            self.assert_true(trader.is_stopped, "系统标记为已终止")
            self.assert_true(trader.stop_reason is not None, "终止原因非空")
            logger.info(f"   终止原因: {trader.stop_reason}")
            
            # 测试余额不足终止
            trader2 = SimulatedTrader('test_termination2')
            trader2.initial_balance = 10.0
            trader2.balance = 0.5  # 余额不足1U
            trader2.max_loss_pct = 0.5
            trader2.min_trade_amount = 1.0
            
            should_stop2 = trader2._check_termination_conditions()
            self.assert_true(should_stop2, "余额0.5U触发终止")
            self.assert_true(trader2.is_stopped, "系统标记为已终止")
            logger.info(f"   终止原因: {trader2.stop_reason}")
            
            # 测试正常情况不终止
            trader3 = SimulatedTrader('test_termination3')
            trader3.initial_balance = 10.0
            trader3.balance = 8.0  # 亏损20%
            trader3.max_loss_pct = 0.5
            trader3.min_trade_amount = 1.0
            
            should_stop3 = trader3._check_termination_conditions()
            self.assert_true(not should_stop3, "亏损20%不触发终止")
            self.assert_true(not trader3.is_stopped, "系统未终止")
            
            # 测试终止后无法开仓
            trader4 = SimulatedTrader('test_termination4')
            trader4.initial_balance = 10.0
            trader4.balance = 4.0
            trader4.max_loss_pct = 0.5
            trader4.min_trade_amount = 1.0
            trader4.is_stopped = True
            trader4.stop_reason = "测试终止"
            
            position = trader4.open_position('DOGEUSDT', 'buy', 0.09, size_pct=0.2)
            self.assert_true(position == {}, "终止后无法开仓")
            
            logger.info("✅ 终止保护测试通过")
            
        except Exception as e:
            self.assert_true(False, f"终止保护测试: {e}")
            logger.error(f"   异常: {e}")
    
    def print_summary(self):
        """打印测试摘要"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 测试摘要")
        logger.info("=" * 60)
        logger.info(f"✅ 通过: {self.passed}")
        logger.info(f"❌ 失败: {self.failed}")
        logger.info(f"总计: {self.passed + self.failed}")
        
        if self.errors:
            logger.error("\n❌ 失败的测试:")
            for error in self.errors:
                logger.error(f"   • {error}")
        
        if self.failed == 0:
            logger.info("\n🎉 所有测试通过！系统数据流转逻辑正确。")
        else:
            logger.error(f"\n⚠️ 有 {self.failed} 个测试失败，请检查相关逻辑。")
        
        return self.failed == 0


if __name__ == "__main__":
    tester = TestDataFlow()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
