const numberFormat = new Intl.NumberFormat("en-US")
const compactFormat = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 })
const relative = new Intl.RelativeTimeFormat("en-US", { numeric: "auto" })
const MINUS = "−"

export const formatNumber = (value) => (value == null ? "-" : numberFormat.format(value))

export const formatCompact = (value) => (value == null ? "-" : compactFormat.format(value))

export const formatPercent = (value, digits = 0) => (value == null ? "-" : `${(value * 100).toFixed(digits)}%`)

/** A signed value with a true minus sign: "+0.07", "−0.11", "0.00". */
export function formatSigned(value, digits = 2) {
  if (value == null || Number.isNaN(value)) return "-"
  const fixed = Math.abs(value).toFixed(digits)
  if (Number(fixed) === 0) return fixed
  return value > 0 ? `+${fixed}` : `${MINUS}${fixed}`
}

export const formatRange = (lo, hi, digits = 2) => `${formatSigned(lo, digits)} to ${formatSigned(hi, digits)}`

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
  // A bare date ("2022-03-04") is a calendar day, not an instant: show it as written, in UTC.
  const dayOnly = typeof date === "string" && date.length === 10
  return new Date(dayOnly ? `${date}T00:00:00Z` : date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    ...(dayOnly ? { timeZone: "UTC" } : {}),
  })
}

export function formatDateTime(date) {
  if (!date) return "-"
  return new Date(date).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
}

const UTC = { timeZone: "UTC" }

/** "2026-09" or "2026-09-01" as "Sep 2026". */
export function formatMonth(value, { short = false } = {}) {
  const date = new Date(`${value.slice(0, 7)}-01T00:00:00Z`)
  return date.toLocaleDateString("en-US", { month: "short", year: short ? "2-digit" : "numeric", ...UTC })
}

/** API bucket keys are UTC ("2026-09-01" or "2026-09-30T14:00:00Z"); render them without shifting zones. */
export function formatBucket(bucket, size) {
  if (size === "hour") {
    const date = new Date(bucket)
    return `${date.toLocaleDateString("en-US", { month: "short", day: "numeric", ...UTC })}, ${String(
      date.getUTCHours(),
    ).padStart(2, "0")}:00 UTC`
  }
  const date = new Date(`${bucket.slice(0, 10)}T00:00:00Z`)
  if (size === "month") return date.toLocaleDateString("en-US", { month: "short", year: "numeric", ...UTC })
  if (size === "week") return `Week of ${date.toLocaleDateString("en-US", { month: "short", day: "numeric", ...UTC })}`
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", ...UTC })
}

/** A short axis label for a bucket. */
export function formatTick(bucket, size) {
  if (size === "hour") return `${String(new Date(bucket).getUTCHours()).padStart(2, "0")}:00`
  const date = new Date(`${bucket.slice(0, 10)}T00:00:00Z`)
  if (size === "month") return date.toLocaleDateString("en-US", { month: "short", year: "2-digit", ...UTC })
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", ...UTC })
}
