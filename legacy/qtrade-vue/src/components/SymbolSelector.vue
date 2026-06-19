<template>
  <div class="symbol-selector-container">
    <div class="selector-group">
      <label for="symbol-select">交易对:</label>
      <select id="symbol-select" v-model="selectedSymbol" @change="onSymbolChange">
        <option v-for="symbol in symbols" :key="symbol" :value="symbol">
          {{ symbol.toUpperCase() }}
        </option>
      </select>
    </div>

    <div class="selector-group">
      <label for="interval-select">时间间隔:</label>
      <select id="interval-select" v-model="selectedInterval" @change="onIntervalChange">
        <option v-for="interval in intervals" :key="interval" :value="interval">
          {{ interval }}
        </option>
      </select>
    </div>
  </div>
</template>

<script>
import { ref, watch, defineProps, defineEmits } from 'vue'

export default {
  name: 'SymbolSelector',
  props: {
    modelValueSymbol: {
      type: String,
      required: true
    },
    modelValueInterval: {
      type: String,
      required: true
    }
  },
  emits: ['update:modelValueSymbol', 'update:modelValueInterval'],
  setup(props, { emit }) {
    const selectedSymbol = ref(props.modelValueSymbol)
    const selectedInterval = ref(props.modelValueInterval)

    // 监听props变化，同步到本地状态
    watch(() => props.modelValueSymbol,
      (newSymbol) => {
        selectedSymbol.value = newSymbol
      }
    )

    watch(() => props.modelValueInterval,
      (newInterval) => {
        selectedInterval.value = newInterval
      }
    )

    // 交易对列表
    const symbols = [
      'btcusdt',
      'ethusdt',
      'bnbusdt',
      'solusdt',
      'avaxusdt',
      'dogeusdt',
      'adausdt',
      'linkusdt'
    ]

    // 时间间隔列表
    const intervals = [
      '1m',
      '3m',
      '5m',
      '15m',
      '30m',
      '1h',
      '2h',
      '4h',
      '6h',
      '8h',
      '12h',
      '1d',
      '3d',
      '1w',
      '1M'
    ]

    // 处理交易对变化
    const onSymbolChange = () => {
      emit('update:modelValueSymbol', selectedSymbol.value)
    }

    // 处理时间间隔变化
    const onIntervalChange = () => {
      emit('update:modelValueInterval', selectedInterval.value)
    }

    return {
      selectedSymbol,
      selectedInterval,
      symbols,
      intervals,
      onSymbolChange,
      onIntervalChange
    }
  }
}
</script>

<style scoped>
.symbol-selector-container {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.selector-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

label {
  font-weight: 500;
  color: #555;
}

select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
  font-size: 14px;
  transition: border-color 0.2s;
}

select:focus {
  outline: none;
  border-color: #42b983;
}
</style>