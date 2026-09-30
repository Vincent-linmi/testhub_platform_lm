import { ref, onScopeDispose } from 'vue'

// Share request lifecycle, not business filters or API response formats.
export function useListRequest(fetcher, applyResult) {
  const loading = ref(false)
  const error = ref(null)
  let revision = 0
  let controller
  let timer

  const invalidate = () => {
    revision++
    controller?.abort()
    clearTimeout(timer)
  }

  const load = async () => {
    invalidate()
    const current = revision
    controller = new AbortController()
    loading.value = true
    error.value = null
    try {
      const result = await fetcher(controller.signal)
      if (current === revision) applyResult(result)
    } catch (cause) {
      if (current === revision) error.value = cause
    } finally {
      if (current === revision) loading.value = false
    }
  }

  const schedule = () => {
    // Invalidate immediately, including during the debounce window.
    invalidate()
    loading.value = true
    error.value = null
    timer = setTimeout(load, 300)
  }

  onScopeDispose(() => {
    invalidate()
    loading.value = false
  })

  return { loading, error, load, schedule }
}
