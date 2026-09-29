import { useEffect, useState } from "react"
import { getJson } from "./api"

/**
 * Fetches `path` now and every `intervalMs` while the tab is visible.
 * Keeps the previous data on screen while a new path loads, so switching ranges never flashes empty.
 */
export function usePolling(path, intervalMs = 60_000) {
  const [state, setState] = useState({ path: null, data: null, error: null, loading: true, updatedAt: null })

  useEffect(() => {
    if (!path) return undefined
    let cancelled = false
    let controller = null
    let timer = null

    const load = async () => {
      controller?.abort()
      controller = new AbortController()
      setState((s) => ({ ...s, loading: true }))
      try {
        const data = await getJson(path, { signal: controller.signal })
        if (!cancelled) setState({ path, data, error: null, loading: false, updatedAt: new Date() })
      } catch (error) {
        if (!cancelled && error.name !== "AbortError") setState((s) => ({ ...s, error, loading: false }))
      }
    }

    const schedule = () => {
      clearInterval(timer)
      timer = setInterval(() => {
        if (document.visibilityState === "visible") load()
      }, intervalMs)
    }

    const onVisible = () => {
      if (document.visibilityState === "visible") {
        load()
        schedule()
      }
    }

    load()
    schedule()
    document.addEventListener("visibilitychange", onVisible)
    return () => {
      cancelled = true
      controller?.abort()
      clearInterval(timer)
      document.removeEventListener("visibilitychange", onVisible)
    }
  }, [path, intervalMs])

  return state
}
