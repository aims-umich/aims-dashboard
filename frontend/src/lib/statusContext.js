import { createContext, useContext } from "react"

export const StatusContext = createContext({ data: null, error: null, loading: true })

export function useStatus() {
  return useContext(StatusContext)
}

export function usePlatformStatus(key) {
  const { data } = useStatus()
  return data?.platforms.find((p) => p.platform === key) ?? null
}
