// Auth endpoints handle their own failures. Refreshing them can recurse into
// logout; an invalid login must remain on the login form.
const authEndpoints = new Set([
  '/auth/login/', '/auth/sms-login/', '/auth/test-register/',
  '/auth/token/refresh/', '/auth/logout/', '/auth/exchange-token/',
])

export function installAuthInterceptors(api, getUserStore, notifyError) {
  api.interceptors.request.use(async (config) => {
    if (authEndpoints.has(config.url)) return config
    const user = getUserStore()
    if (user.accessToken) {
      if (user.refreshToken && user.isTokenExpiringSoon()) {
        await user.refreshAccessToken()
      }
      config.headers.Authorization = `Bearer ${user.accessToken}`
    }
    return config
  })

  api.interceptors.response.use(response => response, async (error) => {
    const request = error.config
    if (!request || authEndpoints.has(request.url)) throw error
    const user = getUserStore()

    if (error.response?.status === 401) {
      if (!request._retry && user.refreshToken) {
        request._retry = true
        // A delayed 401 can arrive after another request has already refreshed.
        // Reuse that token rather than rotating it again.
        if (request.headers.Authorization === `Bearer ${user.accessToken}`) {
          await user.refreshAccessToken()
        }
        request.headers.Authorization = `Bearer ${user.accessToken}`
        return api(request)
      }
      await user.logout({ revoke: false })
    } else if (error.response?.status >= 500) {
      notifyError('服务器错误，请稍后重试')
    }
    throw error
  })
}
