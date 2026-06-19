class Config:
    # 新增配置项
    DINGTALK_WEBHOOK = os.getenv('DINGTALK_WEBHOOK')
    TRADING_SYMBOLS = ['DOGEUSDT', 'BTCUSDT', 'ETHUSDT']  # 多交易对配置
    LEVERAGE = 20  # 合约杠杆
    CHECK_INTERVAL = 60  # 秒

    # 数据存储路径统一
    HISTORY_DATA_PATH = Path('./data/history').resolve()
    REALTIME_DATA_PATH = Path('./data/realtime').resolve()