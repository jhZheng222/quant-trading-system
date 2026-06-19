<script setup>
// 引入必要的组件
import { ref, onMounted } from 'vue'
import { ElTable, ElTableColumn, ElButton, ElIcon } from 'element-plus'
import { TrendCharts, Refresh } from '@element-plus/icons-vue'

// 模拟交易数据
const generateTradesData = () => {
  const data = []
  const now = new Date()
  const types = ['buy', 'sell']
  
  for (let i = 0; i < 20; i++) {
    const type = types[Math.floor(Math.random() * types.length)]
    const price = 42000 + Math.random() * 1000
    const quantity = 0.001 + Math.random() * 0.1
    const time = new Date(now - i * 60 * 1000)
    
    data.push({
      id: 'TX' + Math.floor(Math.random() * 1000000),
      price: price,
      quantity: quantity,
      amount: price * quantity,
      type: type,
      time: time
    })
  }
  return data
}

// 交易数据
const tradesData = ref(generateTradesData())

// 刷新交易数据
const refreshData = () => {
  tradesData.value = generateTradesData()
}

// 组件挂载时执行
onMounted(() => {
  // 模拟数据更新
  setInterval(refreshData, 15000)
})
</script>

<template>
  <section class="recent-trades">
    <div class="section-header">
      <h2 class="section-title">最近交易</h2>
      <div class="section-actions">
        <ElButton type="text" @click="refreshData">
          <ElIcon><Refresh /></ElIcon>
          刷新
        </ElButton>
      </div>
    </div>

    <div class="trades-table">
      <ElTable :data="tradesData" stripe style="width: 100%">
        <ElTableColumn prop="time" label="时间" width="160">
          <template #default="scope">
            {{ new Date(scope.row.time).toLocaleTimeString() }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="price" label="价格" width="120">
          <template #default="scope">
            ${{ scope.row.price.toFixed(2) }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="quantity" label="数量" width="120">
          <template #default="scope">
            {{ scope.row.quantity.toFixed(6) }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="amount" label="金额" width="150">
          <template #default="scope">
            ${{ scope.row.amount.toFixed(2) }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="type" label="类型" width="100">
          <template #default="scope">
            <span :class="scope.row.type === 'buy' ? 'text-green' : 'text-red'">
              <ElIcon v-if="scope.row.type === 'buy'" class="mr-1"><TrendCharts /></ElIcon>
              <ElIcon v-else class="mr-1"><TrendCharts /></ElIcon>
              {{ scope.row.type === 'buy' ? '买入' : '卖出' }}
            </span>
          </template>
        </ElTableColumn>
      </ElTable>
    </div>
  </section>
</template>

<style scoped>
.recent-trades {
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: bold;
  color: #111827;
}

.trades-table {
  overflow-x: auto;
}

.text-green {
  color: #10b981;
}

.text-red {
  color: #ef4444;
}

.mr-1 {
  margin-right: 4px;
}
</style>