import { timeAgo } from "./format"

export function describeStatus(status) {
  if (!status) return "Checking…"
  const when = timeAgo(status.last_success_at)
  switch (status.state) {
    case "ok":
      return `Updated ${when}`
    case "pending":
      return "Starting up"
    case "stale":
      return `Delayed · last update ${when}`
    default:
      return status.last_success_at ? `Collection paused · last update ${when}` : "Collection paused"
  }
}
