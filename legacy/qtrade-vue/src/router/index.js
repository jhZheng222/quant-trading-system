import { createRouter, createWebHashHistory } from 'vue-router'
import LoginPage from '../components/LoginPage.vue'
import RegisterPage from '../components/RegisterPage.vue'
import HomePage from '../components/HomePage.vue'
import TradeAnalysis from '../view/TradeAnalysis.vue'

// 路由配置
const routes = [
  { path: '/TradeAnalysis', name: 'TradeAnalysis', component: TradeAnalysis },
  {
    path: '/login',
    name: 'Login',
    component: LoginPage,
    meta: {
      requiresAuth: false
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: RegisterPage,
    meta: {
      requiresAuth: false
    }
  },
  {
    path: '/home',
    name: 'Home',
    component: HomePage,
    meta: {
      requiresAuth: true
    }
  },
  { path: '/ta', name: 'TradeAnalysisTA', component: TradeAnalysis, meta: { requiresAuth: false } },
  // 重定向到登录页面
  {
    path: '/',
    redirect: '/home'
  },
  // 404页面
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login'
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 检查是否需要认证
  if (to.meta.requiresAuth) {
    // 检查是否已登录
    const token = localStorage.getItem('token')
    if (token) {
      next()
    } else {
      next('/login')
    }
  } else {
    // 不需要认证的页面
    next()
  }
})

export default router