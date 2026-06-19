<script setup>
// 引入必要的组件
import { ElIcon } from 'element-plus'
import { Message, Link } from '@element-plus/icons-vue'
</script>

<template>
  <footer class="footer">
    <div class="footer-container">
      <div class="footer-logo-section">
        <div class="logo">QTrade</div>
        <p class="logo-description">专业的虚拟币量化交易分析平台</p>
      </div>

      <div class="footer-links-section">
        <div class="footer-links-column">
          <h3 class="column-title">产品</h3>
          <ul class="links-list">
            <li><a href="#" class="footer-link">功能介绍</a></li>
            <li><a href="#" class="footer-link">定价方案</a></li>
            <li><a href="#" class="footer-link">更新日志</a></li>
            <li><a href="#" class="footer-link">API文档</a></li>
          </ul>
        </div>

        <div class="footer-links-column">
          <h3 class="column-title">资源</h3>
          <ul class="links-list">
            <li><a href="#" class="footer-link">帮助中心</a></li>
            <li><a href="#" class="footer-link">交易教程</a></li>
            <li><a href="#" class="footer-link">技术分析</a></li>
            <li><a href="#" class="footer-link">社区讨论</a></li>
          </ul>
        </div>

        <div class="footer-links-column">
          <h3 class="column-title">公司</h3>
          <ul class="links-list">
            <li><a href="#" class="footer-link">关于我们</a></li>
            <li><a href="#" class="footer-link">联系我们</a></li>
            <li><a href="#" class="footer-link">招聘信息</a></li>
            <li><a href="#" class="footer-link">隐私政策</a></li>
          </ul>
        </div>
      </div>

      <div class="footer-social-section">
        <h3 class="social-title">关注我们</h3>
        <div class="social-links">
          <!-- Removed Github icon as it's not available in Element Plus Icons -->
          <!-- Removed Twitter icon as it's not available in Element Plus Icons -->
          <!-- Removed Linkedin icon as it's not available in Element Plus Icons -->
          <a href="#" class="social-link"><ElIcon><Message /></ElIcon></a>
        </div>
      </div>
    </div>

    <div class="footer-bottom">
      <div class="footer-bottom-container">
        <p class="copyright">© 2023 QTrade. 保留所有权利。</p>
        <div class="footer-bottom-links">
          <a href="#" class="bottom-link">服务条款</a>
          <a href="#" class="bottom-link">隐私政策</a>
          <a href="#" class="bottom-link">Cookie政策</a>
        </div>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  background-color: #111827;
  color: white;
  padding-top: 3rem;
  padding-bottom: 1.5rem;
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  gap: 2rem;
}

.footer-logo-section {
  display: flex;
  flex-direction: column;
}

.logo {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
  color: white;
}

.logo-description {
  font-size: 0.875rem;
  color: #9ca3af;
  margin-bottom: 1.5rem;
}

.footer-links-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
}

.footer-links-column {
  display: flex;
  flex-direction: column;
}

.column-title {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: white;
}

.links-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.footer-link {
  display: block;
  color: #9ca3af;
  text-decoration: none;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  transition: color 0.2s;
}

.footer-link:hover {
  color: white;
}

.footer-social-section {
  display: flex;
  flex-direction: column;
}

.social-title {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: white;
}

.social-links {
  display: flex;
  gap: 1rem;
}

.social-link {
  color: #9ca3af;
  font-size: 1.25rem;
  transition: color 0.2s;
}

.social-link:hover {
  color: white;
}

.footer-bottom {
  border-top: 1px solid #374151;
  margin-top: 3rem;
}

.footer-bottom-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.copyright {
  font-size: 0.75rem;
  color: #9ca3af;
}

.footer-bottom-links {
  display: flex;
  gap: 1.5rem;
}

.bottom-link {
  font-size: 0.75rem;
  color: #9ca3af;
  text-decoration: none;
  transition: color 0.2s;
}

.bottom-link:hover {
  color: white;
}
</style>