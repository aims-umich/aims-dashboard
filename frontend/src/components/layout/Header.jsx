import { NavLink } from "react-router-dom"
import { useOnSourcePage } from "../../lib/useOnSourcePage"
import LivePill from "./LivePill"
import Logo from "./Logo"
import { NAV } from "./nav"
import ThemeToggle from "./ThemeToggle"

function navClass(active) {
  return `px-3 py-2.5 text-sm whitespace-nowrap no-underline transition-colors ${
    active ? "font-semibold text-ink shadow-[inset_0_-2px_0_var(--glow)]" : "text-ink2 hover:text-ink"
  }`
}

export default function Header({ theme, onToggleTheme, sourcesHref }) {
  const onSource = useOnSourcePage()
  return (
    <header className="sticky top-0 z-30 hidden border-b border-line bg-bg md:block">
      <div className="mx-auto flex min-h-16 max-w-[1320px] items-center gap-8 px-10">
        <Logo />
        <nav aria-label="Main" className="flex min-w-0 flex-1 gap-0.5 overflow-x-auto">
          {NAV.map((item) =>
            item.to === "/sources" ? (
              <NavLink
                key={item.to}
                to={sourcesHref}
                className={() => navClass(onSource)}
                aria-current={onSource ? "page" : undefined}
              >
                {item.label}
              </NavLink>
            ) : (
              <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => navClass(isActive)}>
                {item.label}
              </NavLink>
            ),
          )}
        </nav>
        <div className="flex items-center gap-3">
          <LivePill />
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        </div>
      </div>
    </header>
  )
}
