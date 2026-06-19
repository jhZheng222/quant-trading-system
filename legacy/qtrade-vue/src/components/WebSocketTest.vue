<template>
  <div class="websocket-test">
    <h2>Binance WebSocket Test</h2>
    <p>Check browser console for debug information</p>
    <button @click="testWebSocket">Start Test</button>
    <div v-if="status">{{ status }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import binanceService from '../services/binanceWebSocket'

const status = ref('')

onMounted(() => {
  console.log('WebSocketTest component mounted')
  status.value = 'Component ready. Click Start Test to begin.'
})

function testWebSocket() {
  console.log('Starting WebSocket test from component')
  status.value = 'Testing WebSocket connection...'
  binanceService.testWebSocket()
}
</script>

<style scoped>
.websocket-test {
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  max-width: 400px;
  margin: 20px auto;
}

h2 {
  color: #333;
}

button {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 10px 15px;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 10px;
}

button:hover {
  background-color: #3aa876;
}
</style>