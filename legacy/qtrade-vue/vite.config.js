import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueJsx(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api/v3': {
        target: 'https://api.binance.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v3/, '/api/v3')
      }
    }
  },
  // 移除将.js文件视为jsx的配置
  // 仅对.jsx和.tsx文件使用jsx loader
  esbuild: {},
  // 添加.cjs文件到assetsInclude
  assetsInclude: ['**/*.cjs']
})
