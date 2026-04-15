import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import Components from 'unplugin-vue-components/vite'

export default defineConfig({
  plugins: [vue(),
  Components({
    dirs: ['src/ui'],
    deep: true,
    dts: true,
  })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
  },
})


