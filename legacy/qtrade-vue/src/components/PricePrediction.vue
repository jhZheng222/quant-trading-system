<script setup>
// 引入必要的组件和库
import { ref, onMounted } from 'vue'
import { ElCard, ElRow, ElCol, ElButton, ElIcon } from 'element-plus'
import { TrendCharts, InfoFilled, CaretBottom, CaretTop } from '@element-plus/icons-vue'
import { Chart, CategoryScale, LinearScale, PointElement, LineElement, LineController, Title, Tooltip, Legend, Filler } from 'chart.js'

// 注册所需的组件
Chart.register(CategoryScale, LinearScale, PointElement, LineElement, LineController, Title, Tooltip, Legend, Filler)

// 预测数据（模拟）
const predictionData = ref([
  { time: '现在', price: 42567.89 },
  { time: '+1小时', price: 42680.23 },
  { time: '+6小时', price: 42950.56 },
  { time: '+12小时', price: 43200.89 },
  { time: '+24小时', price: 43500.12 },
  { time: '+48小时', price: 43800.45 },
  { time: '+7天', price: 45000.67 }
])

// 预测准确度
const predictionAccuracy = ref(78.5)

// 图表实例
let chart = null

// 展开/折叠详情
const isExpanded = ref(false)

// 切换展开/折叠状态
const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

// 创建预测图表
const createPredictionChart = () => {
  const ctx = document.getElementById('predictionChart')
  if (ctx) {
    chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: predictionData.value.map(item => item.time),
        datasets: [{
          label: '预测价格',
          data: predictionData.value.map(item => item.price),
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: '#3b82f6'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
              label: function(context) {
                let label = context.dataset.label || ''
                if (label) {
                  label += ': '
                }
                if (context.parsed.y !== null) {
                  label += new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(context.parsed.y)
                }
                return label
              }
            }
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            }
          },
          y: {
            position: 'right',
            title: {
              display: true,
              text: '价格 (USD)'
            }
          }
        }
      }
    })
  }
}

// 组件挂载时执行
onMounted(() => {
  createPredictionChart()
})
</script>

<template>
  <section class="price-prediction">
    <ElCard class="prediction-card">
      <div class="card-header">
        <div class="header-left">
          <h2 class="section-title">价格预测</h2>
          <div class="prediction-metrics">
            <div class="metric-item">
              <span class="metric-label">预测方向:</span>
              <span class="metric-value bullish"><TrendCharts class="icon" /> 看涨</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">预测准确度:</span>
              <span class="metric-value">{{ predictionAccuracy }}%</span>
            </div>
          </div>
        </div>
        <ElButton type="text" @click="toggleExpand" class="expand-button">
          <ElIcon v-if="isExpanded"><CaretTop /></ElIcon>
          <ElIcon v-else><CaretBottom /></ElIcon>
        </ElButton>
      </div>

      <div class="chart-container">
        <canvas id="predictionChart"></canvas>
      </div>

      <div v-if="isExpanded" class="prediction-details">
        <div class="details-header">
          <h3 class="details-title">预测详情</h3>
          <div class="details-info">
            <InfoFilled class="icon" /> 基于历史数据和机器学习模型预测
          </div>
        </div>

        <div class="prediction-table">
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>预测价格</th>
                <th>变化</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in predictionData" :key="index">
                <td>{{ item.time }}</td>
                <td>${{ item.price.toFixed(2) }}</td>
                <td v-if="index > 0" :class="item.price > predictionData[index-1].price ? 'text-green' : 'text-red'">
                  {{ item.price > predictionData[index-1].price ? '+' : '' }}{{ (item.price - predictionData[index-1].price).toFixed(2) }}
                </td>
                <td v-else>-</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="prediction-insights">
          <h3 class="insights-title">关键洞察</h3>
          <ul class="insights-list">
            <li>价格预计在未来24小时内上涨约2.2%</li>
            <li>7天预测显示价格可能达到$45,000，上涨约5.7%</li>
            <li>短期阻力位在$43,500，支撑位在$42,000</li>
            <li>交易量分析表明买盘力量正在增强</li>
          </ul>
        </div>
      </div>
    </ElCard>
  </section>
</template>

<style scoped>
.price-prediction {
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}

.prediction-card {
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

.header-left {
  flex: 1;
}

.section-title {
  font-size: 1.25rem;
  font-weight: bold;
  color: #111827;
  margin: 0 0 0.5rem 0;
}

.prediction-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
}

.metric-item {
  display: flex;
  align-items: center;
}

.metric-label {
  font-size: 0.875rem;
  color: #6b7280;
  margin-right: 0.5rem;
}

.metric-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
}

.bullish {
  color: #10b981;
}

.expand-button {
  padding: 0 !important;
}

.chart-container {
  height: 250px;
  width: 100%;
  margin-bottom: 1rem;
}

.prediction-details {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.details-title {
  font-size: 1rem;
  font-weight: 600;
  color: #4b5563;
  margin: 0;
}

.details-info {
  font-size: 0.875rem;
  color: #6b7280;
  display: flex;
  align-items: center;
}

.icon {
  margin-right: 0.25rem;
  font-size: 0.875rem;
}

.prediction-table {
  width: 100%;
  margin-bottom: 1.5rem;
  overflow-x: auto;
}

.prediction-table table {
  width: 100%;
  border-collapse: collapse;
}

.prediction-table th,
.prediction-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.prediction-table th {
  font-size: 0.875rem;
  font-weight: 600;
  color: #6b7280;
}

.prediction-table td {
  font-size: 0.875rem;
  color: #111827;
}

.text-green {
  color: #10b981;
}

.text-red {
  color: #ef4444;
}

.prediction-insights {
  margin-top: 1.5rem;
}

.insights-title {
  font-size: 1rem;
  font-weight: 600;
  color: #4b5563;
  margin-bottom: 0.75rem;
}

.insights-list {
  list-style-type: disc;
  padding-left: 1.5rem;
}

.insights-list li {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
}
</style>