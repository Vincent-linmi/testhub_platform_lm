import assert from 'node:assert/strict'
import { test } from 'node:test'
import { effectScope } from 'vue'
import { useListRequest } from '../src/composables/useListRequest.js'
const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

test('a slow old response cannot overwrite the latest list or loading state', async () => {
  const scope = effectScope()
  const first = deferred(), second = deferred()
  const results = [], signals = []
  const request = scope.run(() => useListRequest(signal => {
    signals.push(signal)
    return signals.length === 1 ? first.promise : second.promise
  }, value => results.push(value)))
  const old = request.load()
  const latest = request.load()
  assert.equal(signals[0].aborted, true)
  first.resolve('old')
  await old
  assert.equal(request.loading.value, true)
  second.resolve('new')
  await latest
  assert.deepEqual(results, ['new'])
  assert.equal(request.loading.value, false)
  scope.stop()
})

test('typing coalesces requests and invalidates responses during the debounce window', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const scope = effectScope()
  const oldResponse = deferred()
  let calls = 0
  const results = []
  const request = scope.run(() => useListRequest(() => {
    calls++
    return calls === 1 ? oldResponse.promise : Promise.resolve('latest')
  }, value => results.push(value)))
  const old = request.load()
  request.schedule()
  request.schedule()
  oldResponse.resolve('old')
  await old
  assert.deepEqual(results, [])
  t.mock.timers.tick(299)
  assert.equal(calls, 1)
  t.mock.timers.tick(1)
  await Promise.resolve()
  assert.equal(calls, 2)
  assert.deepEqual(results, ['latest'])
  scope.stop()
})

test('failed requests expose retry state and a successful retry clears it', async () => {
  const scope = effectScope()
  let calls = 0
  const request = scope.run(() => useListRequest(async () => {
    if (++calls === 1) throw new Error('offline')
    return 'ok'
  }, () => {}))
  await request.load()
  assert.match(request.error.value.message, /offline/)
  assert.equal(request.loading.value, false)
  await request.load()
  assert.equal(request.error.value, null)
  scope.stop()
})

test('unmount cancels pending search and ignores responses already in flight', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const scope = effectScope()
  const gate = deferred()
  let calls = 0, applied = 0
  const request = scope.run(() => useListRequest(() => { calls++; return gate.promise }, () => applied++))
  const pending = request.load()
  request.schedule()
  scope.stop()
  gate.resolve('stale')
  await pending
  t.mock.timers.tick(1000)
  assert.equal(calls, 1)
  assert.equal(applied, 0)
})
