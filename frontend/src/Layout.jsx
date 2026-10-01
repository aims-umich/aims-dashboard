import { Suspense } from "react"
import { Outlet } from "react-router-dom"
import Footer from "./components/layout/Footer"
import Header from "./components/layout/Header"
import MobileNav from "./components/layout/MobileNav"
import { Skeleton } from "./components/ui/Panel"
import { PLATFORM_ORDER, PLATFORMS } from "./lib/platforms"
import { StatusProvider } from "./lib/status"
import { useStatus } from "./lib/statusContext"
import { useTheme } from "./lib/theme"

function Shell() {
  const [theme, toggleTheme] = useTheme()
  const { data } = useStatus()
  const live = data?.platforms?.map((p) => p.platform)
  const first = PLATFORM_ORDER.find((key) => !live || live.includes(key)) ?? "bluesky"
  const sourcesHref = PLATFORMS[first].route
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-panel2 px-4 py-2 text-ink focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Skip to content
      </a>
      <Header theme={theme} onToggleTheme={toggleTheme} sourcesHref={sourcesHref} />
      <MobileNav theme={theme} onToggleTheme={toggleTheme} sourcesHref={sourcesHref} />
      <main id="main" className="mx-auto w-full max-w-[1320px] flex-1 px-4 pb-24 sm:px-10">
        <Suspense fallback={<Skeleton height={480} className="mt-14" />}>
          <Outlet />
        </Suspense>
      </main>
      <Footer />
    </div>
  )
}

export default function Layout() {
  return (
    <StatusProvider>
      <Shell />
    </StatusProvider>
  )
}
