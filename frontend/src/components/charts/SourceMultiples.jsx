import { formatDate, formatMonth, formatNumber, formatSigned } from "../../lib/format"
import { PLATFORMS } from "../../lib/platforms"
import { countsTotal, rollingNet } from "../../lib/stats"
import { useColumnHover } from "../../lib/useHover"
import { Panel } from "../ui/Panel"
import Tooltip, { TooltipRow } from "../ui/Tooltip"

const H = 120
const LIMIT = 0.8
const MIN_N = 8

function Multiple({ platform, rows, months, collectingSince }) {
  const config = PLATFORMS[platform]
  const byMonth = Object.fromEntries(rows.map((r) => [r.bucket, r]))
  const aligned = months.map((m) => byMonth[m] ?? { positive: 0, neutral: 0, negative: 0 })
  const rolled = rollingNet(aligned, 3)
  const values = rolled.map((p) => (p.n >= MIN_N ? p.net : null))
  const N = months.length
  const x = (i) => ((i + 0.5) / N) * 1000
  const y = (v) => H / 2 - (Math.max(-LIMIT, Math.min(LIMIT, v)) / LIMIT) * (H / 2 - 6)
  const segs = []
  let cur = []
  values.forEach((v, i) => {
    if (v == null) {
      if (cur.length) segs.push(cur)
      cur = []
    } else cur.push(i)
  })
  if (cur.length) segs.push(cur)
  const line = segs
    .map(
      (seg) =>
        seg.map((i, k) => `${k ? "L" : "M"}${x(i).toFixed(1)} ${y(values[i]).toFixed(1)}`).join("") +
        (seg.length === 1 ? "h0.1" : ""),
    )
    .join("")
  const area = (sign) =>
    segs
      .filter((seg) => seg.length > 1)
      .map((seg) => {
        const pts = seg.map(
          (i) => `${x(i).toFixed(1)} ${y(sign > 0 ? Math.max(0, values[i]) : Math.min(0, values[i])).toFixed(1)}`,
        )
        return `M${x(seg[0]).toFixed(1)} ${H / 2}L${pts.join("L")}L${x(seg[seg.length - 1]).toFixed(1)} ${H / 2}Z`
      })
      .join("")
  const total = rows.reduce((a, r) => a + countsTotal(r), 0)
  const latest = [...values].reverse().find((v) => v != null)
  const fewMonths = rows.filter((r) => countsTotal(r) > 0).length < 3
  const { ref, hover, handlers } = useColumnHover(N)
  return (
    <Panel className="flex flex-col gap-3 p-5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[15px] font-[650]">{config?.name ?? platform}</span>
        <span className="text-xs text-ink3">
          {formatNumber(total)} {config?.unitLabel} {latest != null ? `· now ${formatSigned(latest)}` : ""}
        </span>
      </div>
      <div ref={ref} className="relative rounded-md bg-panel2" style={{ height: H }} {...handlers}>
        <div className="absolute inset-x-0 h-px bg-line2" style={{ top: H / 2 }} />
        <svg
          viewBox={`0 0 1000 ${H}`}
          preserveAspectRatio="none"
          aria-hidden="true"
          className="absolute inset-0 h-full w-full"
        >
          <path d={area(1)} fill="var(--posw)" />
          <path d={area(-1)} fill="var(--negw)" />
          <path
            d={line}
            fill="none"
            stroke="var(--ink)"
            strokeWidth="1.6"
            vectorEffect="non-scaling-stroke"
            strokeLinejoin="round"
          />
        </svg>
        {fewMonths && (
          <div className="hatch absolute inset-0 flex items-center justify-center rounded-md text-xs text-ink2">
            {collectingSince ? `Collecting since ${formatDate(collectingSince)}` : "Not enough history yet"}
          </div>
        )}
        {hover && !fewMonths && (
          <>
            <div className="absolute inset-y-0 w-px bg-ink3" style={{ left: `${x(hover.index) / 10}%` }} />
            <Tooltip x={hover.x} y={8} containerWidth={hover.width} width={190}>
              <span className="font-semibold">{formatMonth(months[hover.index])}</span>
              <TooltipRow
                label="Three-month net"
                value={values[hover.index] == null ? "too few" : formatSigned(values[hover.index])}
              />
              <TooltipRow label="Texts that month" value={formatNumber(countsTotal(aligned[hover.index]))} />
            </Tooltip>
          </>
        )}
      </div>
    </Panel>
  )
}

/** Net sentiment per source over the same months and the same scale. */
export default function SourceMultiples({ series, firstSeen, months: count = 72 }) {
  const all = new Set()
  Object.values(series).forEach((rows) => rows.forEach((r) => all.add(r.bucket)))
  const months = [...all].sort().slice(-count)
  const years = [...new Set(months.map((m) => m.slice(0, 4)))]
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(380px,100%),1fr))] gap-4">
        {Object.entries(series).map(([key, rows]) => (
          <Multiple key={key} platform={key} rows={rows} months={months} collectingSince={firstSeen?.[key]} />
        ))}
      </div>
      <div className="num flex justify-between text-[11px] text-ink3">
        <span>{months[0] ? formatMonth(months[0]) : ""}</span>
        <span>{years.length > 2 ? `${years.length} years, shared scale ${"−"}0.8 to +0.8` : ""}</span>
        <span>{months.length ? formatMonth(months[months.length - 1]) : ""}</span>
      </div>
    </div>
  )
}
