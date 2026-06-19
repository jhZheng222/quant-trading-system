<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage, ElLoading } from 'element-plus'
import binanceService from '../services/binanceWebSocket.js'
import { technicalAnalysisService } from '../services/technicalAnalysisService'
// 导入Chart.js相关库、比例尺和适配器
import { Chart, LinearScale, TimeScale, CategoryScale, Title, Tooltip, Legend } from 'chart.js'
import { CandlestickController, CandlestickElement } from 'chartjs-chart-financial'
import 'chartjs-chart-financial'
import 'chartjs-adapter-date-fns'

// 注册必要的比例尺和插件
Chart.register(LinearScale, TimeScale, CategoryScale, Title, Tooltip, Legend, CandlestickController, CandlestickElement)

// 交易对选择
const selectedSymbol = ref('btcusdt')
const timeInterval = ref('1h')

// 监听交易对变化并更新订阅
watch(selectedSymbol, (newSymbol) => {
  // 清除技术分析服务中旧交易对的缓存数据
  technicalAnalysisService.clearSymbolData(selectedSymbol.value.toUpperCase(), timeInterval.value);
  binanceService.updateSubscription(newSymbol, timeInterval.value);
  // 添加新交易对的数据订阅
  binanceService.addListener(newSymbol.toUpperCase(), (tickerData) => {
    priceData.value = tickerData;
  }, '', 'ticker');
  // 重置所有相关数据
  klineData.value = [];
  priceData.value = { c: '0', o: '0', h: '0', l: '0' };
  indicators.value = { rsi: { '14': 50 }, macd: { histogram: 0 }, bollingerBands: { upper: 0, middle: 0, lower: 0 }, sma: { '5': 0, '10': 0, '20': 0 } };
  predictions.value = null;
  analysisResults.value = {};
  supportResistance.value = {};
  volatilityAlerts.value = [];
  tradingAdvice.value = '';
})

// 监听时间间隔变化并更新订阅
watch(timeInterval, (newInterval) => {
  binanceService.updateSubscription(selectedSymbol.value, newInterval);
})
const availableSymbols = ref(['btcusdt', 'ethusdt', 'solusdt', 'avaxusdt', 'dogeusdt'])
const availableIntervals = ref(['1m', '5m', '15m', '30m', '1h', '4h', '1d'])

// 组件挂载时初始化WebSocket连接
onMounted(() => {
  binanceService.connect();
})

// 直接使用服务中的响应式数据
const priceData = binanceService.priceData
const klineData = binanceService.klineData
const indicators = ref({ rsi: { '14': 50 }, macd: { histogram: 0 }, bollingerBands: { upper: 0, middle: 0, lower: 0 }, sma: { '5': 0, '10': 0, '20': 0 } })
const predictions = ref(null)
const analysisResults = ref({})
const supportResistance = ref({})
const volatilityAlerts = ref([])
const tradingAdvice = ref('')
const marketSentiment = ref(0.5) // 0-1之间的值，表示市场情绪
const loading = ref(false)
const connectionStatus = ref('disconnected')

// 图表实例
let chart = null

// 优化变量
let updateScheduled = false
let lastIndicatorCalculation = 0

// 定时器引用
let statusUpdateTimer = null

onMounted(() => {
  initChart();
  subscribeAllData();
  statusUpdateTimer = setInterval(updateConnectionStatus, 1000);
})

onUnmounted(() => {
  if (statusUpdateTimer) clearInterval(statusUpdateTimer);
  if (chart) chart.destroy();
})

// 监听WebSocket连接状态
const updateConnectionStatus = () => {
  connectionStatus.value = binanceService.isConnected ? 'connected' : 'disconnected'
}

// 初始化图表
const initChart = () => {
  // 确保DOM元素存在
  const canvasElement = document.getElementById('priceChart');
  if (!canvasElement) {
    console.error('Canvas元素未找到，无法初始化图表');
    return;
  }

  const ctx = canvasElement.getContext('2d');
  if (!ctx) {
    console.error('无法获取Canvas上下文');
    return;
  }

  // 销毁已有图表实例
  if (chart) {
    chart.destroy();
  }

  // 初始数据处理
  const initialLabels = klineData.value.map(item => new Date(item.t).toLocaleTimeString());
  const initialPrices = klineData.value.map(item => parseFloat(item.c));

  console.log('klineData: ',klineData.value)
  chart = new Chart(ctx, {
    type: 'candlestick',
    data: {
      labels: initialLabels,
      datasets: [{
        label: `${selectedSymbol.value.toUpperCase()} ${timeInterval.value}`,
        data: klineData.value.map(item => ({x: new Date(item.t), o: parseFloat(item.o), h: parseFloat(item.h), l: parseFloat(item.l), c: parseFloat(item.c)})),
        upColor: '#42b983',
          downColor: '#f56c6c',
          borderColor: '#42b983',
          borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
        },
        tooltip: {
          mode: 'index',
          intersect: false,
        }
      },
      scales: {
        x: {
          type: 'time',
          time: {
            unit: timeInterval.value.includes('m') ? 'minute' : timeInterval.value.includes('h') ? 'hour' : 'day',
            displayFormats: {
              minute: 'HH:mm',
              hour: 'MM/dd HH:mm',
              day: 'MM/dd'
            }
          },
          grid: {
            display: false
          },
          title: {
            display: true,
            text: '时间'
          }
        },
        y: {
          position: 'right',
          grid: {
            color: 'rgba(0, 0, 0, 0.05)'
          },
          title: {
            display: true,
            text: '价格 (USD)'
          }
        }
      }
    }
  });
}

// 更新图表数据
  const updateChart = () => {
    if (!chart) return;

    // 处理K线数据并更新图表

    chart.data.datasets[0].data = klineData.value.map(d => ({x: new Date(d.t), o: parseFloat(d.o), h: parseFloat(d.h), l: parseFloat(d.l), c: parseFloat(d.c)}));
    chart.update();
  }

  // 监听K线数据变化自动更新图表
  watch(klineData, (newVal) => {
  console.log(`klineData变化: 新长度=${newVal.length}`);
  if (newVal.length > 0) {
    calculateIndicators(selectedSymbol.value, timeInterval.value);
    if (chart) {
      updateChart();
    }
  }
}, { deep: true });

// 定义数据存储变量
const tradeData = ref([])
const depthData = ref({})
const tickerData = ref(null)

// 订阅所有数据类型
const subscribeAllData = async () => {
    loading.value = true;
    const loadingInstance = ElLoading.service({ text: '正在获取数据...' });
    try {
        // 重置数据
        klineData.value = [];
        tradeData.value = [];
        depthData.value = {};
        tickerData.value = null;
        priceData.value = null;

        // 使用 uppercase 符号确保与Binance数据匹配
        const upperSymbol = selectedSymbol.value.toUpperCase();
        // 更新订阅配置
        binanceService.updateSubscription(upperSymbol, timeInterval.value);

        // 订阅K线数据
        binanceService.addListener(upperSymbol, (data) => {
            klineData.value.push(data);
            if (klineData.value.length > 100) klineData.value.shift();
        }, timeInterval.value, 'kline');

        // 订阅价格数据
        binanceService.addListener(upperSymbol, (data) => {
            priceData.value = data;
        }, '', 'ticker');
    } catch (error) {
        console.error('订阅数据时发生错误:', error);
        ElMessage.error('数据订阅失败: ' + error.message);
    } finally {
        loading.value = false;
        loadingInstance.close();
    }

            // 图表更新优化
            if (chart && !updateScheduled) {
                updateScheduled = true;
                window.requestAnimationFrame(() => {
                    chart.data.datasets[0].data = klineData.value.map(d => ({
                        x: new Date(d.t), o: parseFloat(d.o), h: parseFloat(d.h),
                        l: parseFloat(d.l), c: parseFloat(d.c)
                    }));
                    chart.update('none');
                    updateScheduled = false;
                });
            }

            // 技术指标计算频率控制
            const now = Date.now();
            if (now - lastIndicatorCalculation > 1000) {
                calculateIndicators();
                lastIndicatorCalculation = now;
            }

        // 订阅其他数据类型
        const upperSymbol = selectedSymbol.value?.toUpperCase() || '';
        binanceService.addListener(upperSymbol, (data) => {
            tradeData.value.push(data);
            if (tradeData.value.length > 50) tradeData.value.shift();
        }, '', 'trade');

        binanceService.addListener(upperSymbol, (data) => {
            depthData.value = data;
        }, '', 'depth');

        binanceService.addListener(upperSymbol, (data) => {
            tickerData.value = data;
        }, '', 'ticker');

        // 时间周期转换为毫秒的映射
        const intervalMap = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '30m': 30 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        };
        // 添加分号确保对象定义正确结束;

        // 设置定时任务定期执行技术分析
        try {
            setInterval(() => {
                if (klineData.value.length > 0) {
                    const results = technicalAnalysisService.analyze(klineData.value);
                    analysisResults.value = results;
                    loading.value = false;
                    loadingInstance.close();
                }
            }, intervalMap[timeInterval.value] || 3600000);
        } catch (error) {
            console.error('订阅数据时发生错误:', error);
            loading.value = false;
            loadingInstance.close();
            ElMessage.error('数据加载失败，请重试');
        } finally {
            // Ensure loading state is cleaned up even if there's an error
            if (loadingInstance) {
                loading.value = false;
                loadingInstance.close();
            }
        }
};

// 计算技术指标
const calculateIndicators = (symbol, interval) => {
  if (klineData.value.length < 10) {
    console.log('K线数据不足，无法计算技术指标');
    return;
  }

  // 跟踪已添加的K线数据索引
  const lastAddedIndex = ref(-1);

  // 将K线数据传递给技术分析服务
  if (!symbol || !interval) {
    console.log(`技术指标计算失败: 无效的符号(${symbol})或时间间隔(${interval})`);
    return;
  }

  // 只添加新的K线数据
  if (klineData.value.length > lastAddedIndex.value + 1) {
    for (let i = lastAddedIndex.value + 1; i < klineData.value.length; i++) {
      technicalAnalysisService.addKlineData(symbol.toUpperCase(), interval, klineData.value[i]);
    }
    lastAddedIndex.value = klineData.value.length - 1;
  }

  // 从技术分析服务获取计算好的指标
  indicators.value = technicalAnalysisService.getIndicators(selectedSymbol.value.toUpperCase(), timeInterval.value) || {
    rsi: { '14': 50 },
    macd: { histogram: 0, macdLine: 0, signalLine: 0 },
    bollingerBands: { upper: 0, middle: 0, lower: 0 },
    sma: { '5': 0, '10': 0, '20': 0 }
  }

  // 生成交易建议
  generateTradingAdvice()

  // 检测异常波动
  detectVolatility()

  // 预测价格走势
  predictPrice()

  // 计算支撑位和压力位
  calculateSupportResistance()
}

// 生成交易建议
const generateTradingAdvice = () => {
  // 简单的交易建议逻辑
  if (!indicators.value.rsi || !indicators.value.macd || !indicators.value.rsi['14']) return

  const rsi = indicators.value.rsi['14']
  const macd = indicators.value.macd

  if (rsi > 70 && macd.histogram < 0) {
    tradingAdvice.value = '超买，考虑卖出'
  } else if (rsi < 30 && macd.histogram > 0) {
    tradingAdvice.value = '超卖，考虑买入'
  } else if (macd.macdLine > macd.signalLine && macd.histogram > 0) {
    tradingAdvice.value = '看涨，持有'
  } else if (macd.macdLine < macd.signalLine && macd.histogram < 0) {
    tradingAdvice.value = '看跌，观望'
  } else {
    tradingAdvice.value = '趋势不明，观望'
  }
}

// 检测异常波动
const detectVolatility = () => {
  if (klineData.value.length < 2) return

  const lastPrice = parseFloat(klineData.value[klineData.value.length - 1].c)
  const prevPrice = parseFloat(klineData.value[klineData.value.length - 2].c)
  const changePercent = Math.abs((lastPrice - prevPrice) / prevPrice * 100)

  // 如果价格变动超过2%，生成提醒
  if (changePercent > 2) {
    const direction = lastPrice > prevPrice ? '上涨' : '下跌'
    const alert = {
      id: Date.now(),
      symbol: selectedSymbol.value.toUpperCase(),
      direction,
      changePercent: changePercent.toFixed(2),
      time: new Date().toLocaleTimeString()
    }

    volatilityAlerts.value.push(alert)

    // 限制提醒数量
    if (volatilityAlerts.value.length > 5) {
      volatilityAlerts.value.shift()
    }

    // 显示通知
    ElMessage.warning(`${selectedSymbol.value.toUpperCase()} ${direction} ${changePercent.toFixed(2)}%`)
  }
}

// 预测价格走势
const predictPrice = () => {
  // 简单的预测逻辑
  if (klineData.value.length < 5) return

  // 提取最近5个收盘价
  const recentCloses = klineData.value.slice(-5).map(d => parseFloat(d.c))

  // 计算平均变化
  let avgChange = 0
  for (let i = 1; i < recentCloses.length; i++) {
    avgChange += (recentCloses[i] - recentCloses[i-1]) / recentCloses[i-1]
  }
  avgChange /= (recentCloses.length - 1)

  // 预测未来价格
  const lastPrice = recentCloses[recentCloses.length - 1]
  const predictedPrice = lastPrice * (1 + avgChange * 2)
  const trend = avgChange > 0 ? '上涨' : '下跌'

  predictions.value = {
    predictedPrice: predictedPrice.toFixed(2),
    trend,
    confidence: Math.min(Math.abs(avgChange) * 100, 90).toFixed(1)
  }
}

// 计算支撑位和压力位
const calculateSupportResistance = () => {
  if (klineData.value.length < 10) return

  // 提取最近10个K线的最高价和最低价
  const recentHighs = klineData.value.slice(-10).map(d => parseFloat(d.h))
  const recentLows = klineData.value.slice(-10).map(d => parseFloat(d.l))

  // 简单计算支撑位和压力位
  supportResistance.value = {
    support: Math.min(...recentLows).toFixed(2),
    resistance: Math.max(...recentHighs).toFixed(2)
  }
}

// 切换交易对
const changeSymbol = (symbol) => {
  selectedSymbol.value = symbol
}

// 切换时间周期
const changeInterval = (interval) => {
  timeInterval.value = interval
}

// 生命周期钩子
onMounted(() => {
  // 连接WebSocket
  binanceService.connect()

  // 定期更新连接状态
  statusUpdateTimer = setInterval(updateConnectionStatus, 1000)

  // 等待连接成功后再订阅数据
  const connectionCheckInterval = setInterval(() => {
    if (binanceService.state.connectionStatus === 'connected') {
      clearInterval(connectionCheckInterval);
      subscribeAllData();
      ElMessage.success('已成功连接到Binance数据服务');
      // 数据加载后初始化图表
      if (klineData.value.length > 0) {
        initChart();
      } else {
        // 监听K线数据变化后初始化图表
        const unwatch = watch(klineData, (newVal) => {
            if (newVal.length > 0) {
              nextTick(() => {
                initChart();
                unwatch();
              });
            }
          });
      }
    } else if (binanceService.state.connectionStatus === 'error') {
      clearInterval(connectionCheckInterval);
      ElMessage.error('连接Binance数据服务失败，请刷新页面重试');
    }
  }, 500);

  // 清理函数
  onUnmounted(() => {
    clearInterval(statusUpdateTimer);
    clearInterval(connectionCheckInterval);
    statusUpdateTimer = null;
    if (binanceService && binanceService.resetConnection) {
      binanceService.resetConnection();
    }
    if (chart) {
      chart.destroy();
      chart = null;
    }
  });
})
</script>

<template>
  <div class="home-page min-h-screen bg-gray-50 font-inter">
    <!-- 导航栏 -->
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="container mx-auto px-4 py-3 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <i class="fa fa-line-chart text-primary text-2xl"></i>
          <h1 class="text-xl font-bold text-dark">QTradeAnalysis</h1>
        </div>

        <div class="hidden md:flex items-center space-x-6">
          <a href="#market" class="text-gray-700 hover:text-primary transition-colors duration-200">市场概览</a>
          <a href="#chart" class="text-gray-700 hover:text-primary transition-colors duration-200">价格图表</a>
          <a href="#indicators" class="text-gray-700 hover:text-primary transition-colors duration-200">技术指标</a>
          <a href="#analysis" class="text-gray-700 hover:text-primary transition-colors duration-200">分析建议</a>
        </div>

        <div class="flex items-center space-x-3">
          <div class="relative">
            <span class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
              <i class="fa fa-search text-gray-400"></i>
            </span>
            <input type="text" placeholder="搜索交易对..." class="pl-10 pr-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200 text-sm">
          </div>

          <div class="relative group">
            <button class="flex items-center space-x-2 bg-white border border-gray-300 rounded-lg px-3 py-2 hover:bg-gray-50 transition-colors duration-200">
              <img src="https://picsum.photos/24/24" alt="用户头像" class="w-6 h-6 rounded-full object-cover">
              <span class="hidden md:inline-block text-sm font-medium">用户名</span>
              <i class="fa fa-angle-down text-gray-500"></i>
            </button>
            <div class="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-2 z-10 invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-all duration-200 transform translate-y-2 group-hover:translate-y-0">
              <a href="#profile" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors duration-200">个人资料</a>
              <a href="#settings" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors duration-200">系统设置</a>
              <div class="border-t border-gray-100 my-1"></div>
              <a href="/login" class="block px-4 py-2 text-sm text-danger hover:bg-gray-100 transition-colors duration-200">退出登录</a>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="container mx-auto px-4 py-6">
      <!-- 连接状态 -->
      <div class="mb-4 flex items-center justify-end">
        <div class="flex items-center space-x-2">
          <span class="inline-block w-2 h-2 rounded-full" :class="connectionStatus === 'connected' ? 'bg-success' : 'bg-danger pulse-animation'"></span>
          <span class="text-sm text-gray-600">
            {{ connectionStatus === 'connected' ? '已连接到Binance' : '正在连接...' }}
          </span>
        </div>
      </div>

      <!-- 交易对和时间周期选择 -->
      <div class="bg-white rounded-xl shadow-sm p-4 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex items-center space-x-2">
          <label class="text-sm font-medium text-gray-700">交易对:</label>
          <select v-model="selectedSymbol" @change="changeSymbol(selectedSymbol)" class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200">
            <option v-for="symbol in availableSymbols" :key="symbol" :value="symbol">{{ symbol.toUpperCase() }}</option>
          </select>
        </div>

        <div class="flex items-center space-x-2">
          <label class="text-sm font-medium text-gray-700">时间周期:</label>
          <select v-model="timeInterval" @change="changeInterval(timeInterval)" class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200">
            <option v-for="interval in availableIntervals" :key="interval" :value="interval">{{ interval }}</option>
          </select>
        </div>
      </div>

      <!-- 价格卡片 -->
      <div id="market" class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div class="bg-white rounded-xl shadow-sm p-4 border-l-4 border-primary card-hover">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-medium text-gray-500">当前价格</h3>
            <span class="text-xs font-medium px-2 py-1 rounded-full bg-primary/10 text-primary">{{ selectedSymbol.toUpperCase() }}</span>
          </div>
          <div class="flex items-baseline">
            <span class="text-2xl font-bold text-dark mr-2">{{ priceData ? (parseFloat(priceData.c) || 0).toFixed(2) : '-' }}</span>
            <span class="text-sm text-gray-500">{{ priceData ? `数据: ${(parseFloat(priceData.c) || 0).toFixed(4)}` : '无数据' }}</span>
            <span class="text-success text-sm flex items-center" v-if="priceData && parseFloat(priceData.c) > parseFloat(priceData.o)">
              <i class="fa fa-caret-up mr-1"></i>
              {{ ((parseFloat(priceData.c) - parseFloat(priceData.o)) / parseFloat(priceData.o) * 100).toFixed(2) }}%
            </span>
            <span class="text-danger text-sm flex items-center" v-else-if="priceData && parseFloat(priceData.c) < parseFloat(priceData.o)">
              <i class="fa fa-caret-down mr-1"></i>
              {{ ((parseFloat(priceData.o) - parseFloat(priceData.c)) / parseFloat(priceData.o) * 100).toFixed(2) }}%
            </span>
            <span class="text-gray-500 text-sm" v-else>-</span>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm p-4 border-l-4 border-secondary card-hover">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-medium text-gray-500">24小时最高</h3>
            <span class="text-xs font-medium px-2 py-1 rounded-full bg-secondary/10 text-secondary">{{ timeInterval }}</span>
          </div>
          <div class="flex items-baseline">
            <span class="text-2xl font-bold text-dark">{{ priceData ? (parseFloat(priceData.h) || 0).toFixed(2) : '-' }}</span>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm p-4 border-l-4 border-warning card-hover">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-medium text-gray-500">24小时最低</h3>
            <span class="text-xs font-medium px-2 py-1 rounded-full bg-warning/10 text-warning">{{ timeInterval }}</span>
          </div>
          <div class="flex items-baseline">
            <span class="text-2xl font-bold text-dark">{{ priceData ? (parseFloat(priceData.l) || 0).toFixed(2) : '-' }}</span>
          </div>
        </div>
      </div>

      <!-- 图表区域 -->
      <div id="chart" class="bg-white rounded-xl shadow-sm p-4 mb-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-dark">{{ selectedSymbol.toUpperCase() }} 价格图表</h2>
        </div>
        
        <div class="h-[400px] flex items-center justify-center">
          <div>{{ klineData.length  > 0}} </div>
          <canvas id="priceChart" v-show="klineData.length > 0"></canvas>
          <div v-if="klineData.length === 0" class="text-center text-gray-500">
            <i class="fa fa-line-chart text-4xl mb-2 opacity-20"></i>
            <p>等待K线数据加载...</p>
          </div>
        </div>
      </div>

      <!-- 分析和指标 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <!-- 技术指标 -->
        <div id="indicators" class="bg-white rounded-xl shadow-sm p-4 lg:col-span-2">
          <h2 class="text-lg font-semibold text-dark mb-4">技术指标</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- RSI -->
            <div class="p-3 border border-gray-100 rounded-lg">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium text-gray-700">RSI (14)</span>
                <span class="text-sm font-bold" :class="indicators.rsi && indicators.rsi['14'] > 70 ? 'text-danger' : indicators.rsi && indicators.rsi['14'] < 30 ? 'text-success' : 'text-dark'">
                  {{ indicators.rsi && indicators.rsi['14'] !== null ? indicators.rsi['14'].toFixed(2) : '0.00' }}
                </span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2.5">
                <div class="h-2.5 rounded-full" :class="indicators.rsi && indicators.rsi['14'] > 70 ? 'bg-danger' : indicators.rsi && indicators.rsi['14'] < 30 ? 'bg-success' : 'bg-primary'" :style="{ width: indicators.rsi && indicators.rsi['14'] ? Math.min(indicators.rsi['14'], 100) + '%' : '0%' }"></div>
              </div>
              <div class="flex justify-between mt-1 text-xs text-gray-500">
                <span>0</span>
                <span>30</span>
                <span>50</span>
                <span>70</span>
                <span>100</span>
              </div>
            </div>

            <!-- MACD -->
            <div class="p-3 border border-gray-100 rounded-lg">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium text-gray-700">MACD Histogram</span>
                <span class="text-sm font-bold" :class="indicators.macd && indicators.macd.histogram > 0 ? 'text-success' : 'text-danger'">
                  {{ indicators.macd && indicators.macd.histogram !== null ? indicators.macd.histogram.toFixed(4) : '0.0000' }}
                </span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2.5">
                <div class="h-2.5 rounded-full" :class="indicators.macd && indicators.macd.histogram > 0 ? 'bg-success' : 'bg-danger'" :style="{ width: indicators.macd ? Math.min(Math.abs(indicators.macd.histogram * 10), 100) + '%' : '0%' }"></div>
              </div>
            </div>

            <!-- 布林带 -->
            <div class="p-3 border border-gray-100 rounded-lg">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium text-gray-700">布林带</span>
                <span class="text-sm font-bold text-dark">{{ indicators.bollingerBands ? indicators.bollingerBands.upper.toFixed(2) + ' / ' + indicators.bollingerBands.lower.toFixed(2) : '-' }}</span>
              </div>
              <div class="flex justify-between text-xs text-gray-500 mt-1">
                  <span>上轨: {{ indicators.bollingerBands && indicators.bollingerBands.upper !== null ? indicators.bollingerBands.upper.toFixed(2) : '0.00' }}</span>
                  <span>中轨: {{ indicators.bollingerBands && indicators.bollingerBands.middle !== null ? indicators.bollingerBands.middle.toFixed(2) : '0.00' }}</span>
                  <span>下轨: {{ indicators.bollingerBands && indicators.bollingerBands.lower !== null ? indicators.bollingerBands.lower.toFixed(2) : '0.00' }}</span>
                </div>
            </div>

            <!-- 移动平均线 -->
            <div class="p-3 border border-gray-100 rounded-lg">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium text-gray-700">移动平均线</span>
              </div>
              <div class="flex justify-between text-xs text-gray-500 mt-1">
                <span>MA5: {{ indicators.sma && indicators.sma['5'] !== null ? indicators.sma['5'].toFixed(2) : '0.00' }}</span>
                <span>MA10: {{ indicators.sma && indicators.sma['10'] !== null ? indicators.sma['10'].toFixed(2) : '0.00' }}</span>
                <span>MA20: {{ indicators.sma && indicators.sma['20'] !== null ? indicators.sma['20'].toFixed(2) : '0.00' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 交易建议 -->
        <div id="analysis" class="bg-white rounded-xl shadow-sm p-4">
          <h2 class="text-lg font-semibold text-dark mb-4">交易建议</h2>

          <!-- 建议内容 -->
          <div class="p-4 rounded-lg mb-4" :class="tradingAdvice.includes('卖出') ? 'bg-danger/10 border border-danger/20' : tradingAdvice.includes('买入') ? 'bg-success/10 border border-success/20' : 'bg-primary/10 border border-primary/20'">
            <p class="text-center font-medium" :class="tradingAdvice.includes('卖出') ? 'text-danger' : tradingAdvice.includes('买入') ? 'text-success' : 'text-primary'">
              {{ tradingAdvice || '等待分析数据...' }}
            </p>
          </div>

          <!-- 价格预测 -->
          <div class="mb-4">
            <h3 class="text-sm font-medium text-gray-700 mb-2">价格预测</h3>
            <div class="flex items-center justify-between p-3 border border-gray-100 rounded-lg">
              <span class="text-sm text-gray-600">预测价格</span>
              <span class="text-sm font-bold text-dark">{{ predictions ? predictions.predictedPrice : '-' }}</span>
            </div>
            <div class="flex items-center justify-between p-3 border border-gray-100 rounded-lg mt-2">
              <span class="text-sm text-gray-600">趋势</span>
              <span class="text-sm font-bold" :class="predictions && predictions.trend === '上涨' ? 'text-success' : 'text-danger'">{{ predictions ? predictions.trend : '-' }}</span>
            </div>
            <div class="flex items-center justify-between p-3 border border-gray-100 rounded-lg mt-2">
              <span class="text-sm text-gray-600">可信度</span>
              <span class="text-sm font-bold text-dark">{{ predictions ? predictions.confidence + '%' : '-' }}</span>
            </div>
          </div>

          <!-- 支撑位和压力位 -->
          <div>
            <h3 class="text-sm font-medium text-gray-700 mb-2">支撑位/压力位</h3>
            <div class="flex items-center justify-between p-3 border border-gray-100 rounded-lg">
              <span class="text-sm text-gray-600">支撑位</span>
              <span class="text-sm font-bold text-success">{{ supportResistance.support || '-' }}</span>
            </div>
            <div class="flex items-center justify-between p-3 border border-gray-100 rounded-lg mt-2">
              <span class="text-sm text-gray-600">压力位</span>
              <span class="text-sm font-bold text-danger">{{ supportResistance.resistance || '-' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 异常波动提醒 -->
      <div class="bg-white rounded-xl shadow-sm p-4 mb-6">
        <h2 class="text-lg font-semibold text-dark mb-4">异常波动提醒</h2>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">交易对</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">方向</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">变动幅度</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">时间</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="alert in volatilityAlerts" :key="alert.id">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-dark">{{ alert.symbol }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm" :class="alert.direction === '上涨' ? 'text-success' : 'text-danger'">{{ alert.direction }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-dark">{{ alert.changePercent }}%</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ alert.time }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="text-center text-sm text-gray-500 mt-4" v-if="volatilityAlerts.length === 0">暂无异常波动提醒</p>
      </div>
    </main>

    <!-- 页脚 -->
    <footer class="bg-dark text-white py-6">
      <div class="container mx-auto px-4">
        <div class="flex flex-col md:flex-row justify-between items-center">
          <div class="flex items-center space-x-2 mb-4 md:mb-0">
            <i class="fa fa-line-chart text-primary text-2xl"></i>
            <h2 class="text-xl font-bold">QTradeAnalysis</h2>
          </div>
          <div class="flex space-x-6 mb-4 md:mb-0">
            <a href="#" class="text-gray-300 hover:text-primary transition-colors duration-200">关于我们</a>
            <a href="#" class="text-gray-300 hover:text-primary transition-colors duration-200">服务条款</a>
            <a href="#" class="text-gray-300 hover:text-primary transition-colors duration-200">隐私政策</a>
            <a href="#" class="text-gray-300 hover:text-primary transition-colors duration-200">帮助中心</a>
          </div>
          <div class="flex space-x-4">
            <a href="#" class="text-gray-300 hover:text-primary transition-colors duration-200"><i class="fa fa-twitter"></i></a>
            <a href="#" class="text-gray-300 hover:text-primary transition-colors duration-200"><i class="fa fa-telegram"></i></a>
            <a href="#" class="text-gray-300 hover:text-primary transition-colors duration-200"><i class="fa fa-discord"></i></a>
          </div>
        </div>
        <div class="mt-6 text-center text-gray-400 text-sm">
          &copy; {{ new Date().getFullYear() }} QTradeAnalysis. 保留所有权利。
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* 样式保持不变，已通过npm引入chartjs-chart-financial */
</style>