<script setup>
// 引入必要的组件
import { ref } from 'vue'
import { ElCard, ElButton, ElIcon } from 'element-plus'
import { TrendCharts, InfoFilled, Check, Close, SortDown } from '@element-plus/icons-vue'

// 交易建议数据
const tradingAdvice = ref({
  recommendation: 'buy',
  confidence: 85,
  entryPrice: 42400,
  takeProfit: 43500,
  stopLoss: 41800,
  riskRewardRatio: 1.5,
  timeFrame: '24小时',
  analysis: '价格突破关键阻力位，RSI和MACD指标显示看涨趋势。成交量增加表明买盘力量增强。建议在回调至$42,400附近买入，设置止损在$41,800，止盈在$43,500。',
  factors: [
    { name: '技术指标', value: '看涨', positive: true },
    { name: '成交量', value: '增加', positive: true },
    { name: '市场情绪', value: '乐观', positive: true },
    { name: '趋势', value: '上升', positive: true },
    { name: '波动性', value: '中等', positive: false }
  ]
})

// 获取建议对应的图标
const getRecommendationIcon = () => {
  if (tradingAdvice.value.recommendation === 'buy') {
    return 'TrendCharts'
  } else if (tradingAdvice.value.recommendation === 'sell') {
    return 'SortDown'
  } else {
    return 'InfoFilled'
  }
}

// 获取建议对应的样式类
const getRecommendationClass = () => {
  if (tradingAdvice.value.recommendation === 'buy') {
    return 'recommendation-buy'
  } else if (tradingAdvice.value.recommendation === 'sell') {
    return 'recommendation-sell'
  } else {
    return 'recommendation-hold'
  }
}

// 获取建议文本
const getRecommendationText = () => {
  if (tradingAdvice.value.recommendation === 'buy') {
    return '买入'
  } else if (tradingAdvice.value.recommendation === 'sell') {
    return '卖出'
  } else {
    return '持有'
  }
}
</script>

<template>
  <section class="trading-advice">
    <ElCard class="advice-card">
      <div class="card-header">
        <h2 class="section-title">交易建议</h2>
        <div :class="'recommendation-badge ' + getRecommendationClass()">
          <component :is="getRecommendationIcon()" class="icon" />
          {{ getRecommendationText() }} (信心: {{ tradingAdvice.confidence }}%)
        </div>
      </div>

      <div class="advice-metrics">
        <div class="metric-item">
          <span class="metric-label">入场价格:</span>
          <span class="metric-value">${{ tradingAdvice.entryPrice.toFixed(2) }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">止盈价格:</span>
          <span class="metric-value">${{ tradingAdvice.takeProfit.toFixed(2) }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">止损价格:</span>
          <span class="metric-value">${{ tradingAdvice.stopLoss.toFixed(2) }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">风险回报比:</span>
          <span class="metric-value">{{ tradingAdvice.riskRewardRatio }}:1</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">时间周期:</span>
          <span class="metric-value">{{ tradingAdvice.timeFrame }}</span>
        </div>
      </div>

      <div class="advice-analysis">
        <h3 class="analysis-title">分析依据</h3>
        <p class="analysis-text">{{ tradingAdvice.analysis }}</p>
      </div>

      <div class="influence-factors">
        <h3 class="factors-title">影响因素</h3>
        <div class="factors-list">
          <div v-for="factor in tradingAdvice.factors" :key="factor.name" class="factor-item">
            <div class="factor-name">{{ factor.name }}</div>
            <div class="factor-value" :class="factor.positive ? 'positive' : 'negative'">
              <component :is="factor.positive ? 'Check' : 'Close'" class="icon" />
              {{ factor.value }}
            </div>
          </div>
        </div>
      </div>

      <div class="advice-actions">
        <ElButton type="primary" :disabled="tradingAdvice.recommendation !== 'buy'">
          执行买入
        </ElButton>
        <ElButton type="danger" :disabled="tradingAdvice.recommendation !== 'sell'">
          执行卖出
        </ElButton>
        <ElButton type="text">
          忽略
        </ElButton>
      </div>
    </ElCard>
  </section>
</template>

<style scoped>
.trading-advice {
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}

.advice-card {
  border: none !important;
  box-shadow: none !important;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: bold;
  color: #111827;
  margin: 0;
}

.recommendation-badge {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 600;
}

.recommendation-buy {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.recommendation-sell {
  background-color: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.recommendation-hold {
  background-color: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.icon {
  margin-right: 0.5rem;
}

.advice-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.metric-item {
  display: flex;
  flex-direction: column;
}

.metric-label {
  font-size: 0.75rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.metric-value {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
}

.advice-analysis {
  margin-bottom: 1.5rem;
}

.analysis-title {
  font-size: 1rem;
  font-weight: 600;
  color: #4b5563;
  margin-bottom: 0.75rem;
}

.analysis-text {
  font-size: 0.875rem;
  color: #6b7280;
  line-height: 1.5;
}

.influence-factors {
  margin-bottom: 1.5rem;
}

.factors-title {
  font-size: 1rem;
  font-weight: 600;
  color: #4b5563;
  margin-bottom: 0.75rem;
}

.factors-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}

.factor-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background-color: #f9fafb;
  border-radius: 0.375rem;
}

.factor-name {
  font-size: 0.875rem;
  color: #6b7280;
}

.factor-value {
  display: flex;
  align-items: center;
  font-size: 0.875rem;
  font-weight: 500;
}

.positive {
  color: #10b981;
}

.negative {
  color: #ef4444;
}

.advice-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}
</style>