import { formatMonth, formatNumber, formatSigned } from "../../lib/format"
import { PLATFORMS } from "../../lib/platforms"
import { rollingNet, sumCounts } from "../../lib/stats"
import { useColumnHover } from "../../lib/useHover"
import { Legend, LegendItem } from "../ui/Legend"
import { Panel, PanelHeader } from "../ui/Panel"
import Tooltip, { TooltipRow } from "../ui/Tooltip"

const H = 300
const MIN_N = 10
const DOMAIN = [-0.6, 0.6]

function pooled(series, group, months) {
  const members = Object.entries(series).filter(([key]) => PLATFORMS[key]?.group === group)
  const byMonth = members.map(([, rows]) => Object.fromEntries(rows.map((r) => [r.bucket, r])))
  return months.map((m) => sumCounts(byMonth.map((rows) => rows[m])))
}

function path(points, x, y) {
  let d = ""
  let open = false
  points.forEach((p, i) => {
    if (p == null) {
      open = false
      return
    }
    d += `${open ? "L" : "M"}${x(i).toFixed(1)} ${y(p).toFixed(1)}`
    open = true
  })
  return d
}

/** Social platforms pooled against newspapers pooled, month by month, three-month rolling. */
export default function SocialVsNews({ series, months: count = 36 }) {
  const all = new Set()
  Object.values(series).forEach((rows) => rows.forEach((r) => all.add(r.bucket)))
  const months = [...all].sort().slice(-count)
  const social = rollingNet(pooled(series, "social", months), 3)
  const news = rollingNet(pooled(series, "news", months), 3)
  const s = social.map((p) => (p.n >= MIN_N ? p.net : null))
  const n = news.map((p) => (p.n >= MIN_N ? p.net : null))
  const N = months.length
  const x = (i) => (N > 1 ? (i / (N - 1)) * 1000 : 500)
  const y = (v) => ((DOMAIN[1] - Math.max(DOMAIN[0], Math.min(DOMAIN[1], v))) / (DOMAIN[1] - DOMAIN[0])) * H
  let fill = ""
  let run = []
  const flush = () => {
    if (run.length > 1)
      fill += `M${run.map((i) => `${x(i).toFixed(1)} ${y(s[i]).toFixed(1)}`).join("L")}L${[...run]
        .reverse()
        .map((i) => `${x(i).toFixed(1)} ${y(n[i]).toFixed(1)}`)
        .join("L")}Z`
    run = []
  }
  months.forEach((_, i) => (s[i] != null && n[i] != null ? run.push(i) : flush()))
  flush()
  const lowRuns = []
  let start = null
  s.forEach((v, i) => {
    if (v == null && start == null) start = i
    if ((v != null || i === N - 1) && start != null) {
      lowRuns.push([start, v == null ? i : i - 1])
      start = null
    }
  })
  const { ref, hover, handlers } = useColumnHover(N)
  const lastS = [...s].reverse().find((v) => v != null)
  const lastN = [...n].reverse().find((v) => v != null)
  const every = Math.max(1, Math.ceil(N / 6))
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        title="Social platforms and newspapers"
        caption="Net sentiment by month, three-month rolling. Social platforms pooled against newspapers pooled. The shaded area is the difference."
        actions={
          <Legend>
            <LegendItem color="var(--ink)" shape="line">
              Social platforms
            </LegendItem>
            <span className="flex items-center gap-2">
              <span className="w-5 border-t-2 border-dashed border-ink2" aria-hidden="true" />
              Newspapers
            </span>
            <LegendItem hatch>Under {MIN_N} texts</LegendItem>
          </Legend>
        }
      />
      <div className="grid grid-cols-[44px_minmax(0,1fr)_110px] gap-2">
        <div className="num relative text-[11px] text-ink3" style={{ height: H }}>
          {[0.6, 0.3, 0, -0.3, -0.6].map((v) => (
            <span key={v} className="absolute right-0" style={{ top: y(v) - 8 }}>
              {v === 0 ? "0" : formatSigned(v, 1)}
            </span>
          ))}
        </div>
        <div ref={ref} className="relative" style={{ height: H }} {...handlers}>
          {lowRuns.map(([a, b]) => (
            <div
              key={a}
              className="hatch absolute inset-y-0"
              style={{ left: `${x(a) / 10 - 50 / N}%`, width: `${(x(b) - x(a)) / 10 + 100 / N}%` }}
            />
          ))}
          {[0.6, 0.3, -0.3, -0.6].map((v) => (
            <div key={v} className="absolute inset-x-0 h-px bg-line" style={{ top: y(v) }} />
          ))}
          <div className="absolute inset-x-0 h-px bg-line2" style={{ top: y(0) }} />
          <svg
            viewBox={`0 0 1000 ${H}`}
            preserveAspectRatio="none"
            aria-hidden="true"
            className="absolute inset-0 h-full w-full overflow-visible"
          >
            <path d={fill} fill="var(--neuw)" />
            <path
              d={path(n, x, y)}
              fill="none"
              stroke="var(--ink2)"
              strokeWidth="2"
              strokeDasharray="6 5"
              vectorEffect="non-scaling-stroke"
              strokeLinejoin="round"
            />
            <path
              d={path(s, x, y)}
              fill="none"
              stroke="var(--ink)"
              strokeWidth="2.4"
              vectorEffect="non-scaling-stroke"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </svg>
          {hover && (
            <>
              <div className="absolute inset-y-0 w-px bg-ink3" style={{ left: `${x(hover.index) / 10}%` }} />
              <Tooltip x={hover.x} y={20} containerWidth={hover.width} width={220}>
                <span className="font-semibold">{formatMonth(months[hover.index])}</span>
                <TooltipRow
                  label={`Social (${formatNumber(social[hover.index].n)})`}
                  value={s[hover.index] == null ? "too few" : formatSigned(s[hover.index])}
                />
                <TooltipRow
                  label={`News (${formatNumber(news[hover.index].n)})`}
                  value={n[hover.index] == null ? "too few" : formatSigned(n[hover.index])}
                />
              </Tooltip>
            </>
          )}
        </div>
        <div className="relative text-xs leading-tight" style={{ height: H }}>
          {lastS != null && (
            <span className="absolute left-0 text-ink" style={{ top: y(lastS) - 8 }}>
              Social <span className="num">{formatSigned(lastS)}</span>
            </span>
          )}
          {lastN != null && (
            <span
              className="absolute left-0 text-ink2"
              style={{ top: y(lastN) - 8 + (lastS != null && Math.abs(y(lastS) - y(lastN)) < 18 ? 18 : 0) }}
            >
              News <span className="num">{formatSigned(lastN)}</span>
            </span>
          )}
        </div>
      </div>
      <div className="grid grid-cols-[44px_minmax(0,1fr)_110px] gap-2">
        <span />
        <div className="num relative h-4 text-[11px] text-ink3">
          {months.map((m, i) =>
            i % every === 0 || i === N - 1 ? (
              <span key={m} className="absolute -translate-x-1/2 whitespace-nowrap" style={{ left: `${x(i) / 10}%` }}>
                {formatMonth(m, { short: true })}
              </span>
            ) : null,
          )}
        </div>
      </div>
    </Panel>
  )
}
