import { useLocation } from "react-router-dom"
import { PLATFORMS } from "./platforms"

const SOURCE_ROUTES = new Set(Object.values(PLATFORMS).map((p) => p.route))

export function useOnSourcePage() {
  return SOURCE_ROUTES.has(useLocation().pathname)
}
