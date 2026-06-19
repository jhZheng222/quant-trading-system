import { ref, reactive, onMounted, onUnmounted } from 'vue';
console.log('=== binanceWebSocket.js 文件开始加载 ===');

// 导入技术分析服务
import { technicalAnalysisService } from './technicalAnalysisService';

// 创建简化的Binance WebSocket服务 - 单例模式
class BinanceWebSocketService {
  static getInstance() {
    if (!BinanceWebSocketService.instance) {
      BinanceWebSocketService.instance = new BinanceWebSocketService();
    }
    return BinanceWebSocketService.instance;
  }

  constructor() {
    try {
      // 初始化响应式数据供Vue组件使用
    this.intervalMap = {
      '1m': 60 * 1000,
      '5m': 5 * 60 * 1000,
      '15m': 15 * 60 * 1000,
      '30m': 30 * 60 * 1000,
      '1h': 60 * 60 * 1000,
      '4h': 4 * 60 * 60 * 1000,
      '1d': 24 * 60 * 60 * 1000
    }
    this.historicalDataLoaded = ref(false)
    this.errorMessage = ref('')
    this.subscribedSymbol = ref('BTCUSDT')
    this.selectedSymbol = ref('BTCUSDT')
    this.interval = ref('1h')
    this.selectedInterval = ref('1h')
    this.priceData = ref({})
    this.klineData = ref([]);
    this.tradeHistory = ref([])
    this.orderBook = ref({ bids: [], asks: [] })
    this.state = reactive({ connectionStatus: 'disconnected' })
    this.log('=== BinanceWebSocketService 初始化流程开始 ===');
    this.log(`当前订阅交易对: ${this.subscribedSymbol.value}, 时间间隔: ${this.interval.value}`);
    this.log('开始预加载历史数据...');
    this.fetchHistoricalKlines(this.subscribedSymbol.value, this.interval.value).then(data => {
      this.log(`预加载历史数据完成，共${data.length}条记录`);
    }).catch(error => {
      this.log(`预加载历史数据失败: ${error.message}`);
    });
    this.log(`构造函数调用: this=${JSON.stringify(this, (k,v) => typeof v === 'function' ? 'function' : v).substring(0, 100)}...`);
    this.log(`技术分析服务加载状态: ${!!technicalAnalysisService}, 类型=${typeof technicalAnalysisService}`);
    this.log(`响应式变量初始化结果: `+
      `subscribedSymbol=${this.subscribedSymbol.value}[${typeof this.subscribedSymbol.value}], `+
      `interval=${this.interval.value}[${typeof this.interval.value}]`);
    this.log(`=== 初始化流程第一阶段完成 ===`);

    // WebSocket配置
    this.wsUrl = 'wss://data-stream.binance.vision/ws';
    this.socket = null
    this.reconnectTimeout = null
    this.heartbeatInterval = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.streams = []
    this.listeners = new Map() // 存储监听器
    this.generateStreams();
      // 初始化时获取历史数据
      this.fetchHistoricalKlines(this.subscribedSymbol.value, this.interval.value)
        .then(historicalData => {
          if (historicalData.length > 0) {
            this.klineData.value = historicalData;
        // 将历史K线数据添加到技术分析服务
        historicalData.forEach(kline => {
          technicalAnalysisService.addKlineData(this.subscribedSymbol.value, this.interval.value, kline);
        });
        this.log(`初始化加载${historicalData.length}条历史K线数据`);
      } else {
        this.log('未获取到历史数据，使用默认数据填充');
        // 使用默认数据填充
        this.klineData.value = Array(20).fill().map((_, i) => ({
          t: Date.now() - (20 - i) * this.getIntervalMs(this.interval.value),
          o: 0, h: 0, l: 0, c: 0, v: 0
        }));
      }
      this.historicalDataLoaded.value = true;
        });
          // 已在上方获取过历史数据，此处无需重复调用
        this.log('历史数据加载流程已完成');
    } catch (error) {
      console.error('BinanceWebSocketService初始化失败:', error);
      this.log(`初始化错误: ${error.message}`);
      this.errorMessage.value = `服务初始化失败: ${error.message}`;
    }
  }

  // 日志输出方法
  log(message) {
    console.log(`[BinanceWebSocket] ${message}`);
  }

  // 添加监听器方法
  addListener(symbol, callback, interval = '', type = 'kline') {
    const key = `${symbol}-${interval}-${type}`;
    if (!this.listeners.has(key)) {
      this.listeners.set(key, []);
    }
    this.listeners.get(key).push(callback);
  }

  // 触发监听器方法
  triggerListeners(symbol, data, interval = '', type) {
    const key = `${symbol}-${interval}-${type}`;
    if (this.listeners.has(key)) {
      this.listeners.get(key).forEach(listener => {
        try {
          listener(data);
        } catch (error) {
          console.error(`Listener error for ${key}:`, error);
        }
      });
    }
  }

  // 获取历史K线数据
  async fetchHistoricalKlines(symbol, interval, limit = 200) {
    this.log(`开始执行fetchHistoricalKlines: symbol=${symbol}, interval=${interval}, limit=${limit}`);
    try {
      this.log(`正在获取历史K线数据: ${symbol} ${interval}, limit=${limit}`);
      const url = `https://data-api.binance.vision/api/v3/klines?symbol=${symbol.toUpperCase()}&interval=${interval}&limit=${limit}`;
      this.log(`历史数据请求URL: ${url}`);
      let retries = 3;
    let response;
    while (retries > 0) {
      try {
        const url = `https://data-api.binance.vision/api/v3/klines?symbol=${symbol.toUpperCase()}&interval=${interval}&limit=${limit}`;
          this.log(`请求已发送: ${url}`);
          this.log(`请求参数: symbol=${symbol.toUpperCase()}, interval=${interval}, limit=${limit}`);
          response = await fetch(url);
        this.log(`API响应状态: ${response.status} ${response.statusText}`);
          this.log(`响应内容类型: ${response.headers.get('content-type')}`);
        if (!response.ok) throw new Error(`HTTP error: ${response.status} ${response.statusText}`);
        break;
      } catch (error) {
        retries--;
        this.log(`获取历史数据失败，剩余重试次数: ${retries}`);
        if (retries === 0) throw error;
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
      const data = await response.json();
          this.log(`原始API响应数据长度: ${data.length}条`);
          if (data.length > 0) this.log(`第一条数据: ${JSON.stringify(data[0])}`);
      this.log(`获取到${data.length}条历史K线数据`);
      console.log('历史K线原始数据:', data);
      // 先解析数据再过滤无效值
return data.map(item => ({
        t: item[0], // 时间戳
        o: parseFloat(item[1]), // 开盘价
        h: parseFloat(item[2]), // 最高价
        l: parseFloat(item[3]), // 最低价
        c: parseFloat(item[4]), // 收盘价
        v: parseFloat(item[5])  // 成交量
      })).filter(kline => kline.o > 0 && kline.h > 0 && kline.l > 0 && kline.c > 0 && kline.t > 1609459200000 && kline.t < Date.now() + 86400000); // 过滤时间戳在2021年之后且不超过未来24小时的有效数据
    } catch (error) {
      this.log(`历史数据获取失败: ${error.message}`);
      this.errorMessage.value = `历史数据加载失败: ${error.message}`;
      this.log(`历史数据获取详细错误: ${JSON.stringify(error, Object.getOwnPropertyNames(error))}`);
      return [];
    }
  }

  // 建立WebSocket连接
  generateStreams() {
      const symbol = this.subscribedSymbol.value.toLowerCase()
      const interval = this.interval.value
      this.streams = [
        `${symbol}@kline_${interval}`,
        `${symbol}@ticker`,
      ]
    }

  async connect() {
    if (this.socket) {
      this.socket.close(1000, 'Intentional close');
    }
    this.state.connectionStatus = 'connecting'
    // 等待历史数据加载完成
      if (!this.historicalDataLoaded.value) {
        this.log('等待历史数据加载...');
        await Promise.race([
          new Promise(resolve => {
            const checkLoaded = setInterval(() => {
              if (this.historicalDataLoaded.value) {
                clearInterval(checkLoaded);
                resolve('loaded');
              }
            }, 100);
          }),
          new Promise(resolve => {
            setTimeout(() => {
              resolve('timeout');
            }, 10000);
          })
        ]).then(result => {
          if (result === 'timeout') {
            this.log('历史数据加载超时，继续连接WebSocket');
          }
        });
      }

      this.socket = new WebSocket(this.wsUrl);

    this.socket.onopen = () => {
      this.state.connectionStatus = 'connected'
      this.isConnected = true;
      this.reconnectAttempts = 0
      // 连接成功后获取历史K线数据
      this.log('WebSocket连接成功，开始获取历史K线数据');
      this.fetchHistoricalKlines(this.subscribedSymbol.value, this.interval.value).then(historicalData => {
        if (historicalData.length > 0) {
          this.klineData.value = historicalData;
          this.log(`成功加载${historicalData.length}条历史K线数据`);
        }
      });
      this.log('=== WebSocket连接成功 ===');
      this.log(`连接状态: ${this.state.connectionStatus}, isConnected=${this.isConnected}`);
      this.log(`订阅的数据流: ${JSON.stringify(this.streams)}`);
      this.subscribe();
      this.startHeartbeat();
    };

    this.socket.onmessage = (event) => {
      // this.log(`接收到原始消息: ${event.data.substring(0, 100)}...`); // 记录前100字符
      try {
        const data = JSON.parse(event.data);
        // 忽略心跳响应
        if (data.e !== 'heartbeat') {
          this.handleMessage(data);
          this.log(`处理消息类型: ${data.e}`);
        }
      } catch (error) {
        this.log(`消息解析错误: ${error.message}, 原始数据: ${event.data}`);
        if (typeof this.errorMessage === 'string') {
          this.errorMessage = ref('');
        }
        this.errorMessage.value = `数据解析错误: ${error.message}`
      }
    };

    this.socket.onclose = (event) => {
      this.isConnected = false;
      this.state.connectionStatus = 'disconnected';
      this.stopHeartbeat();
      this.log(`连接关闭: 代码=${event.code}, 原因=${event.reason}, 干净关闭=${event.wasClean}`);
      // 仅在非故意关闭时重连
      if (event.code !== 1000) {
        this.log(`非预期关闭，尝试重连(${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.reconnect();
      }
    }

    this.socket.onerror = (error) => {
      this.log(`WebSocket错误: ${JSON.stringify(error)}`);
      if (typeof this.errorMessage === 'string') {
        this.errorMessage = ref('');
      }
      this.errorMessage.value = `连接错误: ${error.message || '未知错误'}`
      this.state.connectionStatus = 'error'
    };
  }

  // 订阅数据流
  subscribe() {
    if (!this.isConnected || !this.socket) return;

    const subscribeMessage = {
      method: 'SUBSCRIBE',
      params: this.streams,
      id: Date.now()
    };

    this.socket.send(JSON.stringify(subscribeMessage));
    this.log(`已订阅数据流: ${this.streams.join(', ')}`);
  }

  // 取消订阅
  unsubscribe() {
    if (!this.isConnected || !this.socket) return;

    const unsubscribeMessage = {
      method: 'UNSUBSCRIBE',
      params: this.streams,
      id: Date.now()
    };

    this.socket.send(JSON.stringify(unsubscribeMessage));
    this.log(`已取消订阅: ${this.streams.join(', ')}`);
  }

  // 更新订阅配置
  async updateSubscription(symbol, interval) {
    if (!symbol || !interval || symbol === this.subscribedSymbol.value && interval === this.interval.value) {
      return;
    }

    this.unsubscribe();
    this.log(`更新订阅前的值: subscribedSymbol=${this.subscribedSymbol.value}, interval=${this.interval.value}`);
    this.subscribedSymbol.value = symbol;
    this.interval.value = interval;
    this.selectedSymbol.value = symbol;
    this.selectedInterval.value = interval;
    this.log(`更新订阅后的值: subscribedSymbol=${this.subscribedSymbol.value}, interval=${this.interval.value}`);
    this.generateStreams();
    // 重置历史数据状态并获取新交易对数据
    this.historicalDataLoaded.value = false;
    this.klineData.value = [];
    this.fetchHistoricalKlines(symbol.toUpperCase(), interval)
      .then(historicalData => {
        if (historicalData.length > 0) {
          this.klineData.value = historicalData;
          this.log(`已加载${historicalData.length}条历史K线数据`);
        } else {
          this.log('警告: 未获取到有效历史数据，技术指标将无法计算');
          this.klineData.value = []; // 不使用零值填充，避免影响指标计算
        }
        this.historicalDataLoaded.value = true;
      });
    // 重新连接WebSocket以应用新订阅
    if (this.socket) {
      this.disconnect();
      this.connect();
    }
    this.log(`已更新订阅: ${symbol} ${interval}`);
  }

  // 时间间隔转换为毫秒
  getIntervalMs(interval) {
    return this.intervalMap[interval] || 3600000;
  }

  // 合并历史数据和实时数据
  mergeKlineData(newData) {
    if (!this.klineData.value.length) {
      this.klineData.value = newData;
      return;
    }

    const lastTime = this.klineData.value[this.klineData.value.length - 1].t;
    const filteredNewData = newData.filter(item => item.t > lastTime);

    if (filteredNewData.length > 0) {
      this.klineData.value = [...this.klineData.value, ...filteredNewData];
      // 添加实时K线数据到技术分析服务
      filteredNewData.forEach(kline => {
        technicalAnalysisService.addKlineData(this.subscribedSymbol.value, this.interval.value, kline);
      });
      // 保持数据量在合理范围
      if (this.klineData.value.length > 200) {
        this.klineData.value = this.klineData.value.slice(-200);
      }
      this.log(`合并了${filteredNewData.length}条新K线数据`);
    }
  }

  // 格式化K线数据
  formatKlineData(data) {
    return {
      t: data.k.t,
      o: data.k.o,
      h: data.k.h,
      l: data.k.l,
      c: data.k.c,
      v: data.k.v
    };
  }

  // 处理接收到的消息
  handleMessage(data) {
    // 可以根据需要扩展不同数据类型的处理逻辑
    if (data.e === 'kline') {
      this.mergeKlineData([this.formatKlineData(data)]);
    } else if (data.e === 'trade') {
      this.handleTradeData(data);
    } else if (data.e === 'aggTrade') {
      this.handleAggTradeData(data);
    } else if (data.e === '24hrTicker') {
      this.handleTickerData(data);
    } else if (data.e === 'depthUpdate') {
      this.handleDepthData(data);
    }
  }

  // 处理市场深度数据
  handleDepthData(data) {
    // this.log(`接收到市场深度数据: ${JSON.stringify(data)}`);
    // 处理买单和卖单数据
    const bids = data.bids.map(([price, quantity]) => ({ price: parseFloat(price), quantity: parseFloat(quantity) }));
    const asks = data.asks.map(([price, quantity]) => ({ price: parseFloat(price), quantity: parseFloat(quantity) }));
    this.orderBook.value = { bids, asks };
    // this.log(`深度数据更新: 买单${bids.length}条, 卖单${asks.length}条`);
    // 触发深度数据监听器
    this.triggerListeners(data.s, this.orderBook.value, '', 'depth');
  }

  // K线数据处理
  handleKlineData(data) {
    const kline = data.k;
    // this.log(`原始K线数据格式: ${JSON.stringify(kline, null, 2)}`);
    if (!kline || typeof kline.s !== 'string' || typeof kline.i !== 'string' || !kline.c) {
      this.log('无效的K线数据格式');
      return;
    }
    this.log(`K线数据: ${kline.s} ${kline.i} ${new Date(kline.t).toLocaleString()} ${kline.o}/${kline.c}`);

    // 更新响应式K线数据
    const klineObj = {
      symbol: kline.s,
      interval: kline.i,
      time: new Date(kline.t),
      open: parseFloat(kline.o),
      high: parseFloat(kline.h),
      low: parseFloat(kline.l),
      close: parseFloat(kline.c),
      volume: parseFloat(kline.v),
      isClosed: kline.x
    };
    // this.log(`K线数据处理完成: ${JSON.stringify(klineObj, null, 2)}`);

    // 保持最近的100条K线数据
    // 安全处理K线数据，防止undefined错误
    const currentData = this.klineData.value || [];
    this.klineData.value = [...currentData.slice(-99), klineObj];
    // 触发监听器
        this.triggerListeners(kline.s, klineObj, kline.i, 'kline');
    try {
      // 添加默认值回退并增强日志
      const rawSymbol = this.subscribedSymbol.value;
      const rawInterval = this.interval.value;
      // this.log(`处理K线数据前的原始参数: rawSymbol=${rawSymbol}, rawInterval=${rawInterval}`);
      const symbol = rawSymbol || kline.s || 'BTCUSDT'; // 使用K线数据中的symbol作为备选
      const interval = rawInterval || kline.i || '1h'; // 使用K线数据中的interval作为备选
      // this.log(`应用默认值后的参数: symbol=${symbol}, interval=${interval}`);
      if (!symbol || !interval) {
        this.log(`技术指标计算失败: 无效的符号(${symbol})或时间间隔(${interval}) - 完整对象: ${JSON.stringify({subscribedSymbol: this.subscribedSymbol, interval: this.interval})}`);
        this.errorMessage.value = `技术指标计算失败: 符号=${symbol}, 时间间隔=${interval}, subscribedSymbol类型=${typeof this.subscribedSymbol}, interval类型=${typeof this.interval}`;
        return;
      }
      // 最终参数验证
      this.log(`即将调用技术分析服务: symbol=${symbol}, interval=${interval}, kline=${JSON.stringify(kline).substring(0, 50)}...`);
      if (typeof symbol !== 'string' || typeof interval !== 'string') {
        this.log(`无效的参数类型: symbol=${typeof symbol}, interval=${typeof interval}`);
        this.errorMessage.value = `参数错误: 符号和时间间隔必须为字符串`;
        return;
      }
      technicalAnalysisService.addKlineData(symbol, interval, kline);
    } catch (error) {
      this.log(`技术分析服务调用失败: ${error.message}`);
      // 确保errorMessage始终是ref对象
      if (typeof this.errorMessage === 'string') {
        this.errorMessage = ref('');
      }
      this.errorMessage.value = `数据处理错误: ${error.message}`;
    }
  }

  // 交易数据处理
  handleTradeData(data) {
    const trade = {
      symbol: data.s,
      price: parseFloat(data.p),
      quantity: parseFloat(data.q),
      time: new Date(data.T),
      isBuyerMaker: data.m
    };
    // this.log(`交易数据: ${trade.symbol} ${trade.price} ${trade.quantity} ${trade.time.toLocaleTimeString()}`);

    // 更新响应式交易历史
    // 安全处理交易历史数据
    this.tradeHistory.value = [trade, ...(this.tradeHistory.value || []).slice(0, 49)];

    // 更新最新价格
    this.priceData.value = { ...this.priceData.value, [trade.symbol]: trade.price };
    // 触发交易数据监听器
    this.triggerListeners(data.s, trade, '', 'trade');
  }

  // 聚合交易数据处理
  handleAggTradeData(data) {
    const aggTrade = {
      symbol: data.s,
      price: parseFloat(data.p),
      quantity: parseFloat(data.q),
      time: new Date(data.T),
      isBuyerMaker: data.m
    };
    // this.log(`聚合交易: ${aggTrade.symbol} ${aggTrade.price} ${aggTrade.quantity}`);
  }

  // 行情数据处理
  handleTickerData(data) {
    // 安全解析数字的辅助函数
const safeParseFloat = (value, fallback = 0) => {
  const num = parseFloat(value);
  return isNaN(num) ? fallback : num;
};

const ticker = {
  symbol: data.s || 'UNKNOWN',
  price: safeParseFloat(data.c),
  change: safeParseFloat(data.p),
  changePercent: safeParseFloat(data.P),
  volume: safeParseFloat(data.v),
  h: safeParseFloat(data.h),
    l: safeParseFloat(data.l),
    o: Math.max(safeParseFloat(data.o), 0.0001),
    c: safeParseFloat(data.c),
  // 添加原始收盘价和开盘价用于计算
  rawClose: data.c || '0',
  rawOpen: data.o || '0',
  openTime: data.O ? new Date(data.O) : new Date(),
  closeTime: data.C ? new Date(data.C) : new Date()
};

// 记录解析错误
if (Object.values(ticker).some(v => v === 0 && data.c !== '0')) {
  this.log(`部分数据解析异常: ${JSON.stringify(data)}`);
}
    this.log(`行情更新: ${ticker.symbol} 价格: ${ticker.price} 变化: ${ticker.change}(${ticker.changePercent}%)`);

    // 更新响应式行情数据
    this.priceData.value = { ...this.priceData.value, [ticker.symbol]: ticker };
    // 触发价格数据监听器
    this.triggerListeners(data.s, ticker, '', 'ticker');
  }

  // 开始心跳检测
  startHeartbeat() {
    this.stopHeartbeat();
    // 每30秒发送一次心跳
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected && this.socket) {
        this.socket.send(JSON.stringify({ method: 'PING' }));
      }
    }, 30000);
  }

  // 停止心跳检测
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  // 重新连接 (带指数退避)
  reconnect() {
    this.disconnect();
  this.state.connectionStatus = 'reconnecting';
  if (this.reconnectAttempts < this.maxReconnectAttempts) {
      const delay = Math.pow(2, this.reconnectAttempts) * 1000;
      this.reconnectTimeout = setTimeout(() => {
        this.reconnectAttempts++;
        this.log(`尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
        this.log('=== 开始建立WebSocket连接 ===');
    this.connect();
      }, delay);
    } else {
      // 确保errorMessage是ref对象
    if (typeof this.errorMessage === 'string') {
      this.errorMessage = ref('');
    }
    this.errorMessage.value = '达到最大重连次数，请检查网络连接';
      this.log('达到最大重连次数');
    }
  }

  // 断开连接
  disconnect() {
    if (this.socket) {
      this.socket.close(1000, 'Intentional close');
      this.socket = null;
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.stopHeartbeat();
    this.state.connectionStatus = 'disconnected'
  }

}
// 初始化单例实例
BinanceWebSocketService.instance = null;
// 导出单例实例
export default BinanceWebSocketService.getInstance();