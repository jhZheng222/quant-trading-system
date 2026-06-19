<template>
  <div class="simple-trade-test">
    <h3>交易对切换测试</h3>
    <div class="trade-pairs">
      <button v-for="pair in tradePairs" :key="pair" @click="switchPair(pair)">
        {{ pair }}
      </button>
    </div>
    <div class="kline-data">
      <h4>最新K线数据 ({{ currentPair }})</h4>
      <pre>{{ klineData }}</pre>
    </div>
    <div class="logs">
      <h4>日志</h4>
      <pre>{{ logMessages }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import binanceService from '../services/binanceWebSocket'

// 可用交易对
const tradePairs = ['btcusdt', 'ethusdt', 'solusdt', 'dogeusdt', 'adausdt']
// 当前选中的交易对
const currentPair = ref('btcusdt')
// K线数据
const klineData = ref({})
// 日志消息
const logMessages = ref('')
// 移除监听器的函数
let removeKlineListener = null

// 添加日志
const addLog = (message) => {
  logMessages.value += `[${new Date().toLocaleTimeString()}] ${message}\n`
  // 自动滚动到底部
  setTimeout(() => {
    const logElement = document.querySelector('.logs pre')
    if (logElement) {
      logElement.scrollTop = logElement.scrollHeight
    }
  }, 100)
}

// 切换交易对
const switchPair = (pair) => {
  addLog(`切换到交易对: ${pair}`)
  currentPair.value = pair
  subscribeToKlineData()
}

// 处理K线数据
const handleKlineData = (kline) => {
  addLog(`收到${currentPair.value}的K线数据`)
  klineData.value = kline
}

// 订阅K线数据
const subscribeToKlineData = () => {
  // 取消之前的订阅
  if (removeKlineListener) {
    addLog('取消之前的监听器')
    removeKlineListener()
    removeKlineListener = null
  }

  // 订阅新的交易对
  addLog(`订阅${currentPair.value}的1小时K线数据`)
  binanceService.subscribeToSymbol(currentPair.value, '1h')

  // 添加新的监听器
  removeKlineListener = binanceService.addListener(
    currentPair.value,
    handleKlineData,
    '1h'
  )
}

// 组件挂载时
onMounted(() => {
  addLog('组件已挂载，开始连接WebSocket')
  binanceService.connect()
  setTimeout(() => {
    subscribeToKlineData()
  }, 2000)
})

// 组件卸载时
onUnmounted(() => {
  addLog('组件已卸载，清理订阅')
  if (removeKlineListener) {
    removeKlineListener()
    removeKlineListener = null
  }
})
</script>

<style scoped>
.simple-trade-test {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

trade-pairs {
  margin-bottom: 20px;
}

trade-pairs button {
  margin-right: 10px;
  padding: 8px 16px;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

trade-pairs button:hover {
  background-color: #2563eb;
}

.kline-data, .logs {
  margin-top: 20px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  padding: 10px;
  max-height: 300px;
  overflow-y: auto;
}

.logs pre {
  color: #374151;
  font-family: monospace;
  white-space: pre-wrap;
}
</style>