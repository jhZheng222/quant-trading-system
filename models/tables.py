"""
数据库表结构定义
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Kline(Base):
    """K线数据表"""
    __tablename__ = 'kline'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, comment='交易对')
    timeframe = Column(String(10), nullable=False, comment='时间框架')
    timestamp = Column(DateTime, nullable=False, comment='时间戳')
    open = Column(Float, nullable=False, comment='开盘价')
    high = Column(Float, nullable=False, comment='最高价')
    low = Column(Float, nullable=False, comment='最低价')
    close = Column(Float, nullable=False, comment='收盘价')
    volume = Column(Float, nullable=False, comment='成交量')
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_kline_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp', unique=True),
    )


class FundingRate(Base):
    """资金费率表"""
    __tablename__ = 'funding_rate'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, comment='交易对')
    timestamp = Column(DateTime, nullable=False, comment='时间戳')
    rate = Column(Float, nullable=False, comment='资金费率')
    next_time = Column(DateTime, comment='下次结算时间')
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_funding_symbol_timestamp', 'symbol', 'timestamp', unique=True),
    )


class OpenInterest(Base):
    """持仓量表"""
    __tablename__ = 'open_interest'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, comment='交易对')
    timestamp = Column(DateTime, nullable=False, comment='时间戳')
    interest = Column(Float, nullable=False, comment='持仓量')
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_interest_symbol_timestamp', 'symbol', 'timestamp', unique=True),
    )


class WhaleAddress(Base):
    """大户地址监控表"""
    __tablename__ = 'whale_addresses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String(100), nullable=False, comment='地址')
    chain = Column(String(20), nullable=False, comment='链')
    balance = Column(Float, nullable=False, comment='余额')
    last_updated = Column(DateTime, comment='最后更新时间')
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_whale_address_chain', 'address', 'chain', unique=True),
    )


class LargeTransfer(Base):
    """大额转账表"""
    __tablename__ = 'large_transfers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tx_hash = Column(String(100), nullable=False, comment='交易哈希')
    from_address = Column(String(100), comment='发送地址')
    to_address = Column(String(100), comment='接收地址')
    amount = Column(Float, nullable=False, comment='金额')
    token = Column(String(20), nullable=False, comment='代币')
    timestamp = Column(DateTime, nullable=False, comment='时间戳')
    is_exchange_inflow = Column(Boolean, default=False, comment='是否流入交易所')
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_transfer_tx_hash', 'tx_hash', unique=True),
    )


class SocialSentiment(Base):
    """社交情绪表"""
    __tablename__ = 'social_sentiment'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False, comment='平台')
    symbol = Column(String(20), nullable=False, comment='交易对')
    timestamp = Column(DateTime, nullable=False, comment='时间戳')
    mention_count = Column(Integer, comment='提及次数')
    sentiment_score = Column(Float, comment='情绪得分 (-1到1)')
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_sentiment_platform_symbol_timestamp', 'platform', 'symbol', 'timestamp', unique=True),
    )


class FearGreedIndex(Base):
    """恐惧贪婪指数表"""
    __tablename__ = 'fear_greed_index'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, unique=True, comment='时间戳')
    value = Column(Integer, nullable=False, comment='指数值 (0-100)')
    classification = Column(String(20), comment='分类')
    created_at = Column(DateTime, default=func.now())


class TechnicalIndicator(Base):
    """技术指标表"""
    __tablename__ = 'technical_indicators'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, comment='交易对')
    timeframe = Column(String(10), nullable=False, comment='时间框架')
    timestamp = Column(DateTime, nullable=False, comment='时间戳')
    
    # 移动平均线
    ema_20 = Column(Float, comment='EMA20')
    ema_50 = Column(Float, comment='EMA50')
    ema_200 = Column(Float, comment='EMA200')
    
    # RSI
    rsi_14 = Column(Float, comment='RSI(14)')
    
    # MACD
    macd = Column(Float, comment='MACD')
    macd_signal = Column(Float, comment='MACD信号线')
    macd_hist = Column(Float, comment='MACD柱状图')
    
    # 布林带
    bb_upper = Column(Float, comment='布林带上轨')
    bb_middle = Column(Float, comment='布林带中轨')
    bb_lower = Column(Float, comment='布林带下轨')
    
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_indicator_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp', unique=True),
    )


class TradeSignal(Base):
    """交易信号表"""
    __tablename__ = 'trade_signals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, comment='交易对')
    strategy = Column(String(50), nullable=False, comment='策略名称')
    signal_type = Column(String(10), nullable=False, comment='信号类型 (buy/sell/hold)')
    price = Column(Float, comment='信号价格')
    stop_loss = Column(Float, comment='止损价')
    take_profit = Column(Float, comment='止盈价')
    confidence = Column(Float, comment='置信度 (0-1)')
    reason = Column(String(500), comment='信号原因')
    executed = Column(Boolean, default=False, comment='是否已执行')
    timestamp = Column(DateTime, nullable=False, comment='信号时间')
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_signal_symbol_timestamp', 'symbol', 'timestamp'),
    )


class Order(Base):
    """订单表"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), nullable=False, unique=True, comment='订单ID')
    symbol = Column(String(20), nullable=False, comment='交易对')
    side = Column(String(10), nullable=False, comment='方向 (buy/sell)')
    order_type = Column(String(20), nullable=False, comment='订单类型 (market/limit)')
    amount = Column(Float, nullable=False, comment='数量')
    price = Column(Float, comment='价格')
    stop_loss = Column(Float, comment='止损价')
    take_profit = Column(Float, comment='止盈价')
    status = Column(String(20), nullable=False, comment='订单状态')
    filled_amount = Column(Float, default=0, comment='已成交数量')
    avg_price = Column(Float, comment='成交均价')
    fee = Column(Float, comment='手续费')
    signal_id = Column(Integer, ForeignKey('trade_signals.id'), comment='关联信号ID')
    timestamp = Column(DateTime, nullable=False, comment='订单时间')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class Position(Base):
    """持仓表"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, comment='交易对')
    side = Column(String(10), nullable=False, comment='方向 (long/short)')
    amount = Column(Float, nullable=False, comment='数量')
    entry_price = Column(Float, nullable=False, comment='开仓均价')
    mark_price = Column(Float, comment='标记价格')
    unrealized_pnl = Column(Float, comment='未实现盈亏')
    leverage = Column(Integer, comment='杠杆倍数')
    liquidation_price = Column(Float, comment='强平价')
    margin_mode = Column(String(20), comment='保证金模式')
    timestamp = Column(DateTime, nullable=False, comment='更新时间')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    __table_args__ = (
        Index('idx_position_symbol_side', 'symbol', 'side', unique=True),
    )


class AccountSnapshot(Base):
    """账户快照表"""
    __tablename__ = 'account_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, comment='快照时间')
    total_equity = Column(Float, comment='总权益')
    available_balance = Column(Float, comment='可用余额')
    unrealized_pnl = Column(Float, comment='未实现盈亏')
    margin_used = Column(Float, comment='已用保证金')
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_snapshot_timestamp', 'timestamp', unique=True),
    )