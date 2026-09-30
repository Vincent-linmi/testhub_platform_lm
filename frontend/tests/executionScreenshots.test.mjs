import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  collectExecutionScreenshots,
  createExecutionScreenshotLoader
} from '../src/views/ui-automation/test-cases/executionScreenshots.js'

const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const artifactScreenshot = (overrides = {}) => ({
  artifact_id: 7,
  name: 'failure-step-3.png',
  description: 'failure-step-3.png',
  url: null,
  loaded: false,
  error: false,
  ...overrides
})

test('collects server, data-row and local screenshots with their step and row metadata', () => {
  const source = { url: '/media/failure.png', step_number: 2, description: 'Server failure' }
  const screenshots = collectExecutionScreenshots({
    screenshots: [source],
    data_results: [{ data_index: 0, screenshots: [{ url: '/media/row.png', step_number: 4 }] }],
    local_artifacts: [
      { id: 9, type: 'playwright_trace', name: 'trace.zip' },
      { id: 10, type: 'screenshot', name: 'row-0-failure-step-7.png', created_at: '2026-09-30T12:00:00Z' },
      { id: 11, type: 'screenshot', name: 'execution-42-step-2.png' }
    ]
  })
  assert.equal(screenshots.length, 4)
  assert.deepEqual(screenshots[0], { loaded: false, error: false, ...source })
  assert.equal(screenshots[1].data_index, 0)
  assert.deepEqual(screenshots[2], {
    artifact_id: 10,
    name: 'row-0-failure-step-7.png',
    description: 'row-0-failure-step-7.png',
    step_number: 7,
    data_index: 0,
    timestamp: '2026-09-30T12:00:00Z',
    url: null,
    loaded: false,
    error: false
  })
  assert.equal(screenshots[3].step_number, 2)
  assert.equal(screenshots[3].data_index, undefined)
  assert.equal(source.loaded, undefined, 'collection must not mutate response objects')
})

test('deduplicates URLs and artifact IDs while retaining distinct local images without URLs', () => {
  const screenshots = collectExecutionScreenshots({
    screenshots: [{ url: '/same.png' }, { url: '/artifact/7/download/' }],
    data_results: [{ data_index: 1, screenshots: [{ url: '/same.png' }] }],
    local_artifacts: [
      { id: 7, type: 'screenshot', name: 'failure-step-1.png', download_url: '/artifact/7/download/' },
      { id: 8, type: 'screenshot', name: 'failure-step-2.png' },
      { id: '8', type: 'screenshot', name: 'failure-step-2.png' },
      { id: 9, type: 'screenshot', name: 'failure-step-3.png' }
    ]
  })
  assert.equal(screenshots.length, 4)
  assert.deepEqual(screenshots.filter(item => item.artifact_id).map(item => item.artifact_id), [7, 8, 9])
  assert.equal(screenshots.find(item => item.url === '/same.png').data_index, 1)
  assert.equal(screenshots.find(item => item.artifact_id === 7).url, null)
  assert.deepEqual(collectExecutionScreenshots(null), [])
})

test('keeps identical image data for different rows and removes unowned batch-summary copies', () => {
  const sharedImage = 'data:image/png;base64,c2FtZSBwaXhlbHM='
  const screenshots = collectExecutionScreenshots({
    screenshots: [{ url: sharedImage }, { url: '/top-only.png' }],
    data_results: [
      { data_index: 0, screenshots: [{ url: sharedImage }, { url: sharedImage }] },
      { data_index: 1, screenshots: [{ url: sharedImage }, { url: '/row-only.png' }] }
    ]
  })
  assert.equal(screenshots.length, 4)
  assert.deepEqual(screenshots.filter(item => item.url === sharedImage).map(item => item.data_index), [0, 1])
  assert.deepEqual(screenshots.filter(item => item.data_index == null).map(item => item.url), ['/top-only.png'])
  assert.equal(screenshots.find(item => item.url === '/row-only.png').data_index, 1)
})

test('prefers authenticated artifact loading when direct and artifact URLs overlap', async () => {
  const downloadUrl = '/api/ui-automation/local-runner/artifacts/17/download/'
  const screenshots = collectExecutionScreenshots({
    screenshots: [{ url: downloadUrl, description: 'Failure screenshot' }],
    data_results: [{ data_index: 0, screenshots: [{ url: downloadUrl }] }],
    local_artifacts: [
      { id: 17, type: 'screenshot', name: 'row-0-failure-step-3.png', download_url: downloadUrl },
      { id: 17, type: 'screenshot', name: 'row-0-failure-step-3.png', download_url: downloadUrl }
    ]
  })
  assert.equal(screenshots.length, 1)
  assert.equal(screenshots[0].artifact_id, 17)
  assert.equal(screenshots[0].url, null)
  assert.equal(screenshots[0].data_index, 0)
  assert.equal(screenshots[0].step_number, 3)
  assert.equal(screenshots[0].description, 'Failure screenshot')
  const requests = []
  const loader = createExecutionScreenshotLoader({
    downloadArtifact: async id => { requests.push(id); return { data: new Blob(['pixels']) } },
    createObjectURL: () => 'blob:authenticated-image',
    revokeObjectURL: () => {}
  })
  assert.equal((await loader.load(screenshots[0])).url, 'blob:authenticated-image')
  assert.deepEqual(requests, [17])
})

test('downloads authenticated artifacts once across concurrent loads and later polling', async () => {
  const gate = deferred()
  const requestedIds = [], blobs = []
  const loader = createExecutionScreenshotLoader({
    downloadArtifact: id => { requestedIds.push(id); return gate.promise },
    createObjectURL: blob => { blobs.push(blob); return 'blob:screenshot' },
    revokeObjectURL: () => {}
  })
  const screenshot = artifactScreenshot()
  const first = loader.load(screenshot)
  const concurrent = loader.load({ ...screenshot, description: 'Updated description' })
  await Promise.resolve()
  assert.deepEqual(requestedIds, [7])
  gate.resolve({ data: new Blob(['pixels'], { type: 'application/octet-stream' }) })
  const [firstResult, concurrentResult] = await Promise.all([first, concurrent])
  assert.equal(firstResult.url, 'blob:screenshot')
  assert.equal(firstResult.loaded, false)
  assert.equal(concurrentResult.description, 'Updated description')
  assert.equal(blobs.length, 1)
  assert.equal(blobs[0].type, 'image/png')
  assert.equal(await blobs[0].text(), 'pixels')
  assert.notEqual(firstResult, screenshot)
  assert.equal(screenshot.url, null)
  assert.equal((await loader.load(screenshot)).url, 'blob:screenshot')
  assert.deepEqual(requestedIds, [7])
  const direct = { url: '/media/direct.png' }
  assert.equal(await loader.load(direct), direct)
})

test('uses the image extension to correct generic attachment MIME types', async () => {
  const types = []
  const loader = createExecutionScreenshotLoader({
    downloadArtifact: async () => ({ data: new Blob(['pixels'], { type: 'application/octet-stream' }) }),
    createObjectURL: blob => { types.push(blob.type); return `blob:${types.length}` },
    revokeObjectURL: () => {}
  })
  await loader.load(artifactScreenshot({ artifact_id: 1, name: 'shot.JPG' }))
  await loader.load(artifactScreenshot({ artifact_id: 2, name: 'shot.webp' }))
  assert.deepEqual(types, ['image/jpeg', 'image/webp'])
})

test('a failed download shows an error and can be retried on the next load', async () => {
  let requests = 0
  const loader = createExecutionScreenshotLoader({
    downloadArtifact: async () => {
      if (++requests === 1) throw new Error('offline')
      return { data: new Blob(['pixels']) }
    },
    createObjectURL: () => 'blob:recovered',
    revokeObjectURL: () => {}
  })
  const screenshot = artifactScreenshot()
  const failed = await loader.load(screenshot)
  assert.deepEqual(failed, { ...screenshot, url: null, loaded: true, error: true })
  const recovered = await loader.load(failed)
  assert.equal(recovered.url, 'blob:recovered')
  assert.equal(recovered.error, false)
  assert.equal(recovered.loaded, false)
  assert.equal(requests, 2)
})

test('reset revokes cached URLs and downloads again for the next execution', async () => {
  const revoked = []
  let requests = 0
  const loader = createExecutionScreenshotLoader({
    downloadArtifact: async () => { requests++; return { data: new Blob(['pixels']) } },
    createObjectURL: () => `blob:${requests}`,
    revokeObjectURL: url => revoked.push(url)
  })
  await loader.load(artifactScreenshot())
  await loader.load(artifactScreenshot())
  loader.reset()
  loader.reset()
  assert.deepEqual(revoked, ['blob:1'])
  assert.equal((await loader.load(artifactScreenshot())).url, 'blob:2')
  assert.equal(requests, 2)
})

test('refresh retries a decoded-image failure and revokes its previously cached URL', async () => {
  let requests = 0
  const revoked = []
  const loader = createExecutionScreenshotLoader({
    downloadArtifact: async () => { requests++; return { data: new Blob(['pixels']) } },
    createObjectURL: () => `blob:${requests}`,
    revokeObjectURL: url => revoked.push(url)
  })
  const screenshot = artifactScreenshot()
  const first = await loader.load(screenshot)
  assert.equal(first.url, 'blob:1')
  const refreshed = await loader.load({ ...first, error: true }, { refresh: true })
  assert.equal(refreshed.url, 'blob:2')
  assert.equal(refreshed.error, false)
  assert.deepEqual(revoked, ['blob:1'])
  assert.equal((await loader.load(screenshot)).url, 'blob:2')
  assert.equal(requests, 2)
})

test('refresh invalidates an in-flight download without leaking its eventual URL', async () => {
  const first = deferred()
  let requests = 0, created = 0
  const loader = createExecutionScreenshotLoader({
    downloadArtifact: () => ++requests === 1 ? first.promise : Promise.resolve({ data: new Blob(['new']) }),
    createObjectURL: () => `blob:${++created}`,
    revokeObjectURL: () => {}
  })
  const firstLoad = loader.load(artifactScreenshot())
  await Promise.resolve()
  const refreshed = await loader.load(artifactScreenshot(), { refresh: true })
  first.resolve({ data: new Blob(['old']) })
  assert.equal(await firstLoad, null)
  assert.equal(refreshed.url, 'blob:1')
  assert.equal(created, 1)
  assert.equal(requests, 2)
})

test('requests completed after reset never create URLs or replace the current cache', async () => {
  const old = deferred(), current = deferred()
  let requests = 0, created = 0
  const loader = createExecutionScreenshotLoader({
    downloadArtifact: () => ++requests === 1 ? old.promise : current.promise,
    createObjectURL: () => `blob:${++created}`,
    revokeObjectURL: () => {}
  })
  const oldLoad = loader.load(artifactScreenshot())
  await Promise.resolve()
  loader.reset()
  const currentLoad = loader.load(artifactScreenshot())
  old.resolve({ data: new Blob(['stale']) })
  assert.equal(await oldLoad, null)
  assert.equal(created, 0)
  current.resolve({ data: new Blob(['current']) })
  assert.equal((await currentLoad).url, 'blob:1')
  assert.equal((await loader.load(artifactScreenshot())).url, 'blob:1')
  assert.equal(requests, 2)
})

test('a rejected stale request cannot evict a request started after reset', async () => {
  const old = deferred()
  let requests = 0
  const loader = createExecutionScreenshotLoader({
    downloadArtifact: () => ++requests === 1 ? old.promise : Promise.resolve({ data: new Blob(['current']) }),
    createObjectURL: () => 'blob:current',
    revokeObjectURL: () => {}
  })
  const oldLoad = loader.load(artifactScreenshot())
  await Promise.resolve()
  loader.reset()
  await loader.load(artifactScreenshot())
  old.reject(new Error('stale failure'))
  assert.equal(await oldLoad, null)
  assert.equal((await loader.load(artifactScreenshot())).url, 'blob:current')
  assert.equal(requests, 2)
})
