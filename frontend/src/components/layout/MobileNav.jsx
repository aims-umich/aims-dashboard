import { BarChart3, Gauge, LayoutGrid, MoreHorizontal, X } from "lucide-react"
import { useEffect, useState } from "react"
import { Link, NavLink, useLocation } from "react-router-dom"
import { useOnSourcePage } from "../../lib/useOnSourcePage"
import LivePill from "./LivePill"
import Logo from "./Logo"
import ThemeToggle from "./ThemeToggle"

const MORE = [
  { to: "/topics", label: "Topics" },
  { to: "/events", label: "Events" },
  { to: "/model", label: "Model" },
  { to: "/about", label: "About" },
]

function Tab({ to, end, active, icon: Icon, children, onClick, as = "link" }) {
  const className = `flex min-h-[52px] flex-col items-center justify-center gap-1 text-[11px] no-underline ${
    active ? "font-semibold text-ink" : "text-ink2"
  }`
  const content = (
    <>
      <Icon size={20} aria-hidden="true" />
      {children}
      <span className={`h-[2px] w-[18px] rounded-full ${active ? "bg-glow" : "bg-transparent"}`} aria-hidden="true" />
    </>
  )
  if (as === "button") {
    return (
      <button type="button" onClick={onClick} className={className} aria-expanded={active}>
        {content}
      </button>
    )
  }
  return (
    <NavLink to={to} end={end} className={className} aria-current={active ? "page" : undefined}>
      {content}
    </NavLink>
  )
}

/** Phones get a compact header and a bottom tab bar; the rest of the pages live behind "More". */
export default function MobileNav({ theme, onToggleTheme, sourcesHref }) {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()
  const onSource = useOnSourcePage()
  const inMore = MORE.some((m) => m.to === pathname)

  useEffect(() => {
    if (!open) return undefined
    const onKey = (event) => event.key === "Escape" && setOpen(false)
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open])

  return (
    <>
      <header className="sticky top-0 z-30 border-b border-line bg-bg md:hidden">
        <div className="flex h-14 items-center justify-between gap-3 px-4">
          <Logo compact />
          <LivePill />
        </div>
      </header>
      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-line2 bg-panel px-2 pt-1.5 pb-[max(10px,env(safe-area-inset-bottom))] md:hidden"
      >
        <Tab to="/" end active={pathname === "/"} icon={Gauge}>
          Overview
        </Tab>
        <Tab to={sourcesHref} active={onSource} icon={LayoutGrid}>
          Sources
        </Tab>
        <Tab to="/compare" active={pathname === "/compare"} icon={BarChart3}>
          Compare
        </Tab>
        <Tab as="button" active={open || inMore} icon={MoreHorizontal} onClick={() => setOpen((o) => !o)}>
          More
        </Tab>
      </nav>
      {open && (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label="More pages">
          <button
            type="button"
            aria-label="Close menu"
            className="absolute inset-0 bg-black/50"
            onClick={() => setOpen(false)}
          />
          <div className="absolute inset-x-0 bottom-0 flex flex-col gap-2 rounded-t-2xl border-t border-line2 bg-panel px-4 pt-4 pb-[max(20px,env(safe-area-inset-bottom))]">
            <div className="flex items-center justify-between">
              <span className="num text-[11px] tracking-[0.1em] text-ink3">MORE</span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close menu"
                className="flex h-11 w-11 items-center justify-center rounded-[10px] border border-line2 text-ink2"
              >
                <X size={18} aria-hidden="true" />
              </button>
            </div>
            {MORE.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                onClick={() => setOpen(false)}
                className={`flex min-h-12 items-center rounded-xl px-4 text-base no-underline ${
                  pathname === item.to ? "bg-panel2 font-semibold text-ink" : "text-ink2"
                }`}
              >
                {item.label}
              </Link>
            ))}
            <div className="mt-2 flex items-center justify-between border-t border-line pt-4">
              <span className="text-sm text-ink2">{theme === "light" ? "Light theme" : "Dark theme"}</span>
              <ThemeToggle theme={theme} onToggle={onToggleTheme} />
            </div>
          </div>
        </div>
      )}
    </>
  )
}
