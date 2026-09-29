import { timeAgo } from "../../lib/format"

const STYLES = {
  ok: { dot: "bg-emerald-500", text: "text-emerald-700 dark:text-emerald-300", ring: "ring-emerald-600/20" },
  pending: { dot: "bg-sky-500", text: "text-sky-700 dark:text-sky-300", ring: "ring-sky-600/20" },
  stale: { dot: "bg-amber-500", text: "text-amber-700 dark:text-amber-300", ring: "ring-amber-600/20" },
  error: { dot: "bg-red-500", text: "text-red-700 dark:text-red-300", ring: "ring-red-600/20" },
}

function describe(status) {
  if (!status) return "Checking…"
  const when = timeAgo(status.last_success_at)
  switch (status.state) {
    case "ok":
      return `Live · updated ${when}`
    case "pending":
      return "Starting up"
    case "stale":
      return `Delayed · last update ${when}`
    default:
      return status.last_success_at ? `Collection paused · last update ${when}` : "Collection paused"
  }
}

export default function FreshnessBadge({ status }) {
  const style = STYLES[status?.state] ?? STYLES.pending
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full bg-white/80 dark:bg-gray-800/80 px-3 py-1 text-xs font-medium ring-1 ring-inset ${style.ring} ${style.text}`}
      title={status?.last_success_at ? new Date(status.last_success_at).toLocaleString() : undefined}
    >
      <span className="relative flex h-2 w-2">
        {status?.state === "ok" && (
          <span className={`absolute inline-flex h-full w-full rounded-full opacity-60 animate-ping ${style.dot}`} />
        )}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${style.dot}`} />
      </span>
      {describe(status)}
    </span>
  )
}
