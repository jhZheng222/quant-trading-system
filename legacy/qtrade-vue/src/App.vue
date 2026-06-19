<script setup>
// 引入路由视图
import { RouterView } from 'vue-router'
// 导入Binance服务
import binanceService from './services/binanceWebSocket.js'
</script>

<template>
  <div class="debug-panel" style="position: fixed; bottom: 20px; left: 20px; background: rgba(0,0,0,0.8); color: white; padding: 10px; border-radius: 5px; z-index: 9999;">
    <h3>WebSocket状态</h3>
    <p>符号: {{ binanceService?.subscribedSymbol?.value }} ({{ typeof binanceService?.subscribedSymbol?.value }})</p>
    <p>时间间隔: {{ binanceService?.interval?.value }} ({{ typeof binanceService?.interval?.value }})</p>
    <p>连接状态: {{ binanceService?.state?.connectionStatus }}</p>
    <p v-if="binanceService?.errorMessage?.value" style="color: red;">错误: {{ binanceService.errorMessage.value }}</p>
  </div>
  <div class="app-container">
    <!-- 路由视图 -->
    <RouterView />
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  font-family: 'Inter', sans-serif;
}
</style>
