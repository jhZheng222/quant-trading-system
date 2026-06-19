<script setup>
// 引入必要的组件
import { ref } from 'vue'
import { ElCard, ElButton } from 'element-plus'
import { User, Lock, Message } from '@element-plus/icons-vue'

// 定义emits
const emit = defineEmits(['open-login', 'open-register'])
</script>

<template>
  <section class="auth-section">
    <ElCard class="auth-card">
      <h2 class="section-title">开始您的量化交易之旅</h2>
      <p class="section-description">注册账户，获取更多高级功能和个性化分析</p>

      <div class="auth-actions">
        <ElButton
          type="primary"
          size="large"
          @click="emit('open-register')"
          class="auth-button"
        >
          立即注册
        </ElButton>
        <ElButton
          type="default"
          size="large"
          @click="emit('open-login')"
          class="auth-button"
        >
          登录账户
        </ElButton>
      </div>

      <div class="auth-benefits">
        <h3 class="benefits-title">注册后您可以：</h3>
        <ul class="benefits-list">
          <li class="benefit-item">保存您的交易偏好和技术指标设置</li>
          <li class="benefit-item">接收个性化的交易提醒和策略推荐</li>
          <li class="benefit-item">访问高级图表分析工具和历史数据</li>
          <li class="benefit-item">参与社区讨论和分享交易经验</li>
        </ul>
      </div>
    </ElCard>
  </section>
</template>

<style scoped>
.auth-section {
  padding: 3rem 1.5rem;
  background-color: #f9fafb;
  margin: 2rem 0;
  border-radius: 0.5rem;
}

.auth-card {
  border: none !important;
  box-shadow: none !important;
  text-align: center;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  margin-bottom: 0.75rem;
}

.section-description {
  font-size: 1rem;
  color: #6b7280;
  margin-bottom: 2rem;
}

.auth-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.auth-button {
  min-width: 120px;
}

.auth-benefits {
  max-width: 500px;
  margin: 0 auto;
  text-align: left;
}

.benefits-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 1rem;
}

.benefits-list {
  list-style-type: none;
  padding: 0;
}

.benefit-item {
  font-size: 0.875rem;
  color: #4b5563;
  margin-bottom: 0.75rem;
  padding-left: 1.5rem;
  position: relative;
}

.benefit-item:before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #10b981;
  font-weight: bold;
}
</style>