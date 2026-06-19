<script setup>
// 引入必要的组件
import { ref } from 'vue'
import { ElCard, ElAlert, ElIcon } from 'element-plus'
import { Warning, TrendCharts, InfoFilled } from '@element-plus/icons-vue'

// 波动提醒数据
const alerts = ref([
  {
    id: 1,
    type: 'high',
    symbol: 'BTCUSDT',
    priceChange: 3.2,
    volumeChange: 45,
    time: '刚刚',
    description: 'BTCUSDT在过去15分钟内价格上涨3.2%，成交量增加45%'
  },
  {
    id: 2,
    type: 'medium',
    symbol: 'ETHUSDT',
    priceChange: 2.1,
    volumeChange: 30,
    time: '10分钟前',
    description: 'ETHUSDT在过去30分钟内价格上涨2.1%，成交量增加30%'
  },
  {
    id: 3,
    type: 'low',
    symbol: 'SOLUSDT',
    priceChange: -1.5,
    volumeChange: 20,
    time: '30分钟前',
    description: 'SOLUSDT在过去1小时内价格下跌1.5%，成交量增加20%'
  }
])

// 获取提醒类型对应的样式
const getAlertType = (type) => {
  switch (type) {
    case 'high':
      return 'error'
    case 'medium':
      return 'warning'
    case 'low':
      return 'info'
    default:
      return 'info'
  }
}

// 获取提醒图标
const getAlertIcon = (type, priceChange) => {
  if (type === 'high') {
    return 'Warning'
  } else if (priceChange > 0) {
    return 'TrendCharts'
  } else if (priceChange < 0) {
    return 'TrendCharts'
  } else {
    return 'InfoFilled'
  }
}
</script>

<template>
  <section class="volatility-alerts">
    <ElCard class="alerts-card">
      <h2 class="section-title">异常波动提醒</h2>

      <div class="alerts-list">
        <ElAlert
          v-for="alert in alerts"
          :key="alert.id"
          :type="getAlertType(alert.type)"
          :title="alert.symbol + ' ' + (alert.priceChange > 0 ? '上涨' : '下跌') + Math.abs(alert.priceChange) + '%'"
          :closable="false"
          show-icon
          class="alert-item"
        >
          <template #icon>
  <ElIcon>
    <Warning v-if="alert.type === 'high'" />
    <TrendCharts v-else-if="alert.priceChange > 0" />
    <TrendCharts v-else-if="alert.priceChange < 0" />
    <InfoFilled v-else />
  </ElIcon>
</template>
          <div class="alert-content">
            <div class="alert-time">{{ alert.time }}</div>
            <div class="alert-description">{{ alert.description }}</div>
          </div>
        </ElAlert>
      </div>
    </ElCard>
  </section>
</template>

<style scoped>
.volatility-alerts {
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}

.alerts-card {
  border: none !important;
  box-shadow: none !important;
}

.section-title {
  font-size: 1.25rem;
  font-weight: bold;
  color: #111827;
  margin-bottom: 1.5rem;
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.alert-item {
  border-radius: 0.5rem !important;
}

.alert-content {
  display: flex;
  flex-direction: column;
  margin-top: 0.5rem;
}

.alert-time {
  font-size: 0.75rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.alert-description {
  font-size: 0.875rem;
  color: #4b5563;
}

.icon {
  font-size: 1.25rem;
}
</style>