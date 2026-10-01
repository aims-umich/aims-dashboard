import { useCallback, useEffect, useState } from "react"

const KEY = "theme"

function current() {
  return document.documentElement.dataset.theme === "light" ? "light" : "dark"
}

/** The page theme ("dark" or "light"), applied to <html data-theme> and remembered in this browser. */
export function useTheme() {
  const [theme, setTheme] = useState(current)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", theme === "light" ? "#F2F3F0" : "#080C11")
    try {
      localStorage.setItem(KEY, theme)
    } catch {
      // Storage can be unavailable (private mode); the choice then lasts for this visit only.
    }
  }, [theme])

  const toggle = useCallback(() => setTheme((t) => (t === "light" ? "dark" : "light")), [])
  return [theme, toggle]
}
