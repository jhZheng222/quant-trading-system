<template>
  <div class="simple-ws-test">
    <h2>简单WebSocket测试组件</h2>
    <div class="controls">
      <button @click="connect()" :disabled="isConnected">连接WebSocket</button>
      <button @click="disconnect()" :disabled="!isConnected">断开连接</button>
      <button @click="subscribe()" :disabled="!isConnected || isSubscribed">订阅K线数据</button>
      <button @click="unsubscribe()" :disabled="!isConnected || !isSubscribed">取消订阅</button>
    </div>
    <div class="status">
      <p>连接状态: {{ isConnected ? '已连接' : '未连接' }}</p>
      <p>订阅状态: {{ isSubscribed ? '已订阅' : '未订阅' }}</p>
      <p>接收数据数量: {{ dataCount }}</p>
    </div>
    <div class="data-preview">
      <h3>最新K线数据</h3>
      <pre>{{ latestKline ? JSON.stringify(latestKline, null, 2) : '暂无数据' }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

// 状态变量
const isConnected = ref(false)
const isSubscribed = ref(false)
const dataCount = ref(0)
const latestKline = ref(null)
let socket = null
let wsInterval = null

// 连接WebSocket
const connect = () => {
  if (isConnected.value) {
    console.log('WebSocket已经连接')
    return
  }

  console.log('尝试连接到Binance WebSocket...')
  const wsUrl = 'wss://data-stream.binance.vision/ws'
  socket = new WebSocket(wsUrl)

  socket.onopen = () => {
    console.log('WebSocket连接成功')
    isConnected.value = true
  }

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.k && data.e === 'kline') {
        console.log('收到K线数据:', data.k)
        latestKline.value = data.k
        dataCount.value++
      }
    } catch (error) {
      console.error('解析消息出错:', error)
    }
  }

  socket.onclose = () => {
    console.log('WebSocket连接关闭')
    isConnected.value = false
    isSubscribed.value = false
  }

  socket.onerror = (error) => {
    console.error('WebSocket错误:', error)
    isConnected.value = false
  }
}

// 断开WebSocket连接
const disconnect = () => {
  if (socket && isConnected.value) {
    console.log('断开WebSocket连接...')
    socket.close()
    socket = null
    isConnected.value = false
    isSubscribed.value = false
  }
}

// 订阅K线数据
const subscribe = () => {
  if (!isConnected.value) {
    console.error('WebSocket未连接，无法订阅')
    return
  }

  if (isSubscribed.value) {
    console.log('已经订阅过数据')
    return
  }

  console.log('订阅BTCUSDT 1小时K线数据...')
  const message = {
    method: 'SUBSCRIBE',
    params: ['btcusdt@kline_1h'],
    id: Date.now()
  }
  socket.send(JSON.stringify(message))
  isSubscribed.value = true
}

// 取消订阅
const unsubscribe = () => {
  // 由于按钮已禁用，这个检查理论上可以省略，但为了安全起见保留
  if (!isConnected.value || !isSubscribed.value) {
    console.error('未连接或未订阅，无法取消订阅')
    return
  }

  console.log('取消订阅BTCUSDT 1小时K线数据...')
  const message = {
    method: 'UNSUBSCRIBE',
    params: ['btcusdt@kline_1h'],
    id: Date.now()
  }
  try {
    socket.send(JSON.stringify(message))
    isSubscribed.value = false
  } catch (error) {
    console.error('取消订阅失败:', error)
  }
}

// 组件挂载时执行
onMounted(() => {
  console.log('SimpleWsTest组件已挂载')
})

// 组件卸载时执行
onUnmounted(() => {
  console.log('SimpleWsTest组件已卸载，清理资源...')
  disconnect()
})
</script>

<style scoped>
.simple-ws-test {
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
  margin: 20px;
}

.controls {
  margin-bottom: 20px;
}

button {
  margin-right: 10px;
  padding: 8px 12px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background-color: #3aa876;
}

.status {
  margin-bottom: 20px;
}

.data-preview {
  max-height: 300px;
  overflow-y: auto;
  background-color: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
}
</style>