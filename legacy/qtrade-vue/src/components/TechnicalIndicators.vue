<script setup>
// 引入必要的组件
import { ref } from 'vue'
import { ElCard, ElRow, ElCol, ElProgress, ElTag } from 'element-plus'
import { TrendCharts, Warning } from '@element-plus/icons-vue'

// 技术指标数据
const indicators = ref([
  {
    name: 'RSI (14)',
    value: 58.7,
    status: 'neutral',
    description: '相对强弱指数处于中性区域'
  },
  {
    name: 'MACD',
    value: 12.3,
    status: 'bullish',
    description: 'MACD线在信号线之上，呈看涨趋势'
  },
  {
    name: '布林带',
    value: 42650,
    status: 'bearish',
    description: '价格接近上轨，可能面临压力'
  },
  {
    name: '移动平均线 (50)',
    value: 41800,
    status: 'bullish',
    description: '价格在50日均线上方，呈看涨趋势'
  },
  {
    name: '随机指标 (KDJ)',
    value: 72.1,
    status: 'bearish',
    description: '随机指标进入超买区域，可能回调'
  }
])

// 获取状态对应的样式类
const getStatusClass = (status) => {
  switch (status) {
    case 'bullish':
      return 'status-bullish'
    case 'bearish':
      return 'status-bearish'
    default:
      return 'status-neutral'
  }
}

// 获取状态对应的图标
const getStatusIcon = (status) => {
  switch (status) {
    case 'bullish':
      return 'TrendCharts'
    case 'bearish':
      return 'TrendCharts'
    default:
      return 'Warning'
  }
}
</script>

<template>
  <section class="technical-indicators">
    <h2 class="section-title">技术指标分析</h2>
    <div class="indicators-grid">
      <ElCard v-for="indicator in indicators" :key="indicator.name" class="indicator-card">
        <div class="indicator-header">
          <h3 class="indicator-name">{{ indicator.name }}</h3>
          <div :class="getStatusClass(indicator.status) + ' status-badge'">
  <ElIcon>
    <TrendCharts v-if="indicator.status === 'bullish' || indicator.status === 'bearish'" />
    <Warning v-else />
  </ElIcon>
  <span v-if="indicator.status === 'bullish'">看涨</span>
  <span v-else-if="indicator.status === 'bearish'">看跌</span>
  <span v-else>中性</span>
</div>
        </div>
        <div class="indicator-value">{{ indicator.value }}</div>
        <ElProgress
          :percentage="indicator.name === 'RSI (14)' ? indicator.value : 50"
          :color="indicator.status === 'bullish' ? '#10b981' : indicator.status === 'bearish' ? '#ef4444' : '#6b7280'"
          :show-text="false"
          class="indicator-progress"
        />
        <div class="indicator-description">{{ indicator.description }}</div>
      </ElCard>
    </div>
  </section>
</template>

<style scoped>
.technical-indicators {
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: bold;
  color: #111827;
  margin-bottom: 1.5rem;
}

.indicators-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

.indicator-card {
  border: none !important;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
}

.indicator-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.indicator-name {
  font-size: 1rem;
  font-weight: 600;
  color: #4b5563;
  margin: 0;
}

.status-badge {
  display: flex;
  align-items: center;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.status-bullish {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.status-bearish {
  background-color: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.status-neutral {
  background-color: rgba(107, 114, 128, 0.1);
  color: #6b7280;
}

.icon {
  margin-right: 0.25rem;
  font-size: 0.875rem;
}

.indicator-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #111827;
  margin-bottom: 0.5rem;
}

.indicator-progress {
  height: 6px !important;
  margin-bottom: 0.75rem;
}

.indicator-description {
  font-size: 0.875rem;
  color: #6b7280;
}

@media (min-width: 768px) {
  .indicators-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>