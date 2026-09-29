import { useEffect, useState } from "react"
import { FiMoon, FiSun } from "react-icons/fi"
import { Outlet } from "react-router-dom"
import { Sidebar } from "./components/Sidebar"
import { StatusProvider } from "./lib/status"

function readDarkMode() {
  try {
    const saved = localStorage.getItem("darkMode")
    if (saved != null) return JSON.parse(saved)
  } catch {
    // Storage can be unavailable (private mode); fall back to the system preference.
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? true
}

const Layout = () => {
  const [darkMode, setDarkMode] = useState(readDarkMode)

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode)
    try {
      localStorage.setItem("darkMode", JSON.stringify(darkMode))
    } catch {
      // Ignore: the preference just will not persist.
    }
  }, [darkMode])

  return (
    <StatusProvider>
      <Sidebar>
        <div className="px-4 pb-12 pt-4 sm:px-6 lg:px-8">
          <div className="mb-2 flex justify-end">
            <button
              type="button"
              onClick={() => setDarkMode(!darkMode)}
              className="rounded-lg bg-gray-200 p-2 text-gray-800 hover:bg-gray-300 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
              aria-label={darkMode ? "Switch to light mode" : "Switch to dark mode"}
            >
              {darkMode ? <FiSun className="h-5 w-5" /> : <FiMoon className="h-5 w-5" />}
            </button>
          </div>
          <main>
            <Outlet />
          </main>
          <footer className="mx-auto mt-16 max-w-7xl border-t border-gray-200 pt-6 text-xs text-gray-500 dark:border-gray-800 dark:text-gray-400">
            AIMS Lab, University of Michigan · Public posts and articles collected through each platform&apos;s official
            API · Labels are model estimates
          </footer>
        </div>
      </Sidebar>
    </StatusProvider>
  )
}

export default Layout
