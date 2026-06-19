<template>
<div class="container mx-auto p-4 max-w-4xl">
    <header class="text-2xl font-bold mb-6 text-gray-800">QTradeAnalysis</header>
    
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
        <div class="flex justify-end mb-6">
            <button 
                :class="webSocketService.state.connectionStatus === 'disconnected' ? 'bg-green-500 hover:bg-green-600' : 'bg-red-500 hover:bg-red-600'"
                class="px-4 py-2 rounded-md text-white transition"
                @click="socketController"
            >
                {{ webSocketService.state.connectionStatus === 'disconnected' ? '获取数据' : '断开链接' }}
            </button>
        </div>
        
        <div class="mb-6">
            <h2 class="text-sm font-medium text-gray-500 mb-2">交易对</h2>
            <div class="flex flex-wrap gap-2">
                <button 
                    v-for="pair in usedTradePairs" 
                    :key="pair"
                    @click="selectTradePair(pair)"
                    :class="selectedTradePair === pair ? 'bg-blue-600' : 'bg-blue-500 hover:bg-blue-600'"
                    class="px-4 py-2 rounded-md text-white transition"
                >
                    {{ pair }}
                </button>
            </div>
        </div>
        
        <div>
            <h2 class="text-sm font-medium text-gray-500 mb-2">时间周期</h2>
            <div class="flex flex-wrap gap-2">
                <button 
                    v-for="interval in intervals" 
                    :key="interval"
                    @click="selectInterval(interval)"
                    :class="selectedInterval === interval ? 'bg-blue-600' : 'bg-blue-500 hover:bg-blue-600'"
                    class="px-4 py-2 rounded-md text-white transition"
                >
                    {{ interval }}
                </button>
            </div>
        </div>
    </div>
    
    <!-- 图表展示区域 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 class="text-lg font-semibold mb-4 text-gray-800">价格走势图</h2>
      <div class="h-[400px]">
        <Line
          :data="chartData"
          :options="{
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: false,
                title: { display: true, text: '价格 (USDT)' }
              },
              x: {
                title: { display: true, text: '时间' }
              }
            }
          }"
        ></Line>
      </div>
    </div>

    <!-- 分析结果和交易建议 -->
    <div class="bg-white rounded-lg shadow-md p-[20px] mb-6">
      <h2 class="text-lg font-semibold mb-4 text-gray-800">技术分析与交易建议</h2>
      <div v-if="loading" class="text-center py-10">加载分析中...</div>
      <div v-else-if="analysisResults">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div class="p-4 bg-blue-50 rounded-lg">
            <h3 class="font-medium text-blue-700 mb-2">趋势分析</h3>
            <p>{{ analysisResults.trendAnalysis }}</p>
          </div>
          <div class="p-4 bg-green-50 rounded-lg">
            <h3 class="font-medium text-green-700 mb-2">支撑阻力位</h3>
            <p>支撑: {{ analysisResults.supportLevel.toFixed(2) }} USDT</p>
            <p>阻力: {{ analysisResults.resistanceLevel.toFixed(2) }} USDT</p>
          </div>
        </div>

        <div class="p-4 rounded-lg bg-gray-50 border-l-4 border-gray-500">
          <h3 class="font-bold text-lg mb-2">交易建议: {{ analysisResults.tradeSignal }}</h3>
          <p class="text-gray-700">{{ analysisResults.signalReasoning }}</p>
        </div>
      </div>
      <div v-else class="text-center py-10 text-gray-500">
        选择交易对并点击"获取数据"开始分析
      </div>
    </div>
</div>
</template>

<script>
import { defineComponent, ref, watch } from 'vue';
import { Line } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement } from 'chart.js';
import binanceWebSocketService from '../services/binanceWebSocket';
import { technicalAnalysisService } from '../services/technicalAnalysisService';

// 注册Chart.js组件
ChartJS.register(Title, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement);
export default defineComponent({
  components: { Line },
  setup() {
    // 响应式数据
    const selectedTradePair = ref('BTCUSDT');
    const selectedInterval = ref('1h');
    const klineData = ref([]);
    const chartData = ref({ labels: [], datasets: [] });
    const analysisResults = ref(null);
    const loading = ref(false);

    // 初始化图表数据
    const initChart = () => {
      chartData.value = {
        labels: [],
        datasets: [{
          label: '收盘价',
          data: [],
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          tension: 0.3,
          fill: true
        }]
      };
    };

    // 处理WebSocket数据
    const handleKlineUpdate = (data) => {
      klineData.value = [...klineData.value.slice(-99), data];
      chartData.value.labels = klineData.value.map(item => new Date(item.time).toLocaleTimeString());
      chartData.value.datasets[0].data = klineData.value.map(item => item.close);

      // 执行技术分析
      analysisResults.value = technicalAnalysisService.analyze(klineData.value);
      loading.value = false;
    };

    // 选择交易对
    const selectTradePair = (pair) => {
      selectedTradePair.value = pair;
      binanceWebSocketService.updateSubscription(pair, selectedInterval.value);
      klineData.value = [];
      initChart();
    };

    // 选择时间周期
    const selectInterval = (interval) => {
      selectedInterval.value = interval;
      binanceWebSocketService.updateSubscription(selectedTradePair.value, interval);
      klineData.value = [];
      initChart();
    };

    // 连接/断开WebSocket
    const socketController = () => {
      if (binanceWebSocketService.state.connectionStatus === 'disconnected') {
        loading.value = true;
        binanceWebSocketService.connect();
        binanceWebSocketService.on('klineUpdate', handleKlineUpdate);
      } else {
        binanceWebSocketService.disconnect();
        binanceWebSocketService.off('klineUpdate', handleKlineUpdate);
      }
    };

    // 初始化
    initChart();

    return {
      selectedTradePair,
      selectedInterval,
      usedTradePairs: ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT'],
      intervals: ['1m', '3m', '5m', '15m', '1h', '4h', '1d'],
      webSocketService: binanceWebSocketService,
      chartData,
      analysisResults,
      loading,
      selectTradePair,
      selectInterval,
      socketController
    };
  }
});

</script>

<style scoped>
/* 基础动画定义 */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* 数据加载动画类 */
.loading {
    animation: fadeIn 0.3s ease-out;
}
</style>