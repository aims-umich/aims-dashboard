import { createContext, useContext } from "react"

export const SidebarContext = createContext(undefined)

export function useSidebar() {
  const context = useContext(SidebarContext)
  if (!context) {
    throw new Error("useSidebar must be used within a SidebarImpl.")
  }
  return context
}
