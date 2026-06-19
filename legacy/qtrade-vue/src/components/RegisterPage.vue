
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

// 表单数据
const formData = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

// 加载状态
const loading = ref(false)

// 路由实例
const router = useRouter()

// 提交注册表单
const handleRegister = async () => {
  // 简单验证
  if (!formData.value.username || !formData.value.email || !formData.value.password || !formData.value.confirmPassword) {
    ElMessage.error('请填写所有必填字段')
    return
  }

  if (formData.value.password !== formData.value.confirmPassword) {
    ElMessage.error('两次输入的密码不一致')
    return
  }

  if (formData.value.password.length < 6) {
    ElMessage.error('密码长度不能少于6位')
    return
  }

  // 简单的邮箱格式验证
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(formData.value.email)) {
    ElMessage.error('请输入有效的邮箱地址')
    return
  }

  loading.value = true

  try {
    // 这里应该调用注册API
    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 1000))

    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (error) {
    ElMessage.error('注册失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page min-h-screen bg-gradient-to-br from-primary/5 to-primary/10 flex items-center justify-center p-4">
    <div class="register-container w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden transform transition-all duration-300 hover:shadow-2xl">
      <!-- 顶部装饰 -->
      <div class="bg-primary h-2"></div>

      <!-- 注册表单 -->
      <div class="p-8">
        <div class="text-center mb-8">
          <h1 class="text-3xl font-bold text-dark mb-2">QTradeAnalysis</h1>
          <p class="text-gray-500">个人虚拟币量化交易平台</p>
        </div>

        <form @submit.prevent="handleRegister">
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
            <label for="email" class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                <i class="fa fa-envelope text-gray-400"></i>
              </div>
              <input
                type="email"
                id="email"
                v-model="formData.email"
                class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
                placeholder="请输入邮箱"
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

          <div class="mb-6">
            <label for="confirmPassword" class="block text-sm font-medium text-gray-700 mb-1">确认密码</label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                <i class="fa fa-lock text-gray-400"></i>
              </div>
              <input
                type="password"
                id="confirmPassword"
                v-model="formData.confirmPassword"
                class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
                placeholder="请再次输入密码"
              >
            </div>
          </div>

          <div class="flex items-center mb-6">
            <input
              id="terms" 
              type="checkbox"
              class="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
            >
            <label for="terms" class="ml-2 block text-sm text-gray-700">
              我同意<a href="#" class="text-primary hover:text-primary/80 transition-colors duration-200">服务条款</a>和<a href="#" class="text-primary hover:text-primary/80 transition-colors duration-200">隐私政策</a>
            </label>
          </div>

          <button
            type="submit"
            :loading="loading"
            class="w-full bg-primary hover:bg-primary/90 text-white font-medium py-2 px-4 rounded-lg transition-all duration-200 flex items-center justify-center"
          >
            <i class="fa fa-user-plus mr-2"></i> 注册
          </button>
        </form>

        <div class="mt-6 text-center">
          <p class="text-sm text-gray-600">
            已有账号? <a href="/login" class="font-medium text-primary hover:text-primary/80 transition-colors duration-200">立即登录</a>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register-page {
  font-family: 'Inter', sans-serif;
}
</style>