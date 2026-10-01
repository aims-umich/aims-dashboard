import { timeAgo } from "../../lib/format"
import { useStatus } from "../../lib/statusContext"

/** Whether the scorer is keeping up, and when it last scored a text. */
export default function LivePill() {
  const { data } = useStatus()
  const scorer = data?.scorer
  const live = scorer?.ok
  const label = !data ? "Connecting" : live ? "LIVE" : "DELAYED"
  return (
    <span className="num flex items-center gap-2 rounded-full border border-line2 px-3 py-1.5 text-xs whitespace-nowrap text-ink2">
      <span
        className={`h-2 w-2 rounded-full ${live ? "bg-glow" : "bg-ink3"}`}
        style={live ? { boxShadow: "0 0 0 4px var(--glow-ring)" } : undefined}
        aria-hidden="true"
      />
      <span className="font-semibold text-ink">{label}</span>
      {scorer?.last_scored_at && <span className="hidden lg:inline">scored {timeAgo(scorer.last_scored_at)}</span>}
    </span>
  )
}
