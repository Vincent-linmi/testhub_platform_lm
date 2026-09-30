const asArray = value => Array.isArray(value) ? value : []

// Server runs store screenshots directly; local runs return authenticated artifacts.
export function collectExecutionScreenshots(data = {}) {
  const artifacts = asArray(data?.local_artifacts)
    .filter(artifact => artifact?.type === 'screenshot' && artifact.id != null)
    .map(artifact => {
      const name = artifact.name || ''
      const step = name.match(/(?:^|-)(?:failure-)?step-(\d+)(?=\.|$)/)
      const row = name.match(/(?:^|-)row-(\d+)(?=-|$)/)
      return {
        sourceUrl: artifact.download_url,
        screenshot: {
          artifact_id: artifact.id,
          name,
          description: artifact.description || name,
          step_number: step ? Number(step[1]) : undefined,
          data_index: row ? Number(row[1]) : undefined,
          timestamp: artifact.created_at,
          url: null,
          loaded: false,
          error: false
        }
      }
    })
  const artifactsByUrl = new Map(artifacts.filter(item => item.sourceUrl).map(item => [item.sourceUrl, item]))
  const candidates = []
  const addDirect = (screenshot, row) => {
    if (!screenshot || (typeof screenshot !== 'object' && typeof screenshot !== 'string')) return
    let descriptor = typeof screenshot === 'string' ? { url: screenshot } : { ...screenshot }
    if (row && descriptor.data_index == null) descriptor.data_index = row.data_index
    const sourceUrl = descriptor.url
    const artifact = artifactsByUrl.get(sourceUrl)?.screenshot
    if (artifact) {
      // Even when an API URL is also returned as a direct image, it still needs authentication.
      descriptor = {
        ...descriptor,
        ...artifact,
        description: descriptor.description || artifact.description,
        step_number: descriptor.step_number ?? artifact.step_number,
        data_index: descriptor.data_index ?? artifact.data_index,
        timestamp: descriptor.timestamp ?? artifact.timestamp
      }
    }
    candidates.push({ screenshot: descriptor, sourceUrl })
  }
  asArray(data?.screenshots).forEach(screenshot => addDirect(screenshot))
  asArray(data?.data_results).forEach(row => {
    asArray(row?.screenshots).forEach(screenshot => addDirect(screenshot, row))
  })
  candidates.push(...artifacts)

  // A batch summary can repeat row images without row metadata. Keep their owned copies.
  const ownedUrls = new Set()
  const ownedArtifacts = new Set()
  for (const { screenshot, sourceUrl } of candidates) {
    if (screenshot.data_index == null) continue
    if (sourceUrl) ownedUrls.add(sourceUrl)
    if (screenshot.artifact_id != null) ownedArtifacts.add(String(screenshot.artifact_id))
  }
  const screenshots = []
  const seenUrls = new Set()
  const seenArtifacts = new Set()
  candidates.forEach(({ screenshot, sourceUrl }) => {
    const artifactId = screenshot.artifact_id == null ? null : String(screenshot.artifact_id)
    const row = screenshot.data_index == null ? null : String(screenshot.data_index)
    if (row === null && (ownedUrls.has(sourceUrl) || (artifactId && ownedArtifacts.has(artifactId)))) return
    const urlKey = sourceUrl && JSON.stringify([row, sourceUrl])
    const artifactKey = artifactId && JSON.stringify([row, artifactId])
    if ((urlKey && seenUrls.has(urlKey)) || (artifactKey && seenArtifacts.has(artifactKey))) return
    if (urlKey) seenUrls.add(urlKey)
    if (artifactKey) seenArtifacts.add(artifactKey)
    screenshots.push({ loaded: false, error: false, ...screenshot })
  })
  return screenshots
}

const imageMimeTypes = {
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  webp: 'image/webp',
  gif: 'image/gif',
  avif: 'image/avif',
  bmp: 'image/bmp',
  svg: 'image/svg+xml'
}

export function createExecutionScreenshotLoader({
  downloadArtifact,
  createObjectURL = blob => URL.createObjectURL(blob),
  revokeObjectURL = url => URL.revokeObjectURL(url)
}) {
  let generation = 0
  const cache = new Map()

  const load = async (screenshot, { refresh = false } = {}) => {
    if (screenshot?.artifact_id == null) return screenshot
    const requestedGeneration = generation
    const key = String(screenshot.artifact_id)
    let entry = cache.get(key)
    if (refresh && entry) {
      entry.invalidated = true
      if (entry.url) revokeObjectURL(entry.url)
      cache.delete(key)
      entry = null
    }
    if (!entry) {
      entry = { url: null, promise: null, invalidated: false }
      entry.promise = Promise.resolve()
        .then(() => downloadArtifact(screenshot.artifact_id))
        .then(response => {
          if (requestedGeneration !== generation || entry.invalidated) return null
          const extension = (screenshot.name || screenshot.description || '').split('.').pop().toLowerCase()
          const mimeType = imageMimeTypes[extension] || response.data?.type || 'image/png'
          const blob = new Blob([response.data], { type: mimeType })
          entry.url = createObjectURL(blob)
          return entry.url
        })
        .catch(error => {
          // An old request must not evict a retry started after reset().
          if (cache.get(key) === entry) cache.delete(key)
          throw error
        })
      cache.set(key, entry)
    }
    try {
      const url = await entry.promise
      if (requestedGeneration !== generation || entry.invalidated) return null
      return { ...screenshot, url, loaded: false, error: false }
    } catch {
      if (requestedGeneration !== generation || entry.invalidated) return null
      return { ...screenshot, url: null, loaded: true, error: true }
    }
  }

  const reset = () => {
    generation += 1
    for (const entry of cache.values()) {
      entry.invalidated = true
      if (entry.url) revokeObjectURL(entry.url)
    }
    cache.clear()
  }

  return { load, reset }
}
