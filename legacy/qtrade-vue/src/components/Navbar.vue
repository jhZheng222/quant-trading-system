<script setup>
// 引入必要的组件
import { ref } from 'vue'
import { ElButton, ElMenu, ElMenuItem, ElIcon } from 'element-plus'
import { User, Menu as MenuIcon, Close } from '@element-plus/icons-vue'

// 响应式状态
const isMobileMenuOpen = ref(false)
const isUserMenuOpen = ref(false)

// 切换移动端菜单
const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

// 切换用户菜单
const toggleUserMenu = () => {
  isUserMenuOpen.value = !isUserMenuOpen.value
}

// 打开登录模态框
const emit = defineEmits(['open-login', 'open-register'])

const handleLogin = () => {
  emit('open-login')
  isUserMenuOpen.value = false
}

const handleRegister = () => {
  emit('open-register')
  isUserMenuOpen.value = false
}
</script>

<template>
  <header class="navbar">
    <div class="container">
      <div class="navbar-header">
        <a href="#" class="logo">
          <span class="text-primary">Q</span>Trade
        </a>

        <!-- 移动端菜单按钮 -->
        <button class="mobile-menu-btn" @click="toggleMobileMenu">
          <ElIcon v-if="!isMobileMenuOpen"><MenuIcon /></ElIcon>
          <ElIcon v-else><Close /></ElIcon>
        </button>
      </div>

      <!-- 桌面端导航菜单 -->
      <nav class="desktop-nav">
        <ElMenu mode="horizontal" class="nav-menu">
          <ElMenuItem index="1">首页</ElMenuItem>
          <ElMenuItem index="2">市场</ElMenuItem>
          <ElMenuItem index="3">交易</ElMenuItem>
          <ElMenuItem index="4">策略</ElMenuItem>
          <ElMenuItem index="5">资讯</ElMenuItem>
        </ElMenu>
      </nav>

      <!-- 登录/注册按钮 -->
      <div class="auth-buttons">
        <ElButton type="text" @click="handleLogin">登录</ElButton>
        <ElButton type="primary" @click="handleRegister">免费注册</ElButton>
      </div>
    </div>

    <!-- 移动端导航菜单 -->
    <div class="mobile-nav" v-if="isMobileMenuOpen">
      <ElMenu class="mobile-menu">
        <ElMenuItem index="1">首页</ElMenuItem>
        <ElMenuItem index="2">市场</ElMenuItem>
        <ElMenuItem index="3">交易</ElMenuItem>
        <ElMenuItem index="4">策略</ElMenuItem>
        <ElMenuItem index="5">资讯</ElMenuItem>
        <ElMenuItem index="6" @click="handleLogin">登录</ElMenuItem>
        <ElMenuItem index="7" @click="handleRegister">免费注册</ElMenuItem>
      </ElMenu>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  background-color: #1f2937;
  color: white;
  padding: 1rem 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.container {
  width: 90%;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 1.5rem;
  font-weight: bold;
  color: white;
  text-decoration: none;
}

.text-primary {
  color: #3b82f6;
}

.desktop-nav {
  display: flex;
  align-items: center;
}

.nav-menu {
  background-color: transparent !important;
  border: none !important;
}

.nav-menu .el-menu-item {
  color: white;
}

.nav-menu .el-menu-item:hover {
  color: #3b82f6;
}

.auth-buttons {
  display: flex;
  gap: 10px;
}

.mobile-menu-btn {
  display: none;
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
}

.mobile-nav {
  background-color: #1f2937;
  padding: 1rem 0;
}

.mobile-menu {
  background-color: transparent !important;
  border: none !important;
}

.mobile-menu .el-menu-item {
  color: white;
}

.mobile-menu .el-menu-item:hover {
  color: #3b82f6;
}

@media (max-width: 768px) {
  .desktop-nav, .auth-buttons {
    display: none;
  }

  .mobile-menu-btn {
    display: block;
  }
}
</style>