// 导入Vue
import { createApp } from 'vue';
import Chart from 'chart.js/auto';
import { CandlestickController, CandlestickElement } from 'chartjs-chart-financial';

Chart.register(CandlestickController, CandlestickElement);
import App from './App.vue'
import './style.css'

// 导入Element Plus和样式
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// 导入Chart.js和相关插件
import 'chartjs-chart-financial'
// 导入date-fns适配器和语言环境
import 'chartjs-adapter-date-fns'
import { enUS } from 'date-fns/locale'

// 配置Chart.js使用date-fns适配器
// 确保Chart.defaults和Chart.defaults.adapters存在
Chart.defaults = Chart.defaults || {}
Chart.defaults.adapters = Chart.defaults.adapters || {}
Chart.defaults.adapters.date = { locale: enUS }

// 引入axios
import axios from 'axios'

// 引入路由配置
import router from './router'

// 引入Binance WebSocket服务
import binanceService from './services/binanceWebSocket.js'
console.log('Binance WebSocket服务已导入')

// 创建Vue应用
const app = createApp(App)
console.log('Vue应用已创建')

// 注册Element Plus
app.use(ElementPlus)
console.log('Element Plus已注册')

// 注册Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}
console.log('Element Plus图标已注册')

// 配置路由
app.use(router)
console.log('路由已配置')

// 配置axios全局使用
app.config.globalProperties.$axios = axios
console.log('axios已配置')

// 配置Binance WebSocket服务全局使用
app.config.globalProperties.$binanceService = binanceService
console.log('Binance WebSocket服务已配置为全局属性')

// 挂载应用
console.log('准备挂载应用...')
app.mount('#app')
console.log('应用已成功挂载')
