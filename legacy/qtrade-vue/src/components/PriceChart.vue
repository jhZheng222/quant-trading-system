<script setup>
// 引入必要的组件和库
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { ElButton, ElIcon } from 'element-plus'
import { Chart, CategoryScale, LinearScale, PointElement, LineElement, LineController, BarElement, BarController, Title, Tooltip, Legend, Filler } from 'chart.js'
import { Histogram, TrendCharts, Clock, Calendar } from '@element-plus/icons-vue'
// 导入Binance WebSocket服务
import binanceWebSocketService from '../services/binanceWebSocket'

// 注册所需的组件
Chart.register(CategoryScale, LinearScale, PointElement, LineElement, LineController, BarElement, BarController, Title, Tooltip, Legend, Filler)

// 交易对数据
const marketData = ref([
  { symbol: 'btcusdt', name: '比特币' },
  { symbol: 'ethusdt', name: '以太坊' },
  { symbol: 'solusdt', name: '索拉纳' },
  { symbol: 'dogeusdt', name: '狗狗币' },
  { symbol: 'adausdt', name: '卡尔达诺' },
])

// 当前选中的交易对
const selectedPair = ref('btcusdt')

// 切换交易对
const switchPair = (pair) => {
  selectedPair.value = pair
  // 重新订阅K线数据
  subscribeToKlineData()
}

// 当前选中的指标
const selectedIndicator = ref('price')

// 当前选中的时间周期
const selectedTimeframe = ref('1h')

// 可用的时间周期选项
const timeframes = [
  { value: '1m', label: '1分钟' },
  { value: '5m', label: '5分钟' },
  { value: '15m', label: '15分钟' },
  { value: '30m', label: '30分钟' },
  { value: '1h', label: '1小时' },
  { value: '2h', label: '2小时' },
  { value: '4h', label: '4小时' },
  { value: '6h', label: '6小时' },
  { value: '8h', label: '8小时' },
  { value: '12h', label: '12小时' },
  { value: '1d', label: '1天' },
  { value: '3d', label: '3天' },
  { value: '1w', label: '1周' },
  { value: '1M', label: '1月' }
]

// 图表数据
const chartData = ref([])
// 历史K线数据缓存
const klineHistory = new Map()
// 存储移除监听器的函数
let removeKlineListener = null
let removeTradeListener = null

// 格式化K线数据
const formatKlineData = (kline) => {
  const { t, o, h, l, c, v } = kline
  const date = new Date(t)
  let label = ''

  // 根据时间周期格式化标签
  if (selectedTimeframe.value === '1m' || selectedTimeframe.value === '5m' || selectedTimeframe.value === '15m' || selectedTimeframe.value === '30m') {
    label = date.getHours() + ':' + (date.getMinutes() < 10 ? '0' : '') + date.getMinutes()
  } else if (selectedTimeframe.value === '1h' || selectedTimeframe.value === '2h' || selectedTimeframe.value === '4h' || selectedTimeframe.value === '6h' || selectedTimeframe.value === '8h' || selectedTimeframe.value === '12h') {
    label = date.getHours() + ':00'
  } else if (selectedTimeframe.value === '1d' || selectedTimeframe.value === '3d') {
    label = date.getMonth() + 1 + '/' + date.getDate()
  } else if (selectedTimeframe.value === '1w') {
    label = '周' + (date.getDay() || 7)
  } else if (selectedTimeframe.value === '1M') {
    label = (date.getMonth() + 1) + '月'
  }

  return {
    date: label,
    price: parseFloat(c),
    open: parseFloat(o),
    high: parseFloat(h),
    low: parseFloat(l),
    volume: parseFloat(v),
    rsi: 0, // 后续可以添加RSI计算
    macd: 0 // 后续可以添加MACD计算
  }
}

// 处理新的K线数据
  const handleKlineData = (kline) => {
    console.log('接收到K线数据:', kline)
    if (!kline || !kline.t || !kline.c) {
      console.error('无效的K线数据:', kline)
      return
    }

    const formattedData = formatKlineData(kline)
    console.log('格式化后的数据:', formattedData)

    const symbol = selectedPair.value
    const interval = selectedTimeframe.value
    const cacheKey = `${symbol}_${interval}`

    // 初始化缓存
    if (!klineHistory.has(cacheKey)) {
      klineHistory.set(cacheKey, [])
    }

    const history = klineHistory.get(cacheKey)
    // 检查是否已存在该时间点的数据
    const existingIndex = history.findIndex(item => item.date === formattedData.date)

    if (existingIndex >= 0) {
      // 更新现有数据
      history[existingIndex] = formattedData
    } else {
      // 添加新数据
      history.push(formattedData)
      // 保持数据按时间排序
      history.sort((a, b) => new Date(a.date) - new Date(b.date))
      // 增加数据点数量，延长时间窗口
      if (history.length > 300) {
        history.shift()
      }
    }

    // 更新图表数据
    chartData.value = [...history]
    // 触发图表更新
    updateChart()
    console.log('图表数据已更新')
}

// 订阅K线数据
  const subscribeToKlineData = () => {
    console.log(`开始订阅${selectedPair.value}的${selectedTimeframe.value}K线数据`)

    // 确保WebSocket已连接
    if (!binanceWebSocketService.isConnected) {
      console.error('WebSocket未连接，等待连接建立...')
      // 如果未连接，先连接
      binanceWebSocketService.connect()
      // 设置定时器检查连接状态
      const checkConnInterval = setInterval(() => {
        if (binanceWebSocketService.isConnected) {
          clearInterval(checkConnInterval)
          console.log('WebSocket连接已建立，重新尝试订阅数据')
          subscribeToKlineData()
        }
      }, 500)
      return
    }

  // 取消之前的价格图表监听器
  if (removeKlineListener) {
    console.log('取消之前的监听器')
    removeKlineListener()
    removeKlineListener = null
  }

  // 取消当前时间周期的所有交易对订阅
  const currentInterval = selectedTimeframe.value
  Array.from(binanceWebSocketService.subscribedSymbols).forEach(symbol => {
    if (symbol.includes('_')) {
      const [sym, interval] = symbol.split('_')
      if (interval === currentInterval) {
        binanceWebSocketService.unsubscribeFromSymbol(sym, interval)
        console.log(`已取消订阅: ${sym}_${interval}`)
      }
    }
  })

  // 延迟一小段时间，确保取消订阅指令已发送
  setTimeout(() => {
    // 订阅新的价格图表数据
    binanceWebSocketService.subscribeToSymbol(selectedPair.value, selectedTimeframe.value)
    console.log(`已订阅新交易对: ${selectedPair.value}_${selectedTimeframe.value}`)

    // 添加新的监听器
    removeKlineListener = binanceWebSocketService.addListener(
      selectedPair.value,
      handleKlineData,
      selectedTimeframe.value
    )
    console.log(`已添加${selectedPair.value}的${selectedTimeframe.value}监听器`)

    // 初始化图表数据
    const cacheKey = `${selectedPair.value}_${selectedTimeframe.value}`
    if (klineHistory.has(cacheKey)) {
      chartData.value = [...klineHistory.get(cacheKey)]
    } else {
      chartData.value = []
    }

    // 强制更新图表
    updateChart()

    console.log(`订阅完成，当前订阅的交易对: ${selectedPair.value}`)
  }, 300)
}

// 切换指标
const switchIndicator = (indicator) => {
  selectedIndicator.value = indicator
  updateChart()
}

// 切换时间周期
const switchTimeframe = (timeframe) => {
  selectedTimeframe.value = timeframe
  // 重新订阅K线数据
  subscribeToKlineData()
}

// 图表实例
let chart = null

// 更新图表
const updateChart = () => {
  if (!chart) return

  // 准备数据
  const labels = chartData.value.map(item => item.date)
  let data = []
  let borderColor = ''
  let backgroundColor = ''
  let yAxisLabel = ''

  if (selectedIndicator.value === 'price') {
    data = chartData.value.map(item => item.price)
    borderColor = '#3b82f6'
    backgroundColor = 'rgba(59, 130, 246, 0.1)'
    yAxisLabel = '价格 (USD)'
  } else if (selectedIndicator.value === 'rsi') {
    data = chartData.value.map(item => item.rsi)
    borderColor = '#10b981'
    backgroundColor = 'rgba(16, 185, 129, 0.1)'
    yAxisLabel = 'RSI'
  } else if (selectedIndicator.value === 'macd') {
    data = chartData.value.map(item => item.macd)
    borderColor = '#ef4444'
    backgroundColor = 'rgba(239, 68, 68, 0.1)'
    yAxisLabel = 'MACD'
  } else if (selectedIndicator.value === 'volume') {
    data = chartData.value.map(item => item.volume)
    borderColor = '#f59e0b'
    backgroundColor = 'rgba(245, 158, 11, 0.1)'
    yAxisLabel = '成交量'
  }

  // 更新图表
  chart.data.labels = labels
  chart.data.datasets[0].data = data
  chart.data.datasets[0].borderColor = borderColor
  chart.data.datasets[0].backgroundColor = backgroundColor
  chart.options.scales.y.title.text = yAxisLabel

  // 对于RSI，设置Y轴范围
  if (selectedIndicator.value === 'rsi') {
    chart.options.scales.y.min = 0
    chart.options.scales.y.max = 100
  } else {
    chart.options.scales.y.min = 'auto'
    chart.options.scales.y.max = 'auto'
  }

  chart.update()
}

// 交易数据存储
  const tradeData = ref([])
  // 支撑位和压力位数据
  const supportResistance = ref({
    support: [],
    resistance: []
  })
  // 交易建议数据
  const tradingSuggestions = ref([])
  // 波动提醒数据
  const volatilityAlerts = ref([])
  // 市场深度数据
  const depthData = ref({
    bids: [],
    asks: []
  })
  // 价格变动数据
  const tickerData = ref(null)
  // 市场深度最大值(用于计算深度条宽度)
  const maxDepth = computed(() => {
    if (!depthData.value || (depthData.value.bids.length === 0 && depthData.value.asks.length === 0)) {
      return 1
    }
    const bidMax = depthData.value.bids.length > 0 ? Math.max(...depthData.value.bids.map(bid => bid.quantity)) : 0
    const askMax = depthData.value.asks.length > 0 ? Math.max(...depthData.value.asks.map(ask => ask.quantity)) : 0
    return Math.max(bidMax, askMax) || 1
  })
  // 存储移除监听器的函数
  let removeDepthListener = null
  let removeTickerListener = null

  // 订阅交易数据
  const subscribeToTradeData = () => {
    console.log(`开始订阅${selectedPair.value}的交易数据`)

    // 确保WebSocket已连接
    if (!binanceWebSocketService.isConnected) {
      console.error('WebSocket未连接，等待连接建立...')
      // 如果未连接，先连接
      binanceWebSocketService.connect()
      // 设置定时器检查连接状态
      const checkConnInterval = setInterval(() => {
        if (binanceWebSocketService.isConnected) {
          clearInterval(checkConnInterval)
          console.log('WebSocket连接已建立，重新尝试订阅交易数据')
          subscribeToTradeData()
        }
      }, 500)
      return
    }

    // 取消之前的交易数据监听器
    if (removeTradeListener) {
      console.log('取消之前的交易监听器')
      removeTradeListener()
      removeTradeListener = null
    }

    // 订阅aggTrade频道
    binanceWebSocketService.subscribeToSymbol(selectedPair.value, '', 'aggTrade')
    console.log(`已订阅aggTrade: ${selectedPair.value}`)

    // 订阅trade频道
    binanceWebSocketService.subscribeToSymbol(selectedPair.value, '', 'trade')
    console.log(`已订阅trade: ${selectedPair.value}`)

    // 添加交易数据监听器
    removeTradeListener = binanceWebSocketService.addListener(
      selectedPair.value,
      handleTradeData,
      '',
      'trade'
    )
    console.log(`已添加${selectedPair.value}的交易数据监听器`)
  }

  // 处理交易数据
  const handleTradeData = (data) => {
    console.log('收到交易数据:', data)
    if (!data || !data.t || !data.p || !data.q) {
      console.error('无效的交易数据:', data)
      return
    }

    const formattedData = {
      time: new Date(data.t).toLocaleTimeString(),
      price: parseFloat(data.p),
      quantity: parseFloat(data.q),
      side: data.m ? '卖出' : '买入'
    }

    // 更新交易数据列表
    tradeData.value.unshift(formattedData)
    // 只保留最近的20条交易数据
    if (tradeData.value.length > 20) {
      tradeData.value.pop()
    }

    // 计算支撑位和压力位 (简单示例，实际应用中可能需要更复杂的算法)
    calculateSupportResistance()

    // 生成交易建议 (简单示例)
    generateTradingSuggestions()

    // 检查波动 (简单示例)
    checkVolatility()
  }

  // 计算支撑位和压力位
  const calculateSupportResistance = () => {
    // 这里使用简单的滚动窗口计算，实际应用中可能需要更复杂的算法
    const windowSize = 20
    if (chartData.value.length < windowSize) return

    const recentPrices = chartData.value.slice(-windowSize).map(item => item.price)
    const minPrice = Math.min(...recentPrices)
    const maxPrice = Math.max(...recentPrices)

    // 更新支撑位和压力位
    supportResistance.value = {
      support: [minPrice],
      resistance: [maxPrice]
    }
  }

  // 生成交易建议
  const generateTradingSuggestions = () => {
    // 简单示例：基于最新价格和移动平均线
    if (chartData.value.length < 10) return

    const latestPrice = chartData.value[chartData.value.length - 1].price
    const ma5 = chartData.value.slice(-5).reduce((sum, item) => sum + item.price, 0) / 5
    const ma20 = chartData.value.slice(-20).reduce((sum, item) => sum + item.price, 0) / 20

    let suggestion = '持有'
    let reason = ''

    if (latestPrice > ma5 && ma5 > ma20) {
      suggestion = '买入'
      reason = '价格高于5日和20日均线，呈上升趋势'
    } else if (latestPrice < ma5 && ma5 < ma20) {
      suggestion = '卖出'
      reason = '价格低于5日和20日均线，呈下降趋势'
    }

    tradingSuggestions.value = [{
      time: new Date().toLocaleTimeString(),
      suggestion,
      reason
    }]
  }

  // 检查波动
  const checkVolatility = () => {
    // 简单示例：基于最近价格变化率
    if (chartData.value.length < 2) return

    const previousPrice = chartData.value[chartData.value.length - 2].price
    const currentPrice = chartData.value[chartData.value.length - 1].price
    const changePercent = Math.abs((currentPrice - previousPrice) / previousPrice * 100)

    if (changePercent > 1) {
      volatilityAlerts.value.push({
        time: new Date().toLocaleTimeString(),
        symbol: selectedPair.value,
        changePercent: changePercent.toFixed(2),
        message: `价格在短时间内波动超过${changePercent.toFixed(2)}%`
      })

      // 只保留最近的5条提醒
      if (volatilityAlerts.value.length > 5) {
        volatilityAlerts.value.shift()
      }
    }
  }

  // 组件挂载时执行
onMounted(() => {
  console.log('PriceChart组件已挂载')
  // 连接到Binance WebSocket
  console.log('尝试连接到Binance WebSocket...')
  binanceWebSocketService.connect()

  // 等待WebSocket连接建立后订阅所有数据
  const checkConnectionInterval = setInterval(() => {
    if (binanceWebSocketService.isConnected) {
      clearInterval(checkConnectionInterval)
      console.log('WebSocket连接已建立，开始订阅数据...')
      subscribeToKlineData()
      subscribeToTradeData()
      subscribeToDepthData()
      subscribeToTickerData()
    }
  }, 500)



  // 删除旧的5秒超时检查，因为我们已经有了持续的连接检查机制

  // 创建图表
  const ctx = document.getElementById('priceChart')
  if (ctx) {
    chart = new Chart(ctx, {
      type: selectedIndicator.value === 'volume' ? 'bar' : 'line',
      data: {
        labels: chartData.value.map(item => item.date),
        datasets: [{
          label: selectedPair.value.toUpperCase(),
          data: chartData.value.map(item => item.price),
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: selectedIndicator.value !== 'volume',
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 5
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
              label: function(context) {
                let label = context.dataset.label || ''
                if (label) {
                  label += ': '
                }
                if (context.parsed.y !== null) {
                  if (selectedIndicator.value === 'price') {
                    label += new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(context.parsed.y)
                  } else if (selectedIndicator.value === 'volume') {
                    label += new Intl.NumberFormat('en-US', { style: 'decimal', maximumFractionDigits: 0 }).format(context.parsed.y) + ' 体积'
                  } else {
                    label += context.parsed.y.toFixed(2)
                  }
                }
                return label
              }
            }
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            }
          },
          y: {
            position: 'right',
            title: {
              display: true,
              text: '价格 (USD)'
            }
          }
        }
      }
    })
  }

  // 监听图表数据变化，更新图表
  chartData.value = [...chartData.value]
  watch(chartData, () => {
    updateChart()
  })

  // 挂载后3秒自动执行测试
  setTimeout(testDataLoad, 3000)
})

// 测试WebSocket连接
const testWebSocketConnection = () => {
  console.log('手动测试WebSocket连接...')
  if (binanceWebSocketService.isConnected) {
    console.log('WebSocket已经连接')
  } else {
    console.log('WebSocket未连接，尝试连接...')
    binanceWebSocketService.connect()
    // 3秒后检查连接状态
    setTimeout(() => {
      console.log(`WebSocket连接状态: ${binanceWebSocketService.isConnected}`)
    }, 3000)
  }
}

// 测试数据订阅
const testDataSubscription = () => {
  console.log('手动测试数据订阅...')
  if (!binanceWebSocketService.isConnected) {
    console.error('WebSocket未连接，无法订阅数据')
    return
  }
  console.log(`订阅${selectedPair.value}的${selectedTimeframe.value}K线数据`)
  subscribeToKlineData()
}

// 清除图表数据
const clearChartData = () => {
  console.log('清除图表数据...')
  const cacheKey = `${selectedPair.value}_${selectedTimeframe.value}`
  if (klineHistory.has(cacheKey)) {
    klineHistory.set(cacheKey, [])
  }
  chartData.value = []
  updateChart()
  console.log('图表数据已清除')
}

// 组件卸载时执行
onUnmounted(() => {
  // 移除K线监听器
  if (removeKlineListener) {
    removeKlineListener()
    removeKlineListener = null
  }

  // 移除交易数据监听器
  if (removeTradeListener) {
    removeTradeListener()
    removeTradeListener = null
  }

  // 移除市场深度监听器
  if (removeDepthListener) {
    removeDepthListener()
    removeDepthListener = null
  }

  // 移除价格变动监听器
  if (removeTickerListener) {
    removeTickerListener()
    removeTickerListener = null
  }

  // 断开WebSocket连接
  binanceWebSocketService.disconnect()

  // 销毁图表
  if (chart) {
    chart.destroy()
    chart = null
  }
})

// 订阅市场深度数据
  const subscribeToDepthData = () => {
    console.log(`开始订阅${selectedPair.value}的市场深度数据`)

    // 确保WebSocket已连接
    if (!binanceWebSocketService.isConnected) {
      console.error('WebSocket未连接，等待连接建立...')
      // 如果未连接，先连接
      binanceWebSocketService.connect()
      // 设置定时器检查连接状态
      const checkConnInterval = setInterval(() => {
        if (binanceWebSocketService.isConnected) {
          clearInterval(checkConnInterval)
          console.log('WebSocket连接已建立，重新尝试订阅市场深度数据')
          subscribeToDepthData()
        }
      }, 500)
      return
    }

    // 取消之前的市场深度监听器
    if (removeDepthListener) {
      console.log('取消之前的市场深度监听器')
      removeDepthListener()
      removeDepthListener = null
    }

    // 订阅depth频道
    binanceWebSocketService.subscribeToSymbol(selectedPair.value, '', 'depth')
    console.log(`已订阅depth: ${selectedPair.value}`)

    // 添加市场深度监听器
    removeDepthListener = binanceWebSocketService.addListener(
      selectedPair.value,
      handleDepthData,
      'depth',
      'depth'
    )
    console.log(`已添加${selectedPair.value}的市场深度监听器`)
  }

  // 处理市场深度数据
  const handleDepthData = (data) => {
    console.log('收到市场深度数据:', data)
    if (!data || !data.s || !data.b || !data.a) {
      console.error('无效的市场深度数据:', data)
      return
    }

    // 格式化买单和卖单数据
    const bids = data.b.map(bid => ({
      price: parseFloat(bid[0]),
      quantity: parseFloat(bid[1])
    }))

    const asks = data.a.map(ask => ({
      price: parseFloat(ask[0]),
      quantity: parseFloat(ask[1])
    }))

    // 更新市场深度数据
    depthData.value = {
      bids: bids.slice(0, 10), // 只保留前10条买单
      asks: asks.slice(0, 10)  // 只保留前10条卖单
    }
  }

  // 订阅价格变动数据
  const subscribeToTickerData = () => {
    console.log(`开始订阅${selectedPair.value}的价格变动数据`)

    // 确保WebSocket已连接
    if (!binanceWebSocketService.isConnected) {
      console.error('WebSocket未连接，等待连接建立...')
      // 如果未连接，先连接
      binanceWebSocketService.connect()
      // 设置定时器检查连接状态
      const checkConnInterval = setInterval(() => {
        if (binanceWebSocketService.isConnected) {
          clearInterval(checkConnInterval)
          console.log('WebSocket连接已建立，重新尝试订阅价格变动数据')
          subscribeToTickerData()
        }
      }, 500)
      return
    }

    // 取消之前的价格变动监听器
    if (removeTickerListener) {
      console.log('取消之前的价格变动监听器')
      removeTickerListener()
      removeTickerListener = null
    }

    // 订阅ticker频道
    binanceWebSocketService.subscribeToSymbol(selectedPair.value, '', '24hrTicker')
    console.log(`已订阅24hrTicker: ${selectedPair.value}`)

    // 添加价格变动监听器
    removeTickerListener = binanceWebSocketService.addListener(
      selectedPair.value,
      handleTickerData,
      'ticker',
      '24hrTicker'
    )
    console.log(`已添加${selectedPair.value}的价格变动监听器`)
  }

  // 处理价格变动数据
  const handleTickerData = (data) => {
    console.log('收到价格变动数据:', data)
    if (!data || !data.s || !data.c) {
      console.error('无效的价格变动数据:', data)
      return
    }

    // 格式化价格变动数据
    const formattedData = {
      symbol: data.s,
      lastPrice: parseFloat(data.c),
      openPrice: parseFloat(data.o),
      highPrice: parseFloat(data.h),
      lowPrice: parseFloat(data.l),
      volume: parseFloat(data.v),
      priceChange: parseFloat(data.p),
      priceChangePercent: parseFloat(data.P)
    }

    // 更新价格变动数据
    tickerData.value = formattedData
  }

// 挂载后3秒自动执行测试
setTimeout(testDataLoad, 3000)
</script>

<template>
  <section class="price-chart">
    <div class="chart-header">
      <h2 class="chart-title">{{ selectedPair }} 价格图表</h2>
      <!-- 价格变动信息 -->
      <div v-if="tickerData" class="ticker-info">
        <div class="ticker-item"><span class="label">最新价格:</span> <span class="value">{{ tickerData.lastPrice | currency }}</span></div>
        <div class="ticker-item"><span class="label">24h最高:</span> <span class="value">{{ tickerData.highPrice | currency }}</span></div>
        <div class="ticker-item"><span class="label">24h最低:</span> <span class="value">{{ tickerData.lowPrice | currency }}</span></div>
        <div class="ticker-item" :class="tickerData.priceChange >= 0 ? 'positive' : 'negative'"><span class="label">24h变化:</span> <span class="value">{{ tickerData.priceChange | currency }} ({{ tickerData.priceChangePercent }}%)</span></div>
      </div>
      <div class="trading-pairs">
        <div class="pairs-buttons">
          <ElButton
            v-for="item in marketData"
            :key="item.symbol"
            :type="selectedPair === item.symbol ? 'primary' : 'default'"
            @click="switchPair(item.symbol)"
          >
            {{ item.symbol }}
          </ElButton>
        </div>
      </div>
      <div class="chart-controls">
      <div class="indicator-buttons">
        <ElButton
          :type="selectedIndicator === 'price' ? 'primary' : 'default'"
          @click="switchIndicator('price')"
        >
          价格
        </ElButton>
        <ElButton
          :type="selectedIndicator === 'rsi' ? 'primary' : 'default'"
          @click="switchIndicator('rsi')"
          icon="TrendCharts"
        >
          <ElIcon><TrendCharts /></ElIcon>
          RSI
        </ElButton>
        <ElButton
          :type="selectedIndicator === 'macd' ? 'primary' : 'default'"
          @click="switchIndicator('macd')"
          icon="Histogram"
        >
          <ElIcon><Histogram /></ElIcon>
          MACD
        </ElButton>
        <ElButton
          :type="selectedIndicator === 'volume' ? 'primary' : 'default'"
          @click="switchIndicator('volume')"
          icon="TrendCharts"
        >
          <ElIcon><TrendCharts /></ElIcon>
          成交量
        </ElButton>
      </div>
      <div class="timeframe-selector">
        <h3>时间间隔</h3>
        <div class="timeframe-items">
          <div
            v-for="tf in timeframes"
            :key="tf.value"
            :class="['timeframe-item', selectedTimeframe === tf.value ? 'active' : '']"
            @click="switchTimeframe(tf.value)"
          >
            {{ tf.label }}
          </div>
        </div>
      </div>
      <div class="test-controls">
        <ElButton @click="testWebSocketConnection">测试WebSocket连接</ElButton>
        <ElButton @click="testDataSubscription">测试数据订阅</ElButton>
        <ElButton @click="clearChartData">清除图表数据</ElButton>
      </div>
    </div>
    </div>
    <div class="chart-container">
      <canvas id="priceChart"></canvas>
    </div>

    <!-- 市场深度图表 -->
    <div class="depth-chart-container">
      <h3>市场深度</h3>
      <div class="depth-table">
        <div class="asks-header"><h4>卖单</h4></div>
        <div class="asks-body">
          <div v-for="ask in depthData.asks" :key="ask.price" class="depth-row">
            <div class="price">{{ ask.price | currency }}</div>
            <div class="quantity">{{ ask.quantity }}</div>
            <div class="depth-bar" :style="{ width: `${ask.quantity / maxDepth * 100}%` }"></div>
          </div>
        </div>
        <div class="bids-header"><h4>买单</h4></div>
        <div class="bids-body">
          <div v-for="bid in depthData.bids" :key="bid.price" class="depth-row">
            <div class="price">{{ bid.price | currency }}</div>
            <div class="quantity">{{ bid.quantity }}</div>
            <div class="depth-bar" :style="{ width: `${bid.quantity / maxDepth * 100}%` }"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 支撑位和压力位区域 -->
    <div class="support-resistance">
      <h3>支撑位和压力位</h3>
      <div class="levels">
        <div class="resistance-levels">
          <h4>压力位</h4>
          <div v-for="level in supportResistance.resistance" :key="'resistance-' + level" class="level-item resistance">
            ${{ level.toFixed(2) }}
          </div>
        </div>
        <div class="support-levels">
          <h4>支撑位</h4>
          <div v-for="level in supportResistance.support" :key="'support-' + level" class="level-item support">
            ${{ level.toFixed(2) }}
          </div>
        </div>
      </div>
    </div>

    <!-- 交易建议区域 -->
    <div class="trading-suggestions">
      <h3>交易建议</h3>
      <div v-if="tradingSuggestions.length > 0" class="suggestion-item" :class="tradingSuggestions[0].suggestion.toLowerCase()">
        <div class="suggestion-time">{{ tradingSuggestions[0].time }}</div>
        <div class="suggestion-action">{{ tradingSuggestions[0].suggestion }}</div>
        <div class="suggestion-reason">{{ tradingSuggestions[0].reason }}</div>
      </div>
      <div v-else class="no-data">暂无交易建议</div>
    </div>

    <!-- 波动提醒区域 -->
    <div class="volatility-alerts">
      <h3>波动提醒</h3>
      <div v-if="volatilityAlerts.length > 0">
        <div v-for="alert in volatilityAlerts" :key="alert.time" class="alert-item">
          <div class="alert-time">{{ alert.time }}</div>
          <div class="alert-symbol">{{ alert.symbol }}</div>
          <div class="alert-message">{{ alert.message }}</div>
        </div>
      </div>
      <div v-else class="no-data">暂无波动提醒</div>
    </div>

    <!-- 最近交易区域 -->
    <div class="recent-trades">
      <h3>最近交易</h3>
      <div class="trade-table">
        <div class="table-header">
          <div class="table-column">时间</div>
          <div class="table-column">价格 (USD)</div>
          <div class="table-column">数量</div>
          <div class="table-column">方向</div>
        </div>
        <div v-if="tradeData.length > 0">
          <div v-for="trade in tradeData" :key="trade.time" class="table-row" :class="trade.side === '买入' ? 'buy' : 'sell'">
            <div class="table-column">{{ trade.time }}</div>
            <div class="table-column">{{ trade.price.toFixed(2) }}</div>
            <div class="table-column">{{ trade.quantity.toFixed(4) }}</div>
            <div class="table-column">{{ trade.side }}</div>
          </div>
        </div>
        <div v-else class="no-data">暂无交易数据</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.price-chart {
  background-color: #1e293b;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  color: #f8fafc;
}

.ticker-info {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin: 15px 0;
  padding: 10px;
  background-color: #0f172a;
  border-radius: 6px;
}

.ticker-item {
  display: flex;
  align-items: center;
}

.ticker-item .label {
  color: #94a3b8;
  margin-right: 5px;
}

.ticker-item .value {
  font-weight: bold;
}

.ticker-item.positive .value {
  color: #10b981;
}

.ticker-item.negative .value {
  color: #ef4444;
}

.depth-chart-container {
  margin-top: 30px;
  padding: 15px;
  background-color: #0f172a;
  border-radius: 6px;
}

.depth-table {
  width: 100%;
  border-collapse: collapse;
}

.asks-header, .bids-header {
  padding: 10px;
  font-weight: bold;
  text-align: left;
}

.asks-header {
  color: #ef4444;
}

.bids-header {
  color: #10b981;
}

.asks-body, .bids-body {
  width: 100%;
}

.depth-row {
  display: flex;
  align-items: center;
  padding: 5px 0;
  border-bottom: 1px solid #334155;
}

.depth-row .price {
  width: 120px;
  text-align: right;
  padding-right: 10px;
}

.depth-row .quantity {
  width: 100px;
  text-align: right;
  padding-right: 10px;
}

.depth-row .depth-bar {
  flex-grow: 1;
  height: 20px;
  border-radius: 3px;
}

.asks-body .depth-bar {
  background-color: rgba(239, 68, 68, 0.3);
}

.bids-body .depth-bar {
  background-color: rgba(16, 185, 129, 0.3);
}

.chart-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
}

.trading-pairs {
  margin-bottom: 1rem;
  width: 100%;
}

.pairs-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.chart-title {
  font-size: 1.25rem;
  font-weight: bold;
  color: #111827;
}

.chart-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.indicator-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.timeframe-selector {
  margin-top: 1rem;
}

.timeframe-selector h3 {
  margin-bottom: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
}

.timeframe-items {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.timeframe-item {
  padding: 0.5rem 1rem;
  border-radius: 0.25rem;
  background-color: #f3f4f6;
  cursor: pointer;
  transition: all 0.2s;
}

.timeframe-item:hover {
  background-color: #e5e7eb;
}

.timeframe-item.active {
  background-color: #3b82f6;
  color: white;
}

.chart-container {
  height: 400px;
  width: 100%;
  margin-bottom: 2rem;
}

.support-resistance {
  margin-bottom: 2rem;
  padding: 1rem;
  background-color: #f9fafb;
  border-radius: 0.5rem;
}

.levels {
  display: flex;
  gap: 2rem;
}

.resistance-levels, .support-levels {
  flex: 1;
}

.level-item {
  padding: 0.5rem;
  margin-bottom: 0.5rem;
  border-radius: 0.25rem;
  text-align: center;
}

.resistance {
  background-color: #fee2e2;
  color: #dc2626;
}

.support {
  background-color: #d1fae5;
  color: #059669;
}

.trading-suggestions {
  margin-bottom: 2rem;
  padding: 1rem;
  background-color: #f9fafb;
  border-radius: 0.5rem;
}

.suggestion-item {
  padding: 1rem;
  border-radius: 0.25rem;
  margin-top: 0.5rem;
}

.buy {
  background-color: #d1fae5;
  color: #059669;
}

.sell {
  background-color: #fee2e2;
  color: #dc2626;
}

.hold {
  background-color: #e0e7ff;
  color: #4338ca;
}

.suggestion-time {
  font-size: 0.875rem;
  color: #6b7280;
}

.suggestion-action {
  font-size: 1.25rem;
  font-weight: bold;
  margin-top: 0.25rem;
}

.suggestion-reason {
  margin-top: 0.25rem;
}

.volatility-alerts {
  margin-bottom: 2rem;
  padding: 1rem;
  background-color: #f9fafb;
  border-radius: 0.5rem;
}

.alert-item {
  padding: 0.75rem;
  background-color: #fef3c7;
  color: #92400e;
  border-radius: 0.25rem;
  margin-top: 0.5rem;
}

.alert-time {
  font-size: 0.875rem;
}

.alert-symbol {
  font-weight: bold;
  margin-top: 0.25rem;
}

.alert-message {
  margin-top: 0.25rem;
}

.recent-trades {
  margin-bottom: 2rem;
  padding: 1rem;
  background-color: #f9fafb;
  border-radius: 0.5rem;
}

.trade-table {
  width: 100%;
  overflow-x: auto;
}

.table-header {
  display: flex;
  background-color: #e5e7eb;
  font-weight: bold;
}

.table-column {
  flex: 1;
  padding: 0.75rem;
  text-align: left;
}

.table-row {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
}

.table-row:last-child {
  border-bottom: none;
}

.buy {
  background-color: #d1fae5;
}

.sell {
  background-color: #fee2e2;
}

.no-data {
  padding: 1rem;
  text-align: center;
  color: #6b7280;
  background-color: #f3f4f6;
  border-radius: 0.25rem;
  margin-top: 0.5rem;
}
</style>