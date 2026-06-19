
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Binance API配置
    BINANCE_PUBLIC_WBSOCKET_BASE_URL: str = 'wss://data-stream.binance.vision/ws'
    BINANCE_PUBLIC_API_KEY: str = ''

    # MySQL配置
    MYSQL_HOST: str = '47.121.128.177'
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = 'root'
    MYSQL_PASS: str = 'Zdq123#@!'
    MYSQL_DB: str = 'qtrade'

    # Redis配置
    REDIS_HOST: str = '47.121.128.177'
    REDIS_PORT: int = 6379
    REDIS_PASS: str = 'Zdq123#@!'  # 使用正确的Redis密码
    REDIS_DB: int = 0

    # API配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "QTrade API"
    
    # 安全配置
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # WebSocket订阅配置
    WEBSOCKET_SUBSCRIPTIONS: list = [
        {
            'trade_pair': 'btcusdt',
            'stream_types': ['ticker', 'kline_1m', 'kline_5m', 'kline_15m', 'kline_1h', 'depth']
        },
        {
            'trade_pair': 'ethusdt',
            'stream_types': ['ticker', 'kline_1m', 'kline_5m', 'kline_15m', 'kline_1h', 'depth']
        }
    ]

settings = Settings()