<script setup>
// 引入必要的组件
import { ref } from 'vue'
import { ElForm, ElFormItem, ElInput, ElButton, ElIcon, ElCheckbox } from 'element-plus'
import { User, Lock, Message, View } from '@element-plus/icons-vue'
import axios from 'axios'

// 定义props
const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  }
})

// 定义emits
const emit = defineEmits(['update:modelValue', 'register-success'])

// 表单数据
const form = ref({
  email: '',
  username: '',
  password: '',
  confirmPassword: '',
  agreeTerms: false
})

// 表单规则
const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名长度不能少于3位', trigger: 'blur' },
    { max: 20, message: '用户名长度不能超过20位', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' },
    { pattern: /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$/, message: '密码必须包含字母和数字', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: (rule, value, callback) => {
      if (value !== form.value.password) {
        callback(new Error('两次输入的密码不一致'))
      } else {
        callback()
      }
    }, trigger: 'blur' }
  ],
  agreeTerms: [
    { required: true, message: '请同意服务条款和隐私政策', trigger: 'change' }
  ]
}

// 控制密码可见性
const passwordVisible = ref(false)
const confirmPasswordVisible = ref(false)

// 关闭模态框
const closeModal = () => {
  emit('update:modelValue', false)
}

// 提交注册表单
const submitForm = async (formEl) => {
  if (!formEl) return
  await formEl.validate()

  try {
    // 这里是模拟注册请求
    // 实际应用中，应该替换为真实的API请求
    // const response = await axios.post('/api/register', form.value)
    // if (response.data.success) {
    //   emit('register-success', response.data)
    //   closeModal()
    // }

    // 模拟成功注册
    setTimeout(() => {
      emit('register-success', { email: form.value.email })
      closeModal()
    }, 1000)
  } catch (error) {
    console.error('注册失败:', error)
  }
}
</script>

<template>
  <ElModal
    :model-value="modelValue"
    @update:model-value="(value) => emit('update:modelValue', value)"
    title="创建账户"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    @close="closeModal"
    class="register-modal"
  >
    <ElForm ref="registerForm" :model="form" :rules="rules" label-width="0px">
      <ElFormItem prop="email">
        <ElInput
          v-model="form.email"
          placeholder="邮箱"
          prefix-icon="Message"
          class="register-input"
        />
      </ElFormItem>
      <ElFormItem prop="username">
        <ElInput
          v-model="form.username"
          placeholder="用户名"
          prefix-icon="User"
          class="register-input"
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
          class="register-input"
        />
      </ElFormItem>
      <ElFormItem prop="confirmPassword">
        <ElInput
          v-model="form.confirmPassword"
          type="password"
          placeholder="确认密码"
          prefix-icon="Lock"
          :suffix-icon="confirmPasswordVisible ? 'View' : 'View'"
          @click-suffix="confirmPasswordVisible = !confirmPasswordVisible"
          :show-password="confirmPasswordVisible"
          class="register-input"
        />
      </ElFormItem>
      <ElFormItem prop="agreeTerms">
        <ElCheckbox v-model="form.agreeTerms" class="agree-terms">
          我同意 <a href="#" class="link">服务条款</a> 和 <a href="#" class="link">隐私政策</a>
        </ElCheckbox>
      </ElFormItem>
      <ElButton
        type="primary"
        class="register-button"
        @click="submitForm(registerForm.ref)"
      >
        注册
      </ElButton>
    </ElForm>

    <div class="login-link">
      已有账户? <a href="#" @click.stop="emit('update:modelValue', false); $emit('open-login')">立即登录</a>
    </div>
  </ElModal>
</template>

<style scoped>
.register-modal .el-modal__body {
  padding: 2rem 2rem 1.5rem;
}

.register-input .el-input__inner {
  height: 50px;
  border-radius: 8px;
}

.agree-terms .el-checkbox__label {
  color: #6b7280;
  font-size: 0.875rem;
}

.link {
  color: #3b82f6;
  text-decoration: none;
}

.register-button {
  width: 100%;
  height: 50px;
  border-radius: 8px;
  font-size: 1rem;
  margin-bottom: 1.5rem;
}

.register-divider {
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
}

.register-divider::before, .register-divider::after {
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

.social-register {
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

.login-link {
  text-align: center;
  font-size: 0.875rem;
  color: #6b7280;
}

.login-link a {
  color: #3b82f6;
  text-decoration: none;
}
</style>