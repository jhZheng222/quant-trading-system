<template>
  <div class="technical-analysis-container">
    <h3>技术分析</h3>
    <div class="analysis-header">
      <div class="symbol-info">
        <span class="symbol">{{ currentSymbol.toUpperCase() }}</span>
        <span class="interval">({{ currentInterval }})</span>
      </div>
      <div class="prediction-badge" :class="predictionClass">
        {{ prediction }}
      </div>
    </div>

    <div class="analysis-results">
      <div class="indicator-group">
        <h4>移动平均线 (SMA)</h4>
        <div class="indicator-item">
          <span class="label">SMA 20:</span>
          <span class="value">{{ sma20 }}</span>
        </div>
        <div class="indicator-item">
          <span class="label">SMA 50:</span>
          <span class="value">{{ sma50 }}</span>
        </div>
        <div class="indicator-item">
          <span class="label">SMA 200:</span>
          <span class="value">{{ sma200 }}</span>
        </div>
      </div>

      <div class="indicator-group">
        <h4>相对强弱指数 (RSI)</h4>
        <div class="indicator-item rsi">
          <span class="label">RSI 14:</span>
          <span class="value" :class="rsiClass">{{ rsi14 }}</span>
        </div>
      </div>

      <div class="indicator-group">
        <h4>布林带</h4>
        <div class="indicator-item">
          <span class="label">上轨:</span>
          <span class="value">{{ bollingerUpper }}</span>
        </div>
        <div class="indicator-item">
          <span class="label">中轨:</span>
          <span class="value">{{ bollingerMiddle }}</span>
        </div>
        <div class="indicator-item">
          <span class="label">下轨:</span>
          <span class="value">{{ bollingerLower }}</span>
        </div>
      </div>

      <div class="indicator-group">
        <h4>MACD</h4>
        <div class="indicator-item">
          <span class="label">MACD线:</span>
          <span class="value">{{ macdLine }}</span>
        </div>
        <div class="indicator-item">
          <span class="label">信号线:</span>
          <span class="value">{{ signalLine }}</span>
        </div>
        <div class="indicator-item">
          <span class="label">柱状图:</span>
          <span class="value" :class="histogramClass">{{ histogram }}</span>
        </div>
      </div>
    </div>

    <div class="prediction-section">
      <h4>预测分析</h4>
      <div class="prediction-details">
        <div class="prediction-item">
          <span class="label">预测方向:</span>
          <span class="value">{{ prediction }}</span>
        </div>
        <div class="prediction-item">
          <span class="label">支撑位:</span>
          <span class="value">{{ supportLevel }}</span>
        </div>
        <div class="prediction-item">
          <span class="label">阻力位:</span>
          <span class="value">{{ resistanceLevel }}</span>
        </div>
      </div>

      <div class="reasons-section">
        <h4>分析依据</h4>
        <ul v-if="reasons.length > 0" class="reasons-list">
          <li v-for="(reason, index) in reasons" :key="index">{{ reason }}</li>
        </ul>
        <p v-else>暂无分析依据</p>
      </div>
    </div>

    <div v-if="volatilityAlert" class="alert alert-danger">
      <strong>异常波动提醒!</strong> 检测到价格异常波动，请关注市场变化。
    </div>
  </div>
</template>

<script>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { technicalAnalysisService } from '../services/technicalAnalysisService'
import binanceWebSocketService from '../services/binanceWebSocket.js'

export default {
  name: 'TechnicalAnalysis',
  props: {
    symbol: {
      type: String,
      required: true
    },
    interval: {
      type: String,
      default: '1h'
    }
  },
  setup(props) {
    const currentSymbol = ref(props.symbol)
    const currentInterval = ref(props.interval)
    const sma20 = ref('--')
    const sma50 = ref('--')
    const sma200 = ref('--')
    const rsi14 = ref('--')
    const bollingerUpper = ref('--')
    const bollingerMiddle = ref('--')
    const bollingerLower = ref('--')
    const macdLine = ref('--')
    const signalLine = ref('--')
    const histogram = ref('--')
    const prediction = ref('中性')
    const reasons = ref([])
    const supportLevel = ref('--')
    const resistanceLevel = ref('--')
    const volatilityAlert = ref(false)

    // 监听props变化
    watch(() => props.symbol,
      (newSymbol) => {
        currentSymbol.value = newSymbol
        updateAnalysis()
      }
    )

    watch(() => props.interval,
      (newInterval) => {
        currentInterval.value = newInterval
        updateAnalysis()
      }
    )

    // 更新技术分析数据
    const updateAnalysis = () => {
      const indicators = technicalAnalysisService.getIndicators(
        currentSymbol.value,
        currentInterval.value
      )

      if (indicators) {
        sma20.value = indicators.sma[20]?.toFixed(2) || '--'
        sma50.value = indicators.sma[50]?.toFixed(2) || '--'
        sma200.value = indicators.sma[200]?.toFixed(2) || '--'
        rsi14.value = indicators.rsi[14]?.toFixed(2) || '--'
        bollingerUpper.value = indicators.bollingerBands?.upper?.toFixed(2) || '--'
        bollingerMiddle.value = indicators.bollingerBands?.middle?.toFixed(2) || '--'
        bollingerLower.value = indicators.bollingerBands?.lower?.toFixed(2) || '--'
        macdLine.value = indicators.macd?.macdLine?.toFixed(4) || '--'
        signalLine.value = indicators.macd?.signalLine?.toFixed(4) || '--'
        histogram.value = indicators.macd?.histogram?.toFixed(4) || '--'
        volatilityAlert.value = indicators.volatilityAlert || false
      } else {
        sma20.value = '--'
        sma50.value = '--'
        sma200.value = '--'
        rsi14.value = '--'
        bollingerUpper.value = '--'
        bollingerMiddle.value = '--'
        bollingerLower.value = '--'
        macdLine.value = '--'
        signalLine.value = '--'
        histogram.value = '--'
        volatilityAlert.value = false
      }

      // 获取预测
      const predictionResult = technicalAnalysisService.getPricePrediction(
        currentSymbol.value,
        currentInterval.value
      )

      if (predictionResult) {
        prediction.value = predictionResult.prediction
        reasons.value = predictionResult.reasons
        supportLevel.value = predictionResult.supportLevel?.toFixed(2) || '--'
        resistanceLevel.value = predictionResult.resistanceLevel?.toFixed(2) || '--'
      } else {
        prediction.value = '中性'
        reasons.value = []
        supportLevel.value = '--'
        resistanceLevel.value = '--'
      }
    }

    // 订阅K线数据更新
    const unsubscribe = binanceWebSocketService.addListener(
      currentSymbol.value,
      () => {
        updateAnalysis()
      },
      currentInterval.value
    )

    // 组件挂载时
    onMounted(() => {
      // 初始化分析数据
      updateAnalysis()
    })

    // 组件卸载时
    onUnmounted(() => {
      // 取消订阅
      unsubscribe()
    })

    // 计算预测标签的类名
    const predictionClass = ref('')
    watch(prediction, (newPrediction) => {
      if (newPrediction === '看涨') {
        predictionClass.value = 'badge bullish'
      } else if (newPrediction === '看跌') {
        predictionClass.value = 'badge bearish'
      } else {
        predictionClass.value = 'badge neutral'
      }
    })

    // 计算RSI的类名
    const rsiClass = ref('')
    watch(rsi14, (newRsi) => {
      const rsiValue = parseFloat(newRsi)
      if (rsiValue > 70) {
        rsiClass.value = 'overbought'
      } else if (rsiValue < 30) {
        rsiClass.value = 'oversold'
      } else {
        rsiClass.value = ''
      }
    })

    // 计算MACD柱状图的类名
    const histogramClass = ref('')
    watch(histogram, (newHistogram) => {
      const histogramValue = parseFloat(newHistogram)
      if (histogramValue > 0) {
        histogramClass.value = 'bullish'
      } else if (histogramValue < 0) {
        histogramClass.value = 'bearish'
      } else {
        histogramClass.value = ''
      }
    })

    return {
      currentSymbol,
      currentInterval,
      sma20,
      sma50,
      sma200,
      rsi14,
      bollingerUpper,
      bollingerMiddle,
      bollingerLower,
      macdLine,
      signalLine,
      histogram,
      prediction,
      reasons,
      supportLevel,
      resistanceLevel,
      volatilityAlert,
      predictionClass,
      rsiClass,
      histogramClass
    }
  }
}
</script>

<style scoped>
.technical-analysis-container {
  background-color: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 20px;
}

h3 {
  margin-top: 0;
  margin-bottom: 16px;
  color: #333;
  font-size: 1.25rem;
}

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eaeaea;
}

.symbol-info {
  display: flex;
  align-items: center;
}

.symbol {
  font-size: 1.5rem;
  font-weight: bold;
  color: #333;
}

.interval {
  margin-left: 8px;
  font-size: 0.9rem;
  color: #666;
  background-color: #eaeaea;
  padding: 2px 8px;
  border-radius: 12px;
}

.prediction-badge {
  padding: 4px 10px;
  border-radius: 16px;
  font-weight: bold;
  font-size: 0.9rem;
}

.badge {
  padding: 4px 10px;
  border-radius: 16px;
  font-weight: bold;
}

.bullish {
  background-color: #4CAF50;
  color: white;
}

.bearish {
  background-color: #F44336;
  color: white;
}

.neutral {
  background-color: #FFC107;
  color: #333;
}

.analysis-results {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.indicator-group {
  background-color: white;
  border-radius: 6px;
  padding: 15px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

h4 {
  margin-top: 0;
  margin-bottom: 12px;
  color: #444;
  font-size: 1rem;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 8px;
}

.indicator-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.label {
  color: #666;
}

.value {
  font-weight: 500;
}

.rsi .overbought {
  color: #F44336;
}

.rsi .oversold {
  color: #4CAF50;
}

.prediction-section {
  background-color: white;
  border-radius: 6px;
  padding: 15px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.prediction-details {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  margin-bottom: 15px;
}

.prediction-item {
  display: flex;
  justify-content: space-between;
}

.reasons-section {
  margin-top: 15px;
}

.reasons-list {
  padding-left: 20px;
  margin: 0;
}

.reasons-list li {
  margin-bottom: 5px;
  color: #555;
}

.alert {
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.alert-danger {
  background-color: #ffebee;
  color: #b71c1c;
  border: 1px solid #ffcdd2;
}
</style>