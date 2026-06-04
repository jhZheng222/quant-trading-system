"""
实时交易引擎 v2
==============

使用统一数据服务（WebSocket转发）获取数据。
支持模拟和实盘模式切换。

架构：
  数据服务 → DataClient → 策略引擎 → 交易执行
"""

import json
import time
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger

from core.data.websocket_service import DataClient
from core.config.strategy_config import StrategyConfig, SimulatedTrader


class RealtimeEngineV2:
    """
    实时交易引擎 v2
    
    使用统一数据服务，支持模拟和实盘。
    """
    
    def __init__(self, config_name: str = 'default', mode: str = 'simulation',
                 data_url: str = 'ws://localhost:8765'):
        """
        Args:
            config_name: 策略配置名称
            mode: 模式 ('simulation' 或 'live')
            data_url: 数据服务地址
        """
        self.config_name = config_name
        self.mode = mode
        self.data_url = data_url
        
        # 加载策略配置
        self.config_manager = StrategyConfig()
        self.params = self.config_manager.load_params(config_name)
        
        if not self.params:
            # 使用默认参数
            self.params = {
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.08,
                'buy_threshold': 65,
                'sell_threshold': 40,
                'position_size': 0.2
            }
            logger.warning(f"使用默认参数")
        
        # 数据客户端
        self.data_client = DataClient(data_url)
        self.data_client.on_ticker = self._on_ticker_update
        self.data_client.on_kline = self._on_kline_update
        
        # 模拟交易器（模拟模式）
        self.simulator: Optional[SimulatedTrader] = None
        if mode == 'simulation':
            self.simulator = SimulatedTrader(config_name)
        
        # 状态
        self._running = False
        self.evaluation_count = 0
        self.last_evaluation = None
        
        # 交易对
        self.symbols = ['DOGEUSDT', 'PEPEUSDT']
        
        logger.info(f"⚡ 实时引擎 v2 初始化")
        logger.info(f"   模式: {mode}")
        logger.info(f"   配置: {config_name}")
        logger.info(f"   数据源: {data_url}")
    
    def _on_ticker_update(self, symbol: str, ticker: Dict):
        """Ticker更新回调"""
        # 检查止损止盈
        if self.simulator:
            current_price = ticker.get('price', 0)
            closed_trades = self.simulator.check_stop_loss_take_profit(symbol, current_price)
            
            for trade in closed_trades:
                logger.info(f"📉 自动平仓 {symbol}: {trade['reason']}, 盈亏={trade['pnl']:.2f}U")
    
    def _on_kline_update(self, symbol: str, interval: str, kline: Dict):
        """K线更新回调"""
        # 只在K线收盘时评估
        if not kline.get('is_closed', False):
            return
        
        # 只在主周期评估
        if interval != '1h':
            return
        
        self.evaluation_count += 1
        self.last_evaluation = datetime.now()
        
        logger.info(f"{'='*40}")
        logger.info(f"⚡ K线收盘 {symbol} {interval} | 第{self.evaluation_count}次评估")
        
        # 获取数据
        klines = self.data_client.get_klines(symbol, interval)
        current_price = kline.get('close', 0)
        
        # 生成信号
        signal = self._generate_signal(symbol, klines, current_price)
        
        if signal:
            logger.info(f"   信号: {signal['signal']}, 得分: {signal['score']}")
            
            # 执行交易逻辑
            self._execute_signal(symbol, signal, current_price)
        
        logger.info(f"   价格: {current_price}")
        logger.info(f"{'='*40}")
    
    def _generate_signal(self, symbol: str, klines: List, current_price: float) -> Optional[Dict]:
        """生成交易信号"""
        if len(klines) < 24:
            return None
        
        # 计算简单指标
        closes = [k[4] for k in klines]
        volumes = [k[5] for k in klines]
        
        # EMA计算
        ema_20 = self._calculate_ema(closes, 20)
        ema_50 = self._calculate_ema(closes, 50)
        
        # RSI计算
        rsi = self._calculate_rsi(closes, 14)
        
        # 成交量变化
        avg_volume = sum(volumes[-24:]) / 24
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # 价格位置
        high_24 = max(closes[-24:])
        low_24 = min(closes[-24:])
        price_position = (current_price - low_24) / (high_24 - low_24) if high_24 != low_24 else 0.5
        
        # 生成信号
        score = 50
        
        # EMA信号
        if ema_20 > ema_50:
            score += 10  # 多头排列
        else:
            score -= 10  # 空头排列
        
        # RSI信号
        if rsi < 30:
            score += 15  # 超卖
        elif rsi > 70:
            score -= 15  # 超买
        
        # 成交量信号
        if volume_ratio > 1.5:
            if price_position < 0.3:
                score += 10  # 低位放量
            elif price_position > 0.7:
                score -= 10  # 高位放量
        
        # 价格位置信号
        if price_position < 0.2:
            score += 10  # 低位
        elif price_position > 0.8:
            score -= 10  # 高位
        
        # 限制在0-100
        score = max(0, min(100, score))
        
        # 生成信号
        if score >= 70:
            signal = 'strong_buy'
        elif score >= self.params.get('buy_threshold', 65):
            signal = 'buy'
        elif score >= self.params.get('sell_threshold', 40):
            signal = 'hold'
        elif score >= 30:
            signal = 'sell'
        else:
            signal = 'strong_sell'
        
        return {
            'signal': signal,
            'score': score,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'rsi': rsi,
            'volume_ratio': volume_ratio,
            'price_position': price_position
        }
    
    def _calculate_ema(self, data: List[float], period: int) -> float:
        """计算EMA"""
        if len(data) < period:
            return data[-1]
        
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_rsi(self, data: List[float], period: int = 14) -> float:
        """计算RSI"""
        if len(data) < period + 1:
            return 50
        
        deltas = [data[i] - data[i-1] for i in range(1, len(data))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _execute_signal(self, symbol: str, signal: Dict, current_price: float):
        """执行交易信号"""
        if not self.simulator:
            return
        
        signal_type = signal['signal']
        
        # 检查是否有持仓
        has_position = any(p['symbol'] == symbol for p in self.simulator.positions)
        
        if signal_type in ['buy', 'strong_buy'] and not has_position:
            # 开多仓
            self.simulator.open_position(
                symbol, 'buy', current_price,
                reason=f"信号得分: {signal['score']}"
            )
            logger.info(f"📈 开多仓 {symbol} @ {current_price:.6f}")
        
        elif signal_type in ['sell', 'strong_sell'] and not has_position:
            # 开空仓
            self.simulator.open_position(
                symbol, 'sell', current_price,
                reason=f"信号得分: {signal['score']}"
            )
            logger.info(f"📉 开空仓 {symbol} @ {current_price:.6f}")
        
        elif signal_type in ['sell', 'strong_sell'] and has_position:
            # 平多仓
            for i, pos in enumerate(self.simulator.positions):
                if pos['symbol'] == symbol and pos['side'] == 'buy':
                    self.simulator.close_position(i, current_price, '反向信号')
                    logger.info(f"📉 平多仓 {symbol} @ {current_price:.6f}")
                    break
        
        elif signal_type in ['buy', 'strong_buy'] and has_position:
            # 平空仓
            for i, pos in enumerate(self.simulator.positions):
                if pos['symbol'] == symbol and pos['side'] == 'sell':
                    self.simulator.close_position(i, current_price, '反向信号')
                    logger.info(f"📈 平空仓 {symbol} @ {current_price:.6f}")
                    break
    
    def start(self):
        """启动引擎"""
        self._running = True
        self.data_client.start()
        logger.info("⚡ 实时引擎已启动")
    
    def stop(self):
        """停止引擎"""
        self._running = False
        self.data_client.stop()
        logger.info("⚡ 实时引擎已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        status = {
            'mode': self.mode,
            'config_name': self.config_name,
            'running': self._running,
            'evaluation_count': self.evaluation_count,
            'last_evaluation': self.last_evaluation.isoformat() if self.last_evaluation else None,
            'data_source': self.data_url,
            'symbols': self.symbols,
            'params': self.params
        }
        
        # 模拟状态
        if self.simulator:
            sim_status = self.simulator.get_status()
            status['simulation'] = {
                'balance': sim_status['balance'],
                'total_pnl': sim_status['total_pnl'],
                'total_return_pct': sim_status['total_return_pct'],
                'total_trades': sim_status['total_trades'],
                'win_rate': sim_status['win_rate'],
                'open_positions': sim_status['open_positions']
            }
        
        # 实时价格
        status['prices'] = {}
        for symbol in self.symbols:
            price = self.data_client.get_price(symbol)
            if price > 0:
                status['prices'][symbol] = price
        
        return status
    
    def format_status(self) -> str:
        """格式化状态"""
        status = self.get_status()
        
        report = f"""
⚡ 实时引擎 v2 状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 基本信息:
   模式: {status['mode']}
   配置: {status['config_name']}
   状态: {'✅ 运行中' if status['running'] else '❌ 已停止'}
   数据源: {status['data_source']}
   评估次数: {status['evaluation_count']}
   上次评估: {status['last_evaluation'] or '无'}

💰 实时价格:
"""
        
        for symbol, price in status.get('prices', {}).items():
            report += f"   {symbol}: ${price:.6f}\n"
        
        if 'simulation' in status:
            sim = status['simulation']
            report += f"""
📊 模拟交易:
   余额: {sim['balance']:.2f}U
   总盈亏: {sim['total_pnl']:+.2f}U ({sim['total_return_pct']:+.2f}%)
   交易: {sim['total_trades']}笔
   胜率: {sim['win_rate']:.1f}%
   持仓: {sim['open_positions']}笔
"""
        
        report += f"""
⚙️  策略参数:
   止损: {status['params']['stop_loss_pct']*100:.0f}%
   止盈: {status['params']['take_profit_pct']*100:.0f}%
   买入阈值: {status['params']['buy_threshold']}
   卖出阈值: {status['params']['sell_threshold']}
   仓位: {status['params']['position_size']*100:.0f}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return report


# 全局实例
_engine: Optional[RealtimeEngineV2] = None


def get_engine() -> Optional[RealtimeEngineV2]:
    """获取引擎实例"""
    return _engine


def init_engine(config_name: str = 'default', mode: str = 'simulation',
                data_url: str = 'ws://localhost:8765') -> RealtimeEngineV2:
    """初始化引擎"""
    global _engine
    _engine = RealtimeEngineV2(config_name, mode, data_url)
    return _engine


# 使用示例
if __name__ == '__main__':
    import sys
    
    config_name = sys.argv[1] if len(sys.argv) > 1 else 'optimized_DOGEUSDT_30d'
    mode = sys.argv[2] if len(sys.argv) > 2 else 'simulation'
    
    print(f"启动实时引擎: {config_name} ({mode})")
    
    engine = init_engine(config_name, mode)
    engine.start()
    
    try:
        while True:
            time.sleep(10)
            print(engine.format_status())
    except KeyboardInterrupt:
        engine.stop()
