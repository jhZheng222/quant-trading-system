<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

// 表单数据
const formData = ref({
  username: '',
  password: ''
})

// 加载状态
const loading = ref(false)

// 路由实例
const router = useRouter()

// 提交登录表单
const handleLogin = async () => {
  // 简单验证
  if (!formData.value.username || !formData.value.password) {
    ElMessage.error('请输入用户名和密码')
    return
  }

  loading.value = true

  try {
    // 这里应该调用登录API
    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 1000))

    // 假设登录成功，存储token
    localStorage.setItem('token', 'mock_token_' + Date.now())
    localStorage.setItem('userInfo', JSON.stringify({
      username: formData.value.username,
      role: 'user' // 默认为普通用户
    }))

    ElMessage.success('登录成功')
    router.push('/home')
  } catch (error) {
    ElMessage.error('登录失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page min-h-screen bg-gradient-to-br from-primary/5 to-primary/10 flex items-center justify-center p-4">
    <div class="login-container w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden transform transition-all duration-300 hover:shadow-2xl">
      <!-- 顶部装饰 -->
      <div class="bg-primary h-2"></div>

      <!-- 登录表单 -->
      <div class="p-8">
        <div class="text-center mb-8">
          <h1 class="text-3xl font-bold text-dark mb-2">QTradeAnalysis</h1>
          <p class="text-gray-500">个人虚拟币量化交易平台</p>
        </div>

        <form @submit.prevent="handleLogin">
          <div class="mb-6">
            <label for="username" class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                <i class="fa fa-user text-gray-400"></i>
              </div>
              <input
                type="text"
                id="username"
                v-model="formData.username"
                class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
                placeholder="请输入用户名"
              >
            </div>
          </div>

          <div class="mb-6">
            <label for="password" class="block text-sm font-medium text-gray-700 mb-1">密码</label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                <i class="fa fa-lock text-gray-400"></i>
              </div>
              <input
                type="password"
                id="password"
                v-model="formData.password"
                class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
                placeholder="请输入密码"
              >
            </div>
          </div>

          <div class="flex items-center justify-between mb-6">
            <div class="flex items-center">
              <input
                id="remember-me" 
                type="checkbox"
                class="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
              >
              <label for="remember-me" class="ml-2 block text-sm text-gray-700">
                记住我
              </label>
            </div>
            <a href="#" class="text-sm font-medium text-primary hover:text-primary/80 transition-colors duration-200">
              忘记密码?
            </a>
          </div>

          <button
            type="submit"
            :loading="loading"
            class="w-full bg-primary hover:bg-primary/90 text-white font-medium py-2 px-4 rounded-lg transition-all duration-200 flex items-center justify-center"
          >
            <i class="fa fa-sign-in mr-2"></i> 登录
          </button>
        </form>

        <div class="mt-6 text-center">
          <p class="text-sm text-gray-600">
            还没有账号? <a href="/register" class="font-medium text-primary hover:text-primary/80 transition-colors duration-200">立即注册</a>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  font-family: 'Inter', sans-serif;
}
</style>