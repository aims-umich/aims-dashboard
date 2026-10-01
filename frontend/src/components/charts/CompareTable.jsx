import { formatNumber, formatPercent, formatRange, formatSigned } from "../../lib/format"
import { PLATFORMS } from "../../lib/platforms"
import { fromCounts, leanColor, MIN_SAMPLE } from "../../lib/stats"
import PlatformMark from "../ui/PlatformMark"
import SplitBar from "../ui/SplitBar"

const COLS = "grid-cols-[210px_minmax(260px,1.4fr)_110px_minmax(220px,1fr)_90px_100px]"

function since(row) {
  const first = row.totals?.first_published
  return first ? new Date(first).getUTCFullYear() : null
}

/** Every source on one row: net sentiment with its interval, the split, sample size and confidence. */
export default function CompareTable({ platforms }) {
  const rows = platforms.map((p) => ({ ...p, ...fromCounts(p.sentiment), config: PLATFORMS[p.platform] }))
  const ok = rows.filter((r) => r.n >= MIN_SAMPLE)
  const lo = Math.min(-0.4, Math.floor(Math.min(...ok.map((r) => r.lo), 0) * 5) / 5)
  const hi = Math.max(0.2, Math.ceil(Math.max(...ok.map((r) => r.hi), 0) * 5) / 5)
  const pct = (v) => ((v - lo) / (hi - lo)) * 100
  const ticks = []
  for (let v = lo; v <= hi + 1e-9; v += 0.2) ticks.push(Math.round(v * 10) / 10)
  return (
    <>
      <div className="flex flex-col overflow-hidden rounded-2xl border border-line bg-panel md:hidden">
        {rows.map((r) => (
          <div key={r.platform} className="flex flex-col gap-2 border-b border-line px-4 py-3.5 last:border-b-0">
            <div className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2.5">
                <PlatformMark platform={r.platform} size={26} />
                <span className="text-[15px] font-semibold">{r.config.name}</span>
              </span>
              <span className="num text-sm">{r.n >= MIN_SAMPLE ? formatSigned(r.net, 3) : "too few"}</span>
            </div>
            <SplitBar sentiment={r.sentiment} height={8} labels />
            <span className="num flex justify-between text-[11px] text-ink3">
              <span>{formatNumber(r.n)} scored</span>
              <span>{r.n >= MIN_SAMPLE ? formatRange(r.lo, r.hi) : ""}</span>
              <span>{formatPercent(r.totals?.avg_confidence, 1)} sure</span>
            </span>
          </div>
        ))}
      </div>
      <div className="hidden overflow-x-auto rounded-2xl border border-line bg-panel md:block">
        <div className="min-w-[1000px]">
          <div className={`grid ${COLS} items-center gap-5 border-b border-line2 px-6 py-3.5 text-xs text-ink3`}>
            <span>Source</span>
            <span>Net sentiment, 95% interval</span>
            <span className="text-right">Net</span>
            <span>Positive · neutral · negative</span>
            <span className="text-right">Scored</span>
            <span className="text-right">Confidence</span>
          </div>
          {rows.map((r) => (
            <div key={r.platform} className={`grid ${COLS} min-h-16 items-center gap-5 border-b border-line px-6`}>
              <div className="flex items-center gap-3">
                <PlatformMark platform={r.platform} size={30} />
                <span className="flex flex-col leading-tight">
                  <span className="text-[15px] font-semibold">{r.config.name}</span>
                  <span className="text-xs text-ink3">
                    {r.config.unitLabel[0].toUpperCase() + r.config.unitLabel.slice(1)}
                    {since(r) ? ` · since ${since(r)}` : ""}
                  </span>
                </span>
              </div>
              <div className="relative h-10">
                {ticks.map((t) => (
                  <div
                    key={t}
                    className={`absolute inset-y-0 w-px ${t === 0 ? "bg-line2" : "bg-line"}`}
                    style={{ left: `${pct(t)}%` }}
                  />
                ))}
                {r.n >= MIN_SAMPLE ? (
                  <>
                    <div
                      className="absolute top-[19px] h-[2px] bg-ink3"
                      style={{ left: `${pct(r.lo)}%`, width: `${pct(r.hi) - pct(r.lo)}%` }}
                    />
                    <div
                      className="absolute top-3 -ml-2 h-4 w-4 rounded-full"
                      style={{ left: `${pct(r.net)}%`, background: leanColor(r), boxShadow: "0 0 0 3px var(--panel)" }}
                    />
                  </>
                ) : (
                  <span className="hatch absolute top-2 left-2 rounded-md border border-line2 px-2 py-[3px] text-xs text-ink2">
                    Too few to call
                  </span>
                )}
              </div>
              <span className="flex flex-col items-end leading-tight">
                <span className="num text-[17px] font-medium">{r.n >= MIN_SAMPLE ? formatSigned(r.net, 3) : "-"}</span>
                <span className="num text-[11px] text-ink3">
                  {r.n >= MIN_SAMPLE ? formatRange(r.lo, r.hi) : `n = ${r.n}`}
                </span>
              </span>
              <SplitBar sentiment={r.sentiment} height={10} labels />
              <span className="num text-right text-sm">{formatNumber(r.n)}</span>
              <span className="num text-right text-sm">{formatPercent(r.totals?.avg_confidence, 1)}</span>
            </div>
          ))}
          <div className={`grid ${COLS} gap-5 px-6 pt-2.5 pb-3.5`}>
            <span />
            <div className="num relative h-4 text-[11px] text-ink3">
              {ticks.map((t) => (
                <span key={t} className="absolute -translate-x-1/2" style={{ left: `${pct(t)}%` }}>
                  {t === 0 ? "0" : formatSigned(t, 1)}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
