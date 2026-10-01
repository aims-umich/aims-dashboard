import { formatNumber, formatRange, formatSigned } from "../../lib/format"
import { PLATFORMS } from "../../lib/platforms"
import { fromCounts, leanColor, MIN_SAMPLE, sumCounts } from "../../lib/stats"
import { useMarkHover } from "../../lib/useHover"
import { Legend, LegendItem } from "../ui/Legend"
import PlatformMark from "../ui/PlatformMark"
import SplitBar from "../ui/SplitBar"
import Tooltip from "../ui/Tooltip"

const GROUPS = [
  { key: "social", label: "SOCIAL PLATFORMS", noun: "texts" },
  { key: "news", label: "NEWSPAPERS", noun: "texts" },
]

/** Pick a domain that holds every interval, in steps of 0.2, always including zero. */
function domainFor(rows) {
  const lows = rows.map((r) => r.lo).filter((v) => v != null)
  const highs = rows.map((r) => r.hi).filter((v) => v != null)
  const lo = Math.min(-0.2, Math.floor((Math.min(...lows, 0) - 0.05) * 5) / 5)
  const hi = Math.max(0.2, Math.ceil((Math.max(...highs, 0) + 0.05) * 5) / 5)
  return [Math.max(-1, lo), Math.min(1, hi)]
}

function ticksFor([lo, hi]) {
  const ticks = []
  for (let v = lo; v <= hi + 1e-9; v += 0.2) ticks.push(Math.round(v * 10) / 10)
  return ticks
}

/**
 * Net sentiment of each source with its 95% interval, grouped into social platforms and newspapers.
 * `platforms` are rows from /platforms (with `sentiment` counts).
 */
export default function SourceScale({ platforms, unitOf }) {
  const { ref, hover, enter, leave } = useMarkHover()
  const rows = platforms.map((p) => ({ ...p, ...fromCounts(p.sentiment), config: PLATFORMS[p.platform] }))
  const shown = rows.filter((r) => r.n >= MIN_SAMPLE)
  const domain = domainFor(shown)
  const ticks = ticksFor(domain)
  const pct = (v) => ((v - domain[0]) / (domain[1] - domain[0])) * 100
  const groups = GROUPS.map((g) => {
    const members = rows.filter((r) => r.config?.group === g.key)
    const pooled = fromCounts(sumCounts(members.map((m) => m.sentiment)))
    return { ...g, members, pooled }
  }).filter((g) => g.members.length)

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col rounded-2xl border border-line bg-panel px-4 pt-1 pb-3 sm:hidden">
        {groups.map((group) => (
          <div key={group.key} className="flex flex-col">
            <span className="num pt-4 pb-1 text-[11px] tracking-[0.1em] text-ink3">{group.label}</span>
            {group.members.map((row) => {
              const ok = row.n >= MIN_SAMPLE
              return (
                <div key={row.platform} className="flex flex-col gap-1.5 border-b border-line py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="flex items-center gap-2.5">
                      <PlatformMark platform={row.platform} size={24} />
                      <span className="flex flex-col leading-tight">
                        <span className="text-sm font-semibold">{row.config?.name}</span>
                        <span className="text-[11px] text-ink3">
                          {formatNumber(row.n)} {unitOf(row)}
                        </span>
                      </span>
                    </span>
                    <span className="flex flex-col items-end leading-tight">
                      <span className="num text-sm">{ok ? formatSigned(row.net, 3) : "-"}</span>
                      <span className="num text-[10px] text-ink3">{ok ? formatRange(row.lo, row.hi) : "too few"}</span>
                    </span>
                  </div>
                  <div className="relative h-[18px]">
                    <div className="absolute inset-y-0 w-px bg-line2" style={{ left: `${pct(0)}%` }} />
                    {ok && (
                      <>
                        <div
                          className="absolute top-2 h-[2px] bg-ink3"
                          style={{ left: `${pct(row.lo)}%`, width: `${pct(row.hi) - pct(row.lo)}%` }}
                        />
                        <div
                          className="absolute top-[3px] -ml-1.5 h-3 w-3 rounded-full"
                          style={{
                            left: `${pct(row.net)}%`,
                            background: leanColor(row),
                            boxShadow: "0 0 0 2px var(--panel)",
                          }}
                        />
                      </>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        ))}
        <div className="num relative mt-2 h-4 text-[10px] text-ink3">
          {ticks.map((t) => (
            <span key={t} className="absolute -translate-x-1/2" style={{ left: `${pct(t)}%` }}>
              {t === 0 ? "0" : formatSigned(t, 1)}
            </span>
          ))}
        </div>
      </div>
      <div
        ref={ref}
        className="relative hidden overflow-x-auto rounded-2xl border border-line bg-panel px-6 pt-2 pb-5 sm:block"
      >
        <div className="min-w-[640px]">
          {groups.map((group) => (
            <div key={group.key}>
              <div className="grid min-h-11 grid-cols-[220px_minmax(0,1fr)_180px] items-center pt-3">
                <span className="num text-[11px] tracking-[0.1em] text-ink3">{group.label}</span>
                <span className="text-xs text-ink3">
                  {group.pooled.n >= MIN_SAMPLE
                    ? `Average ${formatSigned(group.pooled.net)} · 95% interval ${formatRange(group.pooled.lo, group.pooled.hi)} · ${formatNumber(group.pooled.n)} ${group.noun}`
                    : `${formatNumber(group.pooled.n)} ${group.noun}`}
                </span>
                <span />
              </div>
              {group.members.map((row) => {
                const ok = row.n >= MIN_SAMPLE
                const unit = unitOf(row)
                return (
                  <div
                    key={row.platform}
                    className="grid h-[52px] grid-cols-[220px_minmax(0,1fr)_180px] items-center border-t border-line"
                  >
                    <div className="flex items-center gap-3">
                      <PlatformMark platform={row.platform} size={28} />
                      <span className="flex flex-col leading-tight">
                        <span className="text-[15px] font-semibold">{row.config?.name ?? row.name}</span>
                        <span className="text-xs text-ink3">
                          {formatNumber(row.n)} {unit}
                        </span>
                      </span>
                    </div>
                    <div className="relative h-[52px]">
                      {group.pooled.n >= MIN_SAMPLE && (
                        <div
                          className="absolute inset-y-0 bg-neuw"
                          style={{
                            left: `${pct(group.pooled.lo)}%`,
                            width: `${pct(group.pooled.hi) - pct(group.pooled.lo)}%`,
                          }}
                        />
                      )}
                      {ticks.map((t) => (
                        <div
                          key={t}
                          className={`absolute inset-y-0 w-px ${t === 0 ? "bg-line2" : "bg-line"}`}
                          style={{ left: `${pct(t)}%` }}
                        />
                      ))}
                      {ok ? (
                        <button
                          type="button"
                          className="absolute inset-y-0 w-full cursor-default"
                          aria-label={`${row.config?.name}: net ${formatSigned(row.net, 3)}, 95% interval ${formatRange(row.lo, row.hi, 3)}`}
                          onPointerMove={(e) => enter(row, e)}
                          onPointerLeave={leave}
                          onFocus={(e) =>
                            enter(row, {
                              clientX: e.target.getBoundingClientRect().left + 40,
                              clientY: e.target.getBoundingClientRect().top,
                            })
                          }
                          onBlur={leave}
                        >
                          <span
                            className="absolute top-[25px] h-[2px] rounded-[1px] bg-ink3"
                            style={{ left: `${pct(row.lo)}%`, width: `${pct(row.hi) - pct(row.lo)}%` }}
                          />
                          <span className="absolute top-5 h-3 w-[2px] bg-ink3" style={{ left: `${pct(row.lo)}%` }} />
                          <span
                            className="absolute top-5 -ml-[2px] h-3 w-[2px] bg-ink3"
                            style={{ left: `${pct(row.hi)}%` }}
                          />
                          <span
                            className="absolute top-[18px] -ml-2 h-4 w-4 rounded-full"
                            style={{
                              left: `${pct(row.net)}%`,
                              background: leanColor(row),
                              boxShadow: "0 0 0 3px var(--panel)",
                            }}
                          />
                        </button>
                      ) : (
                        <span className="hatch absolute top-3.5 left-3 rounded-md border border-line2 px-2 py-[3px] text-xs text-ink2">
                          Too few to call
                        </span>
                      )}
                    </div>
                    <div className="flex flex-col items-end leading-tight">
                      <span className="num text-lg font-medium">{ok ? formatSigned(row.net, 3) : "-"}</span>
                      <span className="num text-[11px] text-ink3">
                        {ok ? formatRange(row.lo, row.hi) : `n = ${row.n}`}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          ))}
          <div className="grid grid-cols-[220px_minmax(0,1fr)_180px] border-t border-line2 pt-2.5">
            <span />
            <div className="relative h-[18px]">
              {ticks.map((t) => (
                <span
                  key={t}
                  className="num absolute -translate-x-1/2 text-[11px] text-ink3"
                  style={{ left: `${pct(t)}%` }}
                >
                  {t === 0 ? "0" : formatSigned(t, 1)}
                </span>
              ))}
            </div>
            <span />
          </div>
        </div>
        {hover && (
          <Tooltip x={hover.x} y={hover.y + 12} containerWidth={hover.width} width={260}>
            <div className="flex justify-between font-semibold">
              <span>{hover.item.config?.name}</span>
              <span className="num">{formatSigned(hover.item.net, 3)}</span>
            </div>
            <SplitBar sentiment={hover.item.sentiment} labels />
            <span className="text-xs text-ink3">
              {formatNumber(hover.item.n)} {unitOf(hover.item)} · 95% interval{" "}
              {formatRange(hover.item.lo, hover.item.hi, 3)}
            </span>
          </Tooltip>
        )}
      </div>
      <Legend>
        <LegendItem color="var(--pos)" shape="dot">
          Clearly positive
        </LegendItem>
        <LegendItem color="var(--neu)" shape="dot">
          Can&apos;t tell from neutral
        </LegendItem>
        <LegendItem color="var(--neg)" shape="dot">
          Clearly negative
        </LegendItem>
        <span className="flex items-center gap-2">
          <span className="h-3 w-5 border border-line2 bg-neuw" aria-hidden="true" />
          Group average, 95% interval
        </span>
      </Legend>
    </div>
  )
}
