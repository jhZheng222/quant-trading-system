<script setup>
// 引入必要的组件
import { ElButton } from 'element-plus'

// 定义事件发射
const emit = defineEmits(['open-register'])

// 处理注册按钮点击
const handleRegister = () => {
  emit('open-register')
}
</script>

<template>
  <section class="hero-section">
    <div class="container">
      <div class="hero-content">
        <h1 class="hero-title">
          智能<span class="text-primary">量化交易</span>分析平台
        </h1>
        <p class="hero-subtitle">
          利用先进算法和AI技术，为您提供精准的虚拟币交易信号和策略分析
        </p>
        <div class="hero-cta">
          <ElButton type="primary" size="large" @click="handleRegister">
            免费开始使用
          </ElButton>
          <ElButton type="text" size="large" class="learn-more-btn">
            了解更多
          </ElButton>
        </div>
        <div class="hero-features">
          <div class="feature-item">
            <div class="feature-icon">📊</div>
            <div class="feature-text">实时市场数据分析</div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🤖</div>
            <div class="feature-text">AI驱动的交易信号</div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🔒</div>
            <div class="feature-text">安全可靠的交易环境</div>
          </div>
        </div>
      </div>
      <div class="hero-image">
        <div class="chart-container">
          <!-- 这里将放置图表组件 -->
          <div class="chart-placeholder"></div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero-section {
  background-color: #f9fafb;
  padding: 4rem 0;
}

.container {
  width: 90%;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
}

.hero-content {
  flex: 1;
  min-width: 300px;
  padding-right: 2rem;
}

.hero-title {
  font-size: 2.5rem;
  font-weight: bold;
  margin-bottom: 1rem;
  color: #111827;
}

.text-primary {
  color: #3b82f6;
}

.hero-subtitle {
  font-size: 1.125rem;
  color: #6b7280;
  margin-bottom: 2rem;
  max-width: 400px;
}

.hero-cta {
  display: flex;
  gap: 1rem;
  margin-bottom: 3rem;
}

.learn-more-btn {
  color: #3b82f6 !important;
}

.hero-features {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.feature-icon {
  font-size: 1.25rem;
}

.feature-text {
  font-size: 0.875rem;
  color: #6b7280;
}

.hero-image {
  flex: 1;
  min-width: 300px;
  margin-top: 2rem;
}

.chart-container {
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  padding: 1.5rem;
  height: 300px;
}

.chart-placeholder {
  width: 100%;
  height: 100%;
  background-color: #f3f4f6;
  border-radius: 0.375rem;
}

@media (min-width: 768px) {
  .hero-image {
    margin-top: 0;
  }
}
</style>