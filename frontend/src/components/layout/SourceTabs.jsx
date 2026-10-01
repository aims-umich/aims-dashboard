import { NavLink } from "react-router-dom"
import { PLATFORM_ORDER, PLATFORMS } from "../../lib/platforms"
import { useStatus } from "../../lib/statusContext"

const DOT = { ok: "bg-glow", pending: "bg-ink3", stale: "bg-[#E8A33D]", error: "bg-neg" }

/** The live sources, as tabs across the top of every source page. */
export default function SourceTabs() {
  const { data } = useStatus()
  const states = Object.fromEntries((data?.platforms ?? []).map((p) => [p.platform, p.state]))
  const keys = PLATFORM_ORDER.filter((key) => !data || key in states)
  return (
    <nav aria-label="Sources" className="-mx-4 flex gap-1 overflow-x-auto border-b border-line px-4 sm:mx-0 sm:px-0">
      {keys.map((key) => (
        <NavLink
          key={key}
          to={PLATFORMS[key].route}
          className={({ isActive }) =>
            `flex min-h-11 shrink-0 items-center gap-2 px-3.5 text-sm no-underline ${
              isActive ? "font-semibold text-ink shadow-[inset_0_-2px_0_var(--ink)]" : "text-ink2 hover:text-ink"
            }`
          }
        >
          <span className={`h-[7px] w-[7px] rounded-full ${DOT[states[key]] ?? DOT.pending}`} aria-hidden="true" />
          {PLATFORMS[key].name}
        </NavLink>
      ))}
    </nav>
  )
}
