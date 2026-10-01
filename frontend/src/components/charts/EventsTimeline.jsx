import { formatMonth, formatNumber, formatSigned } from "../../lib/format"
import { countsTotal, fromCounts, rollingNet } from "../../lib/stats"
import { useColumnHover } from "../../lib/useHover"
import { Panel, PanelHeader } from "../ui/Panel"
import Tooltip, { TooltipRow } from "../ui/Tooltip"

const H = 340
const VOL_H = 70

/** Pin rows so numbered markers that would touch are stacked instead. */
function pinRows(events, N, width) {
  const rows = []
  const lastX = []
  for (const e of events) {
    const px = ((e.index + 0.5) / N) * width
    let row = 0
    while (lastX[row] != null && px - lastX[row] < 30) row += 1
    lastX[row] = px
    rows.push(row)
  }
  return rows
}

/** Net sentiment per month for one source: dots sized by volume, a three-month line, listed events pinned. */
export default function EventsTimeline({ months, events, noun, width = 1200 }) {
  const N = months.length
  const { ref, hover, handlers } = useColumnHover(N)
  const x = (i) => ((i + 0.5) / N) * 100
  const y = (v) => ((1 - v) / 2) * H
  const maxN = Math.max(1, ...months.map(countsTotal))
  const rolled = rollingNet(months, 3)
  let line = ""
  let open = false
  rolled.forEach((p, i) => {
    if (p.n < 5) {
      open = false
      return
    }
    line += `${open ? "L" : "M"}${(x(i) * 10).toFixed(1)} ${y(p.net).toFixed(1)}`
    open = true
  })
  const slot = 1000 / N
  const bw = Math.min(slot * 0.7, 18)
  const vol = months
    .map((m, i) => {
      const n = countsTotal(m)
      return n
        ? `M${(i * slot + (slot - bw) / 2).toFixed(1)} ${VOL_H}h${bw.toFixed(1)}v-${((n / maxN) * (VOL_H - 4)).toFixed(1)}h-${bw.toFixed(1)}Z`
        : ""
    })
    .join("")
  const pinned = events
    .map((e) => ({ ...e, index: months.findIndex((m) => m.month === e.month) }))
    .filter((e) => e.index >= 0)
  const rows = pinRows(pinned, N, width)
  const pinHeight = 30 * (Math.max(0, ...rows) + 1) + 6
  const years = months.map((m, i) => ({ i, m })).filter(({ m }) => m.month.endsWith("-01"))
  const hovered = hover ? months[hover.index] : null
  const hoveredEvent = hovered ? pinned.find((e) => e.month === hovered.month) : null
  return (
    <Panel className="flex flex-col gap-4 p-6">
      <PanelHeader
        title="Net sentiment, month by month"
        caption="Dots are single months, sized by how many texts they hold. The line is a three-month rolling average. Numbered pins mark listed events."
        actions={
          <span className="num text-xs text-ink3">
            {formatNumber(months.reduce((a, m) => a + countsTotal(m), 0))} {noun.toUpperCase()}
          </span>
        }
      />
      <div className="grid grid-cols-[44px_minmax(0,1fr)] gap-2">
        <span />
        <div className="relative" style={{ height: pinHeight }}>
          {pinned.map((e, k) => (
            <span key={e.number}>
              <span
                className="absolute w-px bg-ink3 opacity-45"
                style={{ left: `${x(e.index)}%`, top: 4 + rows[k] * 30 + 26, bottom: 0 }}
              />
              <span
                className="num absolute -ml-[13px] flex h-[26px] w-[26px] items-center justify-center rounded-full border border-line2 text-[11px] font-semibold"
                style={{
                  left: `${x(e.index)}%`,
                  top: 4 + rows[k] * 30,
                  background: e.verdict === "shift" ? "var(--ink)" : "var(--panel2)",
                  color: e.verdict === "shift" ? "var(--bg)" : "var(--ink2)",
                }}
                title={e.title}
              >
                {e.number}
              </span>
            </span>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-[44px_minmax(0,1fr)] gap-2">
        <div className="num relative text-[11px] text-ink3" style={{ height: H }}>
          {[1, 0.5, 0, -0.5, -1].map((v) => (
            <span key={v} className="absolute right-0" style={{ top: y(v) - 7 }}>
              {v === 0 ? "0" : formatSigned(v, v % 1 ? 1 : 0)}
            </span>
          ))}
        </div>
        <div ref={ref} className="relative" style={{ height: H }} {...handlers}>
          <div className="absolute inset-x-0 top-0 bg-posw opacity-30" style={{ height: H / 2 }} />
          <div className="absolute inset-x-0 bottom-0 bg-negw opacity-30" style={{ height: H / 2 }} />
          {[0.5, -0.5].map((v) => (
            <div key={v} className="absolute inset-x-0 h-px bg-line" style={{ top: y(v) }} />
          ))}
          <div className="absolute inset-x-0 h-px bg-line2" style={{ top: H / 2 }} />
          {pinned.map((e) => (
            <div
              key={e.number}
              className="absolute inset-y-0 w-px bg-ink3 opacity-45"
              style={{ left: `${x(e.index)}%` }}
            />
          ))}
          {months.map((m, i) => {
            const n = countsTotal(m)
            if (!n) return null
            const { net } = fromCounts(m)
            const size = Math.round(5 + Math.sqrt(n / maxN) * 17)
            return (
              <span
                key={m.month}
                className="absolute rounded-full opacity-85"
                style={{
                  left: `${x(i)}%`,
                  top: y(net),
                  width: size,
                  height: size,
                  marginLeft: -size / 2,
                  marginTop: -size / 2,
                  background: net > 0.05 ? "var(--pos)" : net < -0.05 ? "var(--neg)" : "var(--neu)",
                  boxShadow: "0 0 0 2px var(--panel)",
                }}
              />
            )
          })}
          <svg
            viewBox={`0 0 1000 ${H}`}
            preserveAspectRatio="none"
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 h-full w-full"
          >
            <path
              d={line}
              fill="none"
              stroke="var(--ink)"
              strokeWidth="2.2"
              vectorEffect="non-scaling-stroke"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </svg>
          {hovered && (
            <>
              <div
                className="pointer-events-none absolute inset-y-0 w-px bg-ink2"
                style={{ left: `${x(hover.index)}%` }}
              />
              <Tooltip x={hover.x} y={20} containerWidth={hover.width} width={250}>
                <span className="font-semibold">{formatMonth(hovered.month)}</span>
                {hoveredEvent && (
                  <span className="text-xs text-ink2">
                    {hoveredEvent.number}. {hoveredEvent.title}
                  </span>
                )}
                <TooltipRow label={noun} value={formatNumber(countsTotal(hovered))} />
                <TooltipRow
                  label="Net that month"
                  value={countsTotal(hovered) ? formatSigned(fromCounts(hovered).net) : "-"}
                />
                <TooltipRow
                  label="Three-month net"
                  value={rolled[hover.index].n >= 5 ? formatSigned(rolled[hover.index].net) : "too few"}
                />
              </Tooltip>
            </>
          )}
        </div>
      </div>
      <div className="grid grid-cols-[44px_minmax(0,1fr)] gap-2">
        <div className="num relative text-[11px] text-ink3" style={{ height: VOL_H }}>
          <span className="absolute right-0 -top-0.5">{formatNumber(maxN)}</span>
          <span className="absolute right-0 -bottom-1">0</span>
        </div>
        <div className="relative border-b border-line2" style={{ height: VOL_H }}>
          <svg
            viewBox={`0 0 1000 ${VOL_H}`}
            preserveAspectRatio="none"
            aria-hidden="true"
            className="absolute inset-0 h-full w-full"
          >
            <path d={vol} fill="var(--ink3)" fillOpacity="0.7" />
          </svg>
          <span className="absolute top-0 left-1.5 text-[11px] text-ink3">
            {noun[0].toUpperCase() + noun.slice(1)} per month
          </span>
        </div>
      </div>
      <div className="grid grid-cols-[44px_minmax(0,1fr)] gap-2">
        <span />
        <div className="num relative h-4 text-[11px] text-ink3">
          {years.map(({ i, m }) => (
            <span key={m.month} className="absolute -translate-x-1/2" style={{ left: `${x(i)}%` }}>
              {m.month.slice(0, 4)}
            </span>
          ))}
        </div>
      </div>
    </Panel>
  )
}
