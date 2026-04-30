import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from '@/router'
import App from './App.vue'
import { i18n } from "@/infra/i18n";
import { initTheme } from "@/infra/theme";
import '@/styles/index.css'

initTheme();

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)

app.mount('#app')
