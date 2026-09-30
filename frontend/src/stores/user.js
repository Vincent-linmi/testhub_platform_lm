import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/utils/api'
import { track } from '@/utils/tracker'

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const tokenExpiresAt = ref(parseInt(localStorage.getItem('token_expires_at') || '0'))

  // token刷新定时器
  let refreshTimer = null

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)

  // Read the clock at the point of use; computed values would cache Date.now().
  const isTokenExpiringSoon = () => tokenExpiresAt.value > 0 && tokenExpiresAt.value - Date.now() < 5 * 60 * 1000
  const isTokenExpired = () => tokenExpiresAt.value > 0 && Date.now() >= tokenExpiresAt.value
  let sessionVersion = 0
  let refreshInFlight = null
  let initPromise = null

  // 启动自动刷新token定时器
  const startAutoRefresh = () => {
    // 清除现有定时器
    if (refreshTimer) {
      clearInterval(refreshTimer)
    }

    // 每2分钟检查一次token是否需要刷新
    refreshTimer = setInterval(async () => {
      if (refreshToken.value && isTokenExpiringSoon() && accessToken.value) {
        try {
          await refreshAccessToken()
        } catch (error) {
          console.error('自动刷新token失败:', error)
          // 临时网络失败保留会话，下个周期重试。
        }
      }
    }, 2 * 60 * 1000) // 2分钟检查一次
  }

  // 停止自动刷新定时器
  const stopAutoRefresh = () => {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  const login = async (credentials) => {
    const response = await api.post('/auth/login/', credentials)

    // 保存双token
    sessionVersion++
    accessToken.value = response.data.access
    refreshToken.value = response.data.refresh
    user.value = response.data.user

    // 计算过期时间（当前时间 + 30分钟）
    const expiresAt = Date.now() + 30 * 60 * 1000
    tokenExpiresAt.value = expiresAt

    // 持久化存储
    localStorage.setItem('access_token', accessToken.value)
    localStorage.setItem('refresh_token', refreshToken.value)
    localStorage.setItem('token_expires_at', expiresAt.toString())
    localStorage.setItem('user', JSON.stringify(user.value))

    // 启动自动刷新
    startAutoRefresh()

    track('login_success', {
      event_type: 'business',
      module: 'auth',
      page_path: '/login',
      success: true,
      metadata: {
        login_type: 'password'
      }
    })

    return response.data
  }

  const smsLogin = async (data) => {
    const response = await api.post('/auth/sms-login/', data)

    sessionVersion++
    accessToken.value = response.data.access
    refreshToken.value = response.data.refresh
    user.value = response.data.user

    const expiresAt = Date.now() + 30 * 60 * 1000
    tokenExpiresAt.value = expiresAt

    localStorage.setItem('access_token', accessToken.value)
    localStorage.setItem('refresh_token', refreshToken.value)
    localStorage.setItem('token_expires_at', expiresAt.toString())
    localStorage.setItem('user', JSON.stringify(user.value))

    startAutoRefresh()

    track('login_success', {
      event_type: 'business',
      module: 'auth',
      page_path: '/login',
      success: true,
      metadata: {
        login_type: 'sms'
      }
    })

    return response.data
  }

  const register = async (userData) => {
    const response = await api.post('/auth/test-register/', userData)

    // 注册成功自动登录
    sessionVersion++
    accessToken.value = response.data.access
    refreshToken.value = response.data.refresh
    user.value = response.data.user

    const expiresAt = Date.now() + 30 * 60 * 1000
    tokenExpiresAt.value = expiresAt

    localStorage.setItem('access_token', accessToken.value)
    localStorage.setItem('refresh_token', refreshToken.value)
    localStorage.setItem('token_expires_at', expiresAt.toString())
    localStorage.setItem('user', JSON.stringify(user.value))

    startAutoRefresh()

    track('register_success', {
      event_type: 'business',
      module: 'auth',
      page_path: '/register',
      success: true
    })

    return response.data
  }

  let isLoggingOut = false

  const logout = async ({ revoke = true } = {}) => {
    if (isLoggingOut) return
    isLoggingOut = true
    const token = accessToken.value
    const refresh = refreshToken.value
    const canRevoke = revoke && refresh && !isTokenExpired()
    sessionVersion++
    stopAutoRefresh()
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    tokenExpiresAt.value = 0
    for (const key of ['access_token', 'refresh_token', 'token_expires_at', 'user']) {
      localStorage.removeItem(key)
    }
    try {
      if (canRevoke) {
        await api.post('/auth/logout/', { refresh }, { headers: { Authorization: `Bearer ${token}` } })
      }
    } catch (error) {
      // Local logout succeeds even if the revocation endpoint is unavailable.
      console.error('Logout API调用失败:', error)
    } finally {
      window.location.href = '/login'
      isLoggingOut = false
    }
  }

  const refreshAccessToken = () => {
    if (refreshInFlight?.version === sessionVersion) return refreshInFlight.promise
    const version = sessionVersion
    const refresh = refreshToken.value
    const promise = (async () => {
      try {
        const response = await api.post('/auth/token/refresh/', { refresh })
        // A response from a previous login must never restore a logged-out session.
        if (sessionVersion !== version) throw new Error('Session changed during token refresh')
        accessToken.value = response.data.access
        tokenExpiresAt.value = Date.now() + 30 * 60 * 1000
        if (response.data.refresh) {
          refreshToken.value = response.data.refresh
          localStorage.setItem('refresh_token', refreshToken.value)
        }
        localStorage.setItem('access_token', accessToken.value)
        localStorage.setItem('token_expires_at', tokenExpiresAt.value.toString())
        return accessToken.value
      } catch (error) {
        // Transient network failures should not destroy a valid login.
        if (sessionVersion === version && [400, 401, 403].includes(error.response?.status)) {
          await logout({ revoke: false })
        }
        throw error
      } finally {
        if (refreshInFlight?.version === version) refreshInFlight = null
      }
    })()
    refreshInFlight = { version, promise }
    return promise
  }

  const fetchProfile = async () => {
    try {
      const response = await api.get('/auth/profile/')
      user.value = response.data
      localStorage.setItem('user', JSON.stringify(user.value))
      return response.data
    } catch (error) {
      if (error.response?.status === 401) {
        await logout()
      }
      throw error
    }
  }

  const initializeAuth = async () => {
    // 从 localStorage 恢复用户信息
    if (!user.value) {
      const savedUser = localStorage.getItem('user')
      if (savedUser) {
        try {
          user.value = JSON.parse(savedUser)
        } catch (e) {
          console.error('解析用户信息失败:', e)
        }
      }
    }

    if (accessToken.value) {
      // 检查 token 是否过期，过期则刷新
      if (isTokenExpired() && refreshToken.value) {
        try {
          await refreshAccessToken()
        } catch (error) {
          console.error('Token刷新失败:', error)
          return
        }
      }

      // 获取用户信息
      if (!user.value) {
        try {
          await fetchProfile()
        } catch (error) {
          console.error('获取用户信息失败:', error)
          await logout()
        }
      }

      if (accessToken.value) startAutoRefresh()
    }
  }

  const initAuth = () => {
    if (!initPromise) {
      initPromise = initializeAuth().finally(() => { initPromise = null })
    }
    return initPromise
  }

  return {
    user,
    accessToken,
    refreshToken,
    tokenExpiresAt,
    isAuthenticated,
    isTokenExpiringSoon,
    isTokenExpired,
    login,
    smsLogin,
    register,
    logout,
    refreshAccessToken,
    fetchProfile,
    initAuth,
    startAutoRefresh,
    stopAutoRefresh
  }
})
