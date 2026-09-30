import assert from 'node:assert/strict'
import { before, after, beforeEach, afterEach, test } from 'node:test'
import { createServer } from 'vite'
import { createPinia, setActivePinia } from 'pinia'
import { AxiosError } from 'axios'

let server, api, useUserStore, user
const savedStorage = globalThis.localStorage
const savedWindow = globalThis.window
const storage = new Map()
const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const ok = (config, data = {}) => ({ config, data, status: 200, statusText: 'OK', headers: {} })
const fail = (config, status) => new AxiosError('Request failed', 'ERR_BAD_REQUEST', config, null, { status, data: {}, config })

before(async () => {
  globalThis.localStorage = {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, String(value)),
    removeItem: key => storage.delete(key),
  }
  server = await createServer({
    configFile: false,
    resolve: { alias: { '@': new URL('../src', import.meta.url).pathname } },
    cacheDir: '/tmp/testhub-auth-tests-vite-cache',
    optimizeDeps: { noDiscovery: true, include: [] },
    server: { middlewareMode: true, hmr: false }, appType: 'custom', logLevel: 'error'
  })
  ;({ useUserStore } = await server.ssrLoadModule('/src/stores/user.js'))
  ;({ default: api } = await server.ssrLoadModule('/src/utils/api.js'))
  globalThis.window = { location: { href: '' } }
})
beforeEach(() => {
  storage.clear()
  setActivePinia(createPinia())
  user = useUserStore()
  user.accessToken = 'old'
  user.refreshToken = 'refresh'
  user.tokenExpiresAt = Date.now() + 30 * 60_000
  window.location.href = ''
})
afterEach(() => user.stopAutoRefresh())
after(async () => {
  await server?.close()
  if (savedStorage === undefined) delete globalThis.localStorage
  else globalThis.localStorage = savedStorage
  if (savedWindow === undefined) delete globalThis.window
  else globalThis.window = savedWindow
})

test('expiry checks use the current clock on every call', t => {
  let now = 1_000_000
  t.mock.method(Date, 'now', () => now)
  user.tokenExpiresAt = now + 30 * 60_000
  assert.equal(user.isTokenExpiringSoon(), false)
  now += 26 * 60_000
  assert.equal(user.isTokenExpiringSoon(), true)
  assert.equal(user.isTokenExpired(), false)
  now += 4 * 60_000
  assert.equal(user.isTokenExpired(), true)
})

test('concurrent 401s share refresh and both retry without logout', async () => {
  const gate = deferred()
  const started = deferred()
  let refreshes = 0
  let attempts = 0
  api.defaults.adapter = async config => {
    if (config.url === '/auth/token/refresh/') {
      refreshes++
      started.resolve()
      await gate.promise
      return ok(config, { access: 'new', refresh: 'rotated' })
    }
    attempts++
    if (config.headers.Authorization !== 'Bearer new') throw fail(config, 401)
    return ok(config, { value: config.url })
  }
  const requests = Promise.all([api.get('/first/'), api.get('/second/')])
  await started.promise
  gate.resolve()
  assert.equal((await requests).length, 2)
  assert.equal(refreshes, 1)
  assert.equal(attempts, 4)
  assert.equal(user.refreshToken, 'rotated')
  assert.equal(window.location.href, '')
})

test('late 401 reuses a token refreshed by an earlier request', async () => {
  const late = deferred()
  const sent = deferred()
  let refreshes = 0
  api.defaults.adapter = async config => {
    if (config.url === '/auth/token/refresh/') {
      refreshes++
      return ok(config, { access: 'new' })
    }
    if (config.url === '/slow/' && !config._retry) {
      sent.resolve()
      await late.promise
      throw fail(config, 401)
    }
    if (config.headers.Authorization !== 'Bearer new') throw fail(config, 401)
    return ok(config)
  }
  const slow = api.get('/slow/')
  await sent.promise
  await api.get('/fast/')
  late.resolve()
  await slow
  assert.equal(refreshes, 1)
  assert.equal(window.location.href, '')
})

test('invalid refresh clears login without recursive logout requests', async () => {
  const calls = []
  api.defaults.adapter = async config => { calls.push(config.url); throw fail(config, 401) }
  await assert.rejects(user.refreshAccessToken())
  assert.deepEqual(calls, ['/auth/token/refresh/'])
  assert.equal(user.accessToken, '')
  assert.equal(user.refreshToken, '')
  assert.equal(window.location.href, '/login')
})

test('transient refresh failure preserves session and allows retry', async () => {
  api.defaults.adapter = async () => { throw new AxiosError('offline', 'ERR_NETWORK') }
  await assert.rejects(user.refreshAccessToken())
  assert.equal(user.accessToken, 'old')
  assert.equal(window.location.href, '')
  api.defaults.adapter = async config => ok(config, { access: 'recovered' })
  await user.refreshAccessToken()
  assert.equal(user.accessToken, 'recovered')
})

test('refresh completing after logout cannot restore credentials', async () => {
  const gate = deferred()
  const started = deferred()
  api.defaults.adapter = async config => { started.resolve(); await gate.promise; return ok(config, { access: 'late' }) }
  const pending = user.refreshAccessToken()
  await started.promise
  await user.logout({ revoke: false })
  gate.resolve()
  await assert.rejects(pending, /Session changed/)
  assert.equal(user.accessToken, '')
  assert.equal(storage.has('access_token'), false)
})

test('concurrent initialization fetches the profile once', async () => {
  let profiles = 0
  api.defaults.adapter = async config => { profiles++; return ok(config, { id: 1, username: 'test' }) }
  await Promise.all([user.initAuth(), user.initAuth()])
  assert.equal(profiles, 1)
  assert.equal(user.user.username, 'test')
})

test('invalid login is returned to the form without refresh or logout', async () => {
  const calls = []
  api.defaults.adapter = async config => { calls.push(config.url); throw fail(config, 401) }
  await assert.rejects(user.login({ username: 'wrong', password: 'wrong' }))
  assert.deepEqual(calls, ['/auth/login/'])
  assert.equal(window.location.href, '')
})

test('manual logout still revokes the previous refresh token', async () => {
  const calls = []
  api.defaults.adapter = async config => { calls.push(config); return ok(config) }
  await user.logout()
  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, '/auth/logout/')
  assert.equal(calls[0].headers.Authorization, 'Bearer old')
  assert.deepEqual(JSON.parse(calls[0].data), { refresh: 'refresh' })
  assert.equal(user.accessToken, '')
})
