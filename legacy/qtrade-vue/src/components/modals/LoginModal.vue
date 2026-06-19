<script setup>
// 引入必要的组件
import { ref } from 'vue'
import { ElForm, ElFormItem, ElInput, ElButton, ElIcon, ElCheckbox } from 'element-plus'
import { User, Lock, View } from '@element-plus/icons-vue'
import axios from 'axios'

// 定义props
const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  }
})

// 定义emits
const emit = defineEmits(['update:modelValue', 'login-success'])

// 表单数据
const form = ref({
  email: '',
  password: '',
  rememberMe: false
})

// 表单规则
const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

// 控制密码可见性
const passwordVisible = ref(false)

// 关闭模态框
const closeModal = () => {
  emit('update:modelValue', false)
}

// 提交登录表单
const submitForm = async (formEl) => {
  if (!formEl) return
  await formEl.validate()

  try {
    // 这里是模拟登录请求
    // 实际应用中，应该替换为真实的API请求
    // const response = await axios.post('/api/login', form.value)
    // if (response.data.success) {
    //   emit('login-success', response.data)
    //   closeModal()
    // }

    // 模拟成功登录
    setTimeout(() => {
      emit('login-success', { token: 'mock-token', user: { email: form.value.email } })
      closeModal()
    }, 1000)
  } catch (error) {
    console.error('登录失败:', error)
  }
}
</script>

<template>
  <ElModal
    :model-value="modelValue"
    @update:model-value="(value) => emit('update:modelValue', value)"
    title="登录账户"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    @close="closeModal"
    class="login-modal"
  >
    <ElForm ref="loginForm" :model="form" :rules="rules" label-width="0px">
      <ElFormItem prop="email">
        <ElInput
          v-model="form.email"
          placeholder="邮箱"
          prefix-icon="User"
          class="login-input"
        />
      </ElFormItem>
      <ElFormItem prop="password">
        <ElInput
          v-model="form.password"
          type="password"
          placeholder="密码"
          prefix-icon="Lock"
          :suffix-icon="passwordVisible ? 'View' : 'View'"
          @click-suffix="passwordVisible = !passwordVisible"
          :show-password="passwordVisible"
          class="login-input"
        />
      </ElFormItem>
      <div class="login-options">
        <ElCheckbox v-model="form.rememberMe" class="remember-me">记住我</ElCheckbox>
        <a href="#" class="forgot-password">忘记密码?</a>
      </div>
      <ElButton
        type="primary"
        class="login-button"
        @click="submitForm(loginForm.ref)"
      >
        登录
      </ElButton>
    </ElForm>



    <div class="register-link">
      还没有账户? <a href="#" @click.stop="emit('update:modelValue', false); emit('open-register')">立即注册</a>
    </div>
  </ElModal>
</template>

<style scoped>
.login-modal .el-modal__body {
  padding: 2rem 2rem 1.5rem;
}

.login-input .el-input__inner {
  height: 50px;
  border-radius: 8px;
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.remember-me .el-checkbox__label {
  color: #6b7280;
}

.forgot-password {
  color: #3b82f6;
  text-decoration: none;
}

.login-button {
  width: 100%;
  height: 50px;
  border-radius: 8px;
  font-size: 1rem;
  margin-bottom: 1.5rem;
}

.login-divider {
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
}

.login-divider::before, .login-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background-color: #e5e7eb;
}

.divider-text {
  padding: 0 1rem;
  color: #9ca3af;
  font-size: 0.875rem;
}

.social-login {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.social-button {
  flex: 1;
  height: 50px;
  border-radius: 8px;
  font-size: 0.875rem;
}

.register-link {
  text-align: center;
  font-size: 0.875rem;
  color: #6b7280;
}

.register-link a {
  color: #3b82f6;
  text-decoration: none;
}
</style>