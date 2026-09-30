const numberFormat = new Intl.NumberFormat("en-US")
const compactFormat = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 })
const relative = new Intl.RelativeTimeFormat("en-US", { numeric: "auto" })

export const formatNumber = (value) => (value == null ? "-" : numberFormat.format(value))

export const formatCompact = (value) => (value == null ? "-" : compactFormat.format(value))

export const formatPercent = (value, digits = 0) =>
  value == null ? "-" : `${(value * 100).toFixed(digits)}%`

export function formatSigned(value, digits = 2) {
  if (value == null) return "-"
  const fixed = value.toFixed(digits)
  return value > 0 ? `+${fixed}` : fixed
}

export function timeAgo(date, now = new Date()) {
  if (!date) return "never"
  const seconds = Math.round((new Date(date).getTime() - now.getTime()) / 1000)
  const abs = Math.abs(seconds)
  if (abs < 45) return "just now"
  if (abs < 3600) return relative.format(Math.round(seconds / 60), "minute")
  if (abs < 86_400) return relative.format(Math.round(seconds / 3600), "hour")
  if (abs < 86_400 * 45) return relative.format(Math.round(seconds / 86_400), "day")
  if (abs < 86_400 * 365) return relative.format(Math.round(seconds / (86_400 * 30)), "month")
  return relative.format(Math.round(seconds / (86_400 * 365)), "year")
}

export function formatDate(date) {
  if (!date) return "-"
  return new Date(date).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })
}

export function formatDateTime(date) {
  if (!date) return "-"
  return new Date(date).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

// Bucket keys are UTC dates ("2026-09-01"); render them without shifting into the viewer's time zone.
export function formatBucket(bucket, size) {
  const date = new Date(`${bucket}T00:00:00Z`)
  if (size === "month") return date.toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" })
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" })
}
