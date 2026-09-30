import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { installAuthInterceptors } from './authInterceptors.js'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

installAuthInterceptors(api, () => useUserStore(), (message) => ElMessage.error(message))

export default api
