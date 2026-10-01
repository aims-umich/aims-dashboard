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

/** Like usePolling, for a list of paths fetched together; `data` is an array in the same order. */
export function usePollingAll(paths, intervalMs = 120_000) {
  const key = paths.join("\n")
  const [state, setState] = useState({ key: null, data: null, error: null })

  useEffect(() => {
    if (!key) return undefined
    const list = key.split("\n")
    let cancelled = false
    const controller = new AbortController()
    const load = async () => {
      try {
        const data = await Promise.all(list.map((p) => getJson(p, { signal: controller.signal })))
        if (!cancelled) setState({ key, data, error: null })
      } catch (error) {
        if (!cancelled && error.name !== "AbortError") setState((s) => ({ ...s, error }))
      }
    }
    load()
    const timer = setInterval(() => document.visibilityState === "visible" && load(), intervalMs)
    return () => {
      cancelled = true
      controller.abort()
      clearInterval(timer)
    }
  }, [key, intervalMs])

  return state.key === key ? state : { data: null, error: state.error }
}
