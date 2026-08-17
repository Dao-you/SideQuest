import { createApp } from 'vue'
import '@varlet/ui/es/style'
import App from './App.vue'
import './styles.css'
import { registerPwa } from './pwa'

registerPwa()
createApp(App).mount('#app')
