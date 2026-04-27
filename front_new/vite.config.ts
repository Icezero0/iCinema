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
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('qface.index.json')) {
              return 'chat-qface-data'
            }

            if (!id.includes('node_modules')) {
              return undefined
            }

            if (id.includes('@tiptap') || id.includes('prosemirror')) {
              return 'vendor-editor'
            }

            if (id.includes('@heroicons')) {
              return 'vendor-icons'
            }

            if (
              id.includes('/vue') ||
              id.includes('\\vue') ||
              id.includes('pinia') ||
              id.includes('vue-router') ||
              id.includes('vue-i18n')
            ) {
              return 'vendor-vue'
            }

            return 'vendor'
          },
        },
      },
    },
  }
})


