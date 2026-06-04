"""
Gate.io REST API封装 - 支持模拟盘
"""
import ccxt
import time
from typing import Dict, List, Optional
from loguru import logger


class GateRestClient:
    """Gate.io REST API客户端"""
    
    def __init__(self, api_key: str = '', secret_key: str = '', sandbox: bool = False):
        """初始化Gate.io客户端
        
        Args:
            api_key: API Key
            secret_key: Secret Key
            sandbox: 是否使用模拟盘
        """
        config = {
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'rateLimit': 100,
            'timeout': 30000,
        }
        
        # 模拟盘配置
        if sandbox:
            config['sandbox'] = True
            config['urls'] = {
                'api': {
                    'public': 'https://fx-api-testnet.gateio.ws/api/v4',
                    'private': 'https://fx-api-testnet.gateio.ws/api/v4',
                    'futures': 'https://fx-api-testnet.gateio.ws/api/v4',
                },
                'ws': {
                    'public': 'wss://fx-ws-testnet.gateio.ws/v4/ws/usdt',
                    'private': 'wss://fx-ws-testnet.gateio.ws/v4/ws/usdt',
                }
            }
            logger.info("Gate.io 模拟盘客户端初始化完成")
        else:
            logger.info("Gate.io 实盘客户端初始化完成")
        
        self.exchange = ccxt.gateio(config)
        self.sandbox = sandbox
    
    def get_balance(self) -> Dict:
        """获取账户余额"""
        try:
            balance = self.exchange.fetch_balance()
            return {
                'USDT': {
                    'free': balance['USDT']['free'],
                    'used': balance['USDT']['used'],
                    'total': balance['USDT']['total']
                }
            }
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            raise
    
    def get_positions(self) -> List[Dict]:
        """获取持仓信息"""
        try:
            positions = self.exchange.fetch_positions()
            return [{
                'symbol': p['symbol'],
                'side': p['side'],
                'amount': p['contracts'],
                'entryPrice': p['entryPrice'],
                'markPrice': p['markPrice'],
                'unrealizedPnl': p['unrealizedPnl'],
                'leverage': p['leverage'],
                'liquidationPrice': p['liquidationPrice'],
                'marginMode': p['marginMode'],
            } for p in positions if p['contracts'] > 0]
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            raise
    
    def get_klines(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List:
        """获取K线数据"""
        try:
            klines = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return klines
        except Exception as e:
            logger.error(f"获取K线失败 {symbol} {timeframe}: {e}")
            raise
    
    def get_ticker(self, symbol: str) -> Dict:
        """获取实时行情"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': ticker['symbol'],
                'last': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'high': ticker['high'],
                'low': ticker['low'],
                'volume': ticker['baseVolume'],
                'change': ticker['percentage'],
                'timestamp': ticker['timestamp']
            }
        except Exception as e:
            logger.error(f"获取行情失败 {symbol}: {e}")
            raise
    
    def get_depth(self, symbol: str, limit: int = 20) -> Dict:
        """获取深度数据"""
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)
            return {
                'bids': orderbook['bids'][:limit],
                'asks': orderbook['asks'][:limit],
                'timestamp': orderbook['timestamp']
            }
        except Exception as e:
            logger.error(f"获取深度失败 {symbol}: {e}")
            raise
    
    def get_funding_rate(self, symbol: str) -> Dict:
        """获取资金费率"""
        try:
            funding = self.exchange.fetch_funding_rate(symbol)
            return {
                'symbol': funding['symbol'],
                'rate': funding['fundingRate'],
                'nextTime': funding['fundingDatetime'],
                'timestamp': funding['timestamp']
            }
        except Exception as e:
            logger.error(f"获取资金费率失败 {symbol}: {e}")
            raise
    
    def set_leverage(self, symbol: str, leverage: int, side: str = None) -> Dict:
        """设置杠杆"""
        try:
            result = self.exchange.set_leverage(leverage, symbol)
            logger.info(f"设置杠杆成功 {symbol} {leverage}x")
            return result
        except Exception as e:
            logger.error(f"设置杠杆失败 {symbol}: {e}")
            raise
    
    def create_order(self, symbol: str, side: str, amount: float, 
                     price: float = None, order_type: str = 'market',
                     stop_loss: float = None, take_profit: float = None) -> Dict:
        """创建订单"""
        try:
            # 创建主订单
            if order_type == 'market':
                order = self.exchange.create_order(symbol, 'market', side, amount)
            else:
                order = self.exchange.create_order(symbol, 'limit', side, amount, price)
            
            logger.info(f"创建订单成功 {symbol} {side} {amount} @ {price or 'market'}")
            
            # 设置止损止盈
            if stop_loss or take_profit:
                self._set_stop_loss_take_profit(symbol, side, amount, stop_loss, take_profit)
            
            return order
        except Exception as e:
            logger.error(f"创建订单失败 {symbol}: {e}")
            raise
    
    def _set_stop_loss_take_profit(self, symbol: str, side: str, amount: float,
                                   stop_loss: float = None, take_profit: float = None):
        """设置止损止盈"""
        try:
            # 止损单
            if stop_loss:
                sl_side = 'sell' if side == 'buy' else 'buy'
                sl_params = {
                    'stopPrice': stop_loss,
                    'triggerPrice': stop_loss,
                }
                self.exchange.create_order(symbol, 'market', sl_side, amount, params=sl_params)
                logger.info(f"设置止损 {symbol} @ {stop_loss}")
            
            # 止盈单
            if take_profit:
                tp_side = 'sell' if side == 'buy' else 'buy'
                tp_params = {
                    'stopPrice': take_profit,
                    'triggerPrice': take_profit,
                }
                self.exchange.create_order(symbol, 'market', tp_side, amount, params=tp_params)
                logger.info(f"设置止盈 {symbol} @ {take_profit}")
                
        except Exception as e:
            logger.error(f"设置止损止盈失败 {symbol}: {e}")
            raise
    
    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """取消订单"""
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            logger.info(f"取消订单成功 {symbol} {order_id}")
            return result
        except Exception as e:
            logger.error(f"取消订单失败 {symbol} {order_id}: {e}")
            raise
    
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """获取未成交订单"""
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            return [{
                'id': o['id'],
                'symbol': o['symbol'],
                'side': o['side'],
                'amount': o['amount'],
                'price': o['price'],
                'status': o['status'],
                'timestamp': o['timestamp']
            } for o in orders]
        except Exception as e:
            logger.error(f"获取未成交订单失败: {e}")
            raise
    
    def get_trades(self, symbol: str, limit: int = 50) -> List[Dict]:
        """获取成交历史"""
        try:
            trades = self.exchange.fetch_my_trades(symbol, limit=limit)
            return [{
                'id': t['id'],
                'symbol': t['symbol'],
                'side': t['side'],
                'amount': t['amount'],
                'price': t['price'],
                'cost': t['cost'],
                'fee': t['fee'],
                'timestamp': t['timestamp']
            } for t in trades]
        except Exception as e:
            logger.error(f"获取成交历史失败 {symbol}: {e}")
            raise