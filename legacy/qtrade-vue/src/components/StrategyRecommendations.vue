<script setup>
// 引入必要的组件
import { ref } from 'vue'
import { ElCard, ElButton, ElIcon } from 'element-plus'
import { TrendCharts, InfoFilled, ArrowRight, SortDown } from '@element-plus/icons-vue'

// 策略推荐数据
const strategies = ref([
  {
    id: 1,
    name: '突破交易策略',
    type: 'bullish',
    risk: 'medium',
    expectedReturn: '5-8%',
    timeFrame: '1-3天',
    description: '当价格突破关键阻力位并伴随成交量增加时买入，设置止损在最近的支撑位下方。',
    suitability: '适合有一定经验的交易者',
    popularity: 85
  },
  {
    id: 2,
    name: '均值回归策略',
    type: 'neutral',
    risk: 'low',
    expectedReturn: '2-4%',
    timeFrame: '24小时',
    description: '当价格偏离移动平均线超过一定阈值时卖出，在价格回归均线时买入。',
    suitability: '适合稳健型交易者',
    popularity: 75
  },
  {
    id: 3,
    name: 'MACD交叉策略',
    type: 'bullish',
    risk: 'medium',
    expectedReturn: '4-6%',
    timeFrame: '2-5天',
    description: '当MACD线从下方穿过信号线时买入，在MACD线从上方穿过信号线时卖出。',
    suitability: '适合技术分析交易者',
    popularity: 90
  }
])

// 获取策略类型对应的样式类
const getStrategyClass = (type) => {
  switch (type) {
    case 'bullish':
      return 'strategy-bullish'
    case 'bearish':
      return 'strategy-bearish'
    case 'neutral':
      return 'strategy-neutral'
    default:
      return 'strategy-neutral'
  }
}

// 获取策略类型对应的图标
const getStrategyIcon = (type) => {
  switch (type) {
    case 'bullish':
      return 'TrendCharts'
    case 'bearish':
      return 'SortDown'
    case 'neutral':
      return 'InfoFilled'
    default:
      return 'InfoFilled'
  }
}

// 获取策略类型文本
const getStrategyText = (type) => {
  switch (type) {
    case 'bullish':
      return '看涨'
    case 'bearish':
      return '看跌'
    case 'neutral':
      return '中性'
    default:
      return '未知'
  }
}
</script>

<template>
  <section class="strategy-recommendations">
    <ElCard class="strategies-card">
      <h2 class="section-title">策略推荐</h2>

      <div class="strategies-list">
        <div v-for="strategy in strategies" :key="strategy.id" class="strategy-item" :class="getStrategyClass(strategy.type)">
          <div class="strategy-header">
            <h3 class="strategy-name">{{ strategy.name }}</h3>
            <div class="strategy-type-badge">
              <component :is="getStrategyIcon(strategy.type)" class="icon" />
              {{ getStrategyText(strategy.type) }}
            </div>
          </div>

          <div class="strategy-metrics">
            <div class="metric-item">
              <span class="metric-label">风险等级:</span>
              <span class="metric-value">{{ strategy.risk }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">预期收益:</span>
              <span class="metric-value">{{ strategy.expectedReturn }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">时间周期:</span>
              <span class="metric-value">{{ strategy.timeFrame }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">流行度:</span>
              <span class="metric-value">{{ strategy.popularity }}%</span>
            </div>
          </div>

          <div class="strategy-description">
            {{ strategy.description }}
          </div>

          <div class="strategy-suitability">
            <span class="suitability-label">适合人群:</span>
            <span class="suitability-value">{{ strategy.suitability }}</span>
          </div>

          <div class="strategy-actions">
            <ElButton type="primary" size="small">
              应用策略
              <ElIcon><ArrowRight class="ml-1" /></ElIcon>
            </ElButton>
          </div>
        </div>
      </div>
    </ElCard>
  </section>
</template>

<style scoped>
.strategy-recommendations {
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}

.strategies-card {
  border: none !important;
  box-shadow: none !important;
}

.section-title {
  font-size: 1.25rem;
  font-weight: bold;
  color: #111827;
  margin-bottom: 1.5rem;
}

.strategies-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.strategy-item {
  padding: 1.5rem;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.strategy-bullish {
  border-left: 4px solid #10b981;
  background-color: rgba(16, 185, 129, 0.05);
}

.strategy-bearish {
  border-left: 4px solid #ef4444;
  background-color: rgba(239, 68, 68, 0.05);
}

.strategy-neutral {
  border-left: 4px solid #6b7280;
  background-color: rgba(107, 114, 128, 0.05);
}

.strategy-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.strategy-name {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.strategy-type-badge {
  display: flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.strategy-bullish .strategy-type-badge {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.strategy-bearish .strategy-type-badge {
  background-color: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.strategy-neutral .strategy-type-badge {
  background-color: rgba(107, 114, 128, 0.1);
  color: #6b7280;
}

.icon {
  margin-right: 0.25rem;
  font-size: 0.875rem;
}

.strategy-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
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
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
}

.strategy-description {
  font-size: 0.875rem;
  color: #4b5563;
  margin-bottom: 1rem;
  line-height: 1.5;
}

.strategy-suitability {
  display: flex;
  margin-bottom: 1.5rem;
}

.suitability-label {
  font-size: 0.75rem;
  color: #6b7280;
  margin-right: 0.5rem;
}

.suitability-value {
  font-size: 0.875rem;
  color: #111827;
}

.strategy-actions {
  display: flex;
  justify-content: flex-end;
}

.ml-1 {
  margin-left: 4px;
}
</style>