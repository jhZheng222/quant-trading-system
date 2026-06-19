<script setup>
// 引入必要的组件
import { ref, onMounted, onUnmounted } from 'vue'
import { ElTable, ElTableColumn, ElButton, ElIcon } from 'element-plus'
import { TrendCharts, Refresh } from '@element-plus/icons-vue'
// 导入Binance WebSocket服务
import binanceWebSocketService from '../services/binanceWebSocket'

// 市场数据
const marketData = ref([
  { symbol: 'btcusdt', name: '比特币', price: 0, change: 0, volume: 0, lastUpdate: null },
  { symbol: 'ethusdt', name: '以太坊', price: 0, change: 0, volume: 0, lastUpdate: null },
  { symbol: 'solusdt', name: '索拉纳', price: 0, change: 0, volume: 0, lastUpdate: null },
  { symbol: 'dogeusdt', name: '狗狗币', price: 0, change: 0, volume: 0, lastUpdate: null },
  { symbol: 'adausdt', name: '卡尔达诺', price: 0, change: 0, volume: 0, lastUpdate: null },
])

// 存储初始价格，用于计算涨跌幅
const initialPrices = new Map()
// 存储移除监听器的函数
let removeListeners = []

// 更新市场数据
const updateMarketData = (symbol, data) => {
  const itemIndex = marketData.value.findIndex(item => item.symbol === symbol)
  if (itemIndex !== -1) {
    // 计算涨跌幅
    let change = 0
    const currentPrice = parseFloat(data.p)
    if (!initialPrices.has(symbol)) {
      initialPrices.set(symbol, currentPrice)
    } else {
      change = ((currentPrice - initialPrices.get(symbol)) / initialPrices.get(symbol)) * 100
    }

    // 更新数据
    marketData.value[itemIndex] = {
      ...marketData.value[itemIndex],
      price: currentPrice,
      change: parseFloat(change.toFixed(2)),
      volume: parseFloat(data.q),
      lastUpdate: new Date()
    }

    // 强制更新视图
    marketData.value = [...marketData.value]
  }
}

// 刷新数据
const refreshData = () => {
  // 清空初始价格，重新开始计算涨跌幅
  initialPrices.clear()
  // 重置所有市场数据
  marketData.value.forEach(item => {
    marketData.value[marketData.value.findIndex(i => i.symbol === item.symbol)] = {
      ...item,
      price: 0,
      change: 0,
      volume: 0,
      lastUpdate: null
    }
  })
  // 强制更新视图
  marketData.value = [...marketData.value]
  console.log('市场数据已刷新')
}

// 组件挂载时执行
onMounted(() => {
  // 连接到Binance WebSocket
  binanceWebSocketService.connect()

  // 为每个交易对添加监听器
  marketData.value.forEach(item => {
    const removeListener = binanceWebSocketService.addListener(
      item.symbol,
      (data) => updateMarketData(item.symbol, data),
      '1h',
      'trade'
    )
    removeListeners.push(removeListener)
    console.log(`已为${item.symbol}添加trade频道监听器`)
  })
})

// 组件卸载时执行
onUnmounted(() => {
  // 移除所有监听器
  removeListeners.forEach(remove => remove())
  removeListeners = []

  // 取消所有交易对的trade频道订阅
  marketData.value.forEach(item => {
    binanceWebSocketService.unsubscribeFromSymbol(item.symbol, '1h', 'trade')
  })
  console.log('已取消所有trade频道订阅')
})
</script>

<template>
  <section class="market-overview">
    <div class="container">
      <div class="section-header">
        <h2 class="section-title">市场概览</h2>
        <div class="section-actions">
          <ElButton type="text" icon="RefreshCw" @click="refreshData">
            <ElIcon><Refresh /></ElIcon>
            刷新
          </ElButton>
        </div>
      </div>


      <div class="market-table">
        <ElTable :data="marketData" stripe style="width: 100%">
          <ElTableColumn prop="symbol" label="交易对" width="100" />
          <ElTableColumn prop="name" label="名称" width="120" />
          <ElTableColumn prop="price" label="价格" width="120">
            <template #default="scope">
              ${{ scope.row.price.toFixed(2) }}
            </template>
          </ElTableColumn>
          <ElTableColumn prop="change" label="24h变化" width="120">
            <template #default="scope">
              <span :class="scope.row.change >= 0 ? 'text-green' : 'text-red'">
                <ElIcon v-if="scope.row.change >= 0"><TrendCharts /></ElIcon>
                <ElIcon v-else><TrendCharts /></ElIcon>
                {{ scope.row.change }}%
              </span>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="volume" label="24h成交量" width="150">
            <template #default="scope">
              ${{ (scope.row.volume / 1000000).toFixed(2) }}M
            </template>
          </ElTableColumn>

        </ElTable>
      </div>
    </div>
  </section>
</template>

<style scoped>
.market-overview {
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.container {
  width: 100%;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: bold;
  color: #111827;
}

.trading-pairs {
  margin-bottom: 1.5rem;
}

.pairs-title {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: #4b5563;
}

.pairs-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.market-table {
  overflow-x: auto;
}

.text-green {
  color: #10b981;
}

.text-red {
  color: #ef4444;
}
</style>