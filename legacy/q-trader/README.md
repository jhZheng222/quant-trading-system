# Q-Trader 量化交易系统

## 项目概述
基于Python的加密货币量化交易系统，集成Binance API实现自动化交易。主要功能包括：
- 实时行情数据获取
- 技术指标分析策略
- 风险管理模块
- 自动止损止盈机制

## 环境配置

### 使用Conda创建环境
```bash
conda env create -f environment.yml
conda activate q-trader
```

### 依赖库
- Python 3.9
- pandas/numpy 数据分析
- python-binance API连接
- TA-Lib 技术指标
- Loguru 日志记录

## 配置说明
1. 复制.env模板：
```cp config/.env.example config/.env```
2. 填写Binance API密钥和交易对配置

## 使用示例
```python
# 启动交易系统
python main.py

# 查看实时日志
tail -f logs/trading.log
```

## 风险提示
- 实盘交易前请充分测试
- 建议使用模拟账户操作
- 设置合理的止损止盈比例