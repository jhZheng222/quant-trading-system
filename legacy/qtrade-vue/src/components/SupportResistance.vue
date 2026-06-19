<script setup>
// 引入必要的组件
import { ref } from 'vue'
import { ElCard, ElRow, ElCol, ElTable, ElTableColumn } from 'element-plus'

// 支撑位和压力位数据
const levelsData = ref([
  {
    type: 'resistance',
    level: 43500,
    strength: 'strong',
    probability: 85,
    description: '主要压力位，多次测试未能突破'
  },
  {
    type: 'resistance',
    level: 43000,
    strength: 'medium',
    probability: 70,
    description: '次要压力位'
  },
  {
    type: 'current',
    level: 42567.89,
    strength: 'current',
    probability: 100,
    description: '当前价格'
  },
  {
    type: 'support',
    level: 42000,
    strength: 'strong',
    probability: 90,
    description: '主要支撑位，多次测试未能跌破'
  },
  {
    type: 'support',
    level: 41500,
    strength: 'medium',
    probability: 75,
    description: '次要支撑位'
  }
])

// 获取级别类型对应的样式类
const getLevelClass = (type) => {
  switch (type) {
    case 'resistance':
      return 'level-resistance'
    case 'support':
      return 'level-support'
    case 'current':
      return 'level-current'
    default:
      return ''
  }
}

// 获取强度对应的样式类
const getStrengthClass = (strength) => {
  switch (strength) {
    case 'strong':
      return 'strength-strong'
    case 'medium':
      return 'strength-medium'
    case 'weak':
      return 'strength-weak'
    case 'current':
      return 'strength-current'
    default:
      return ''
  }
}

// 获取强度文本
const getStrengthText = (strength) => {
  switch (strength) {
    case 'strong':
      return '强'
    case 'medium':
      return '中'
    case 'weak':
      return '弱'
    case 'current':
      return '当前'
    default:
      return '未知'
  }
}
</script>

<template>
  <section class="support-resistance">
    <ElCard class="levels-card">
      <h2 class="section-title">支撑位和压力位</h2>

      <div class="levels-chart">
        <div class="chart-axis">
          <div v-for="item in levelsData" :key="item.level" class="level-line" :style="{ top: `${100 - ((item.level - 41000) / 2500 * 100)}%` }"></div>
        </div>
        <div class="chart-levels">
          <div v-for="item in levelsData" :key="item.level" :class="'level-item ' + getLevelClass(item.type)" :style="{ top: `${100 - ((item.level - 41000) / 2500 * 100)}%` }"></div>
        </div>
      </div>

      <div class="levels-table">
        <ElTable :data="levelsData" stripe style="width: 100%">
          <ElTableColumn prop="type" label="类型" width="100">
            <template #default="scope">
              <span :class="getLevelClass(scope.row.type) + ' type-badge'">
                {{ scope.row.type === 'resistance' ? '压力位' : scope.row.type === 'support' ? '支撑位' : '当前价格' }}
              </span>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="level" label="价格" width="120">
            <template #default="scope">
              ${{ scope.row.level.toFixed(2) }}
            </template>
          </ElTableColumn>
          <ElTableColumn prop="strength" label="强度" width="100">
            <template #default="scope">
              <span :class="getStrengthClass(scope.row.strength) + ' strength-badge'">
                {{ getStrengthText(scope.row.strength) }}
              </span>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="probability" label="有效性" width="100">
            <template #default="scope">
              {{ scope.row.probability }}%
            </template>
          </ElTableColumn>
          <ElTableColumn prop="description" label="描述">
            <template #default="scope">
              {{ scope.row.description }}
            </template>
          </ElTableColumn>
        </ElTable>
      </div>
    </ElCard>
  </section>
</template>

<style scoped>
.support-resistance {
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}

.levels-card {
  border: none !important;
  box-shadow: none !important;
}

.section-title {
  font-size: 1.25rem;
  font-weight: bold;
  color: #111827;
  margin-bottom: 1.5rem;
}

.levels-chart {
  position: relative;
  height: 200px;
  background-color: #f9fafb;
  border-radius: 0.5rem;
  margin-bottom: 1.5rem;
  overflow: hidden;
}

.chart-axis {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  padding: 20px 0;
  box-sizing: border-box;
}

.level-line {
  position: absolute;
  left: 0;
  width: 100%;
  height: 1px;
  background-color: #e5e7eb;
  transform: translateY(-50%);
}

.chart-levels {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  padding: 20px 0;
  box-sizing: border-box;
}

.level-item {
  position: absolute;
  left: 0;
  width: 100%;
  height: 20px;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  padding: 0 15px;
  box-sizing: border-box;
}

.level-resistance {
  background-color: rgba(239, 68, 68, 0.1);
  border-top: 2px solid #ef4444;
}

.level-support {
  background-color: rgba(16, 185, 129, 0.1);
  border-top: 2px solid #10b981;
}

.level-current {
  background-color: rgba(59, 130, 246, 0.1);
  border-top: 2px solid #3b82f6;
}

.levels-table {
  overflow-x: auto;
}

.type-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.level-resistance .type-badge {
  background-color: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.level-support .type-badge {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.level-current .type-badge {
  background-color: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.strength-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.strength-strong {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.strength-medium {
  background-color: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.strength-weak {
  background-color: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.strength-current {
  background-color: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}
</style>