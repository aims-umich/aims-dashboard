import { Link } from "react-router-dom"
import { formatDate, formatMonth, formatNumber, formatSigned } from "../lib/format"
import { PLATFORMS } from "../lib/platforms"
import { countsTotal, fromCounts, MIN_SAMPLE } from "../lib/stats"
import { usePolling } from "../lib/usePolling"
import Sparkbars from "./charts/Sparkbars"
import Freshness from "./ui/Freshness"
import LowSample from "./ui/LowSample"
import PlatformMark from "./ui/PlatformMark"
import SplitBar from "./ui/SplitBar"

/** The longest run of empty months between months with data, if it is three months or more. */
function collectionGap(trend) {
  const counts = trend.map(countsTotal)
  const first = counts.findIndex((c) => c > 0)
  let best = null
  let start = null
  for (let i = Math.max(0, first); i < counts.length; i++) {
    if (counts[i] === 0 && start == null) start = i
    if (counts[i] > 0 && start != null) {
      if (i - start >= 3 && (!best || i - start > best[1] - best[0])) best = [start, i]
      start = null
    }
  }
  return best && { from: trend[best[0]].bucket, to: trend[best[1] - 1].bucket }
}

export default function SourceCard({ summary, status }) {
  const config = PLATFORMS[summary.platform]
  const { data: year } = usePolling(`/platforms/${summary.platform}/summary?range=1y`, 300_000)
  const trend = year?.trend ?? []
  const months = trend.slice(-13)
  const since = year?.totals?.collecting_since
  const volumes = trend.map(countsTotal)
  // A source whose data all falls in the last two months is new; its sparkline would be two lonely bars.
  const isNew = volumes.slice(-2).some((v) => v > 0) && volumes.slice(0, -2).every((v) => v === 0)
  const empty = trend.length > 0 && volumes.every((v) => v === 0)
  const gap = trend.length ? collectionGap(trend) : null
  const total = countsTotal(summary.sentiment)
  const { net } = fromCounts(summary.sentiment)
  return (
    <Link
      to={config.route}
      className="group flex flex-col gap-4 rounded-2xl border border-line bg-panel p-5 text-ink no-underline transition-colors hover:border-line2"
    >
      <div className="flex items-center gap-3">
        <PlatformMark platform={summary.platform} size={36} />
        <span className="flex min-w-0 flex-col leading-tight">
          <span className="text-base font-[650]">{config.name}</span>
          <span className="text-xs text-ink3">{config.cadence}</span>
        </span>
      </div>
      <Freshness status={status} />
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1 leading-tight">
          <span className="text-xs text-ink3">Scored</span>
          <span className="num text-2xl font-medium">{formatNumber(total)}</span>
        </div>
        <div className="flex flex-col gap-1 leading-tight">
          <span className="text-xs text-ink3">Net sentiment</span>
          {total >= MIN_SAMPLE ? (
            <span className="num text-2xl font-medium">{formatSigned(net)}</span>
          ) : (
            <span className="mt-0.5">
              <LowSample>Too few</LowSample>
            </span>
          )}
        </div>
      </div>
      <SplitBar sentiment={summary.sentiment} />
      <div className="relative h-10 border-t border-line pt-2">
        {empty ? (
          <span className="flex h-8 items-center text-xs text-ink2">No scored {config.unitLabel} in the past year</span>
        ) : isNew ? (
          <span className="flex h-8 items-center text-xs text-ink2">
            New source · collecting since {formatDate(since)}
          </span>
        ) : months.length ? (
          <>
            <Sparkbars values={volumes.slice(-13)} />
            {gap && (
              <span className="hatch absolute inset-x-0 top-2 flex h-8 items-center justify-center rounded text-[11px] text-ink2">
                No collection {formatMonth(gap.from)} to {formatMonth(gap.to)}
              </span>
            )}
          </>
        ) : (
          <span className="block h-8 animate-pulse rounded bg-panel2" />
        )}
      </div>
      <div className="flex justify-between text-xs text-ink3">
        <span>{formatNumber(summary.scored_all_time)} all time</span>
        <span aria-hidden="true" className="transition-transform group-hover:translate-x-0.5">
          →
        </span>
      </div>
    </Link>
  )
}
