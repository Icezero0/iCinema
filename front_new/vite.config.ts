import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import Components from 'unplugin-vue-components/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiOrigin = env.VITE_API_ORIGIN ?? 'http://localhost:8000'

  return {
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
      proxy: {
        '/avatar': {
          target: apiOrigin,
          changeOrigin: true,
        },
        '/image': {
          target: apiOrigin,
          changeOrigin: true,
        },
        '/sticker': {
          target: apiOrigin,
          changeOrigin: true,
        },
      },
    },
  }
})


