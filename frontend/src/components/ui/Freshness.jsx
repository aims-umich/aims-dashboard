import { describeStatus } from "../../lib/describeStatus"

const DOT = { ok: "bg-glow", pending: "bg-ink3", stale: "bg-[#E8A33D]", error: "bg-neg" }

/** A status dot and words; the words carry the meaning, so color is never the only cue. */
export default function Freshness({ status, className = "" }) {
  return (
    <span
      className={`flex items-center gap-2 text-xs text-ink2 ${className}`}
      title={status?.last_success_at ? new Date(status.last_success_at).toLocaleString() : undefined}
    >
      <span
        className={`h-[7px] w-[7px] shrink-0 rounded-full ${DOT[status?.state] ?? DOT.pending}`}
        aria-hidden="true"
      />
      {describeStatus(status)}
    </span>
  )
}
