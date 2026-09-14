import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from '@/router'
import App from './App.vue'
import { i18n } from "@/infra/i18n";
import { initTheme } from "@/infra/theme";
import '@/styles/index.css'
import { resetStoresOnSessionChange } from '@/infra/auth/sessionPinia'

initTheme();

const app = createApp(App)

const pinia = createPinia()
pinia.use(resetStoresOnSessionChange)
app.use(pinia)
app.use(router)
app.use(i18n)

app.mount('#app')
