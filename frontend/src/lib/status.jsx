import { StatusContext } from "./statusContext"
import { usePolling } from "./usePolling"

// One /status poll for the whole app: the sidebar, home page, and badges all read from it.
export function StatusProvider({ children }) {
  const status = usePolling("/status", 60_000)
  return <StatusContext.Provider value={status}>{children}</StatusContext.Provider>
}
