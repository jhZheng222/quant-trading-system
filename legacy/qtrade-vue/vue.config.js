const { defineConfig } = require('@vue/cli-service');
module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    proxy: {
      '/api/v3': {
        target: 'https://api.binance.com',
        changeOrigin: true,
        pathRewrite: {
          '^/api/v3': '/api/v3'
        }
      }
    }
  }
});