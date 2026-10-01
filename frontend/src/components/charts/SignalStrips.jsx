import { formatNumber } from "../../lib/format"
import { PLATFORMS } from "../../lib/platforms"
import { LABEL_KEYS } from "../../lib/sentiment"
import { useColumnHover } from "../../lib/useHover"
import { Legend, LegendItem } from "../ui/Legend"
import Tooltip, { TooltipRow } from "../ui/Tooltip"

const BINS = 48 // half-hour hover windows
const COLORS = ["var(--neg)", "var(--neu)", "var(--pos)"]
const LOW_CONFIDENCE = 70

function hhmm(seconds) {
  const d = new Date(seconds * 1000)
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`
}

function Strip({ row, since, until, unit }) {
  const span = until - since
  const x = (t) => ((t - since) / span) * 1000
  const paths = { 0: ["", ""], 1: ["", ""], 2: ["", ""] }
  for (const [t, label, confidence] of row.items) {
    paths[label][confidence < LOW_CONFIDENCE ? 1 : 0] += `M${x(t).toFixed(1)} 0V40`
  }
  const startedAt = row.collecting_since ? new Date(row.collecting_since).getTime() / 1000 : since
  const gap = Math.max(0, Math.min(1, (startedAt - since) / span))
  const { ref, hover, handlers } = useColumnHover(BINS)
  let bin = null
  if (hover) {
    const from = since + (hover.index / BINS) * span
    const to = since + ((hover.index + 1) / BINS) * span
    const counts = [0, 0, 0]
    for (const [t, label] of row.items) if (t >= from && t < to) counts[label] += 1
    bin = { from, to, counts }
  }
  return (
    <div ref={ref} className="relative h-11" {...handlers}>
      <div className="absolute inset-0 overflow-hidden rounded-md bg-panel2">
        {gap > 0 && <div className="hatch absolute inset-y-0 left-0" style={{ width: `${gap * 100}%` }} />}
        <svg
          viewBox="0 0 1000 40"
          preserveAspectRatio="none"
          aria-hidden="true"
          className="absolute inset-x-0 top-0.5 h-10 w-full"
        >
          {[1, 0, 2].map((label) => (
            <g key={label}>
              <path
                d={paths[label][1]}
                stroke={COLORS[label]}
                strokeOpacity="0.4"
                strokeWidth="1.3"
                vectorEffect="non-scaling-stroke"
              />
              <path d={paths[label][0]} stroke={COLORS[label]} strokeWidth="1.3" vectorEffect="non-scaling-stroke" />
            </g>
          ))}
        </svg>
        {row.count === 0 && (
          <span className="absolute inset-0 flex items-center px-4 text-[13px] text-ink3">
            No new {unit} in the last 24 hours
          </span>
        )}
        {hover && (
          <div
            className="pointer-events-none absolute inset-y-0 bg-ink/10"
            style={{ left: `${(hover.index / BINS) * 100}%`, width: `${100 / BINS}%` }}
          />
        )}
      </div>
      {bin && (
        <Tooltip x={hover.x} y={50} containerWidth={hover.width} width={200}>
          <span className="font-semibold">
            {hhmm(bin.from)} to {hhmm(bin.to)} UTC
          </span>
          {[2, 1, 0].map((label) => (
            <TooltipRow
              key={label}
              color={COLORS[label]}
              label={LABEL_KEYS[label][0].toUpperCase() + LABEL_KEYS[label].slice(1)}
              value={bin.counts[label]}
            />
          ))}
        </Tooltip>
      )}
    </div>
  )
}

/** One tick per scored text of the last 24 hours, placed at the moment it was published. */
export default function SignalStrips({ data }) {
  const since = new Date(data.since).getTime() / 1000
  const until = new Date(data.until).getTime() / 1000
  const ticks = [0, 6, 12, 18, 24].map((h) => since + h * 3600)
  return (
    <div className="flex flex-col gap-6">
      <Legend>
        <LegendItem color="var(--pos)" shape="tick">
          Positive
        </LegendItem>
        <LegendItem color="var(--neu)" shape="tick">
          Neutral
        </LegendItem>
        <LegendItem color="var(--neg)" shape="tick">
          Negative
        </LegendItem>
        <span className="flex items-center gap-2">
          <span className="h-3.5 w-[3px] bg-ink3 opacity-40" aria-hidden="true" />
          Confidence under 70%
        </span>
        <LegendItem hatch>Not collecting yet</LegendItem>
      </Legend>
      <div className="flex flex-col gap-2.5 rounded-2xl border border-line bg-panel px-6 py-5">
        {data.platforms.map((row) => {
          const config = PLATFORMS[row.platform]
          const unit = config?.unitLabel ?? "texts"
          return (
            <div
              key={row.platform}
              className="grid grid-cols-1 items-center gap-2 sm:grid-cols-[196px_minmax(0,1fr)] sm:gap-6"
            >
              <div className="flex items-baseline justify-between gap-3 leading-tight sm:flex-col sm:items-start sm:gap-0.5">
                <span className="text-[15px] font-semibold">{config?.name ?? row.platform}</span>
                <span className="num text-xs text-ink3">
                  {formatNumber(row.count)} {row.count === 1 ? config?.unitSingular : unit}
                </span>
              </div>
              <Strip row={row} since={since} until={until} unit={unit} />
            </div>
          )
        })}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-[196px_minmax(0,1fr)]">
          <span className="hidden sm:block" />
          <div className="num flex justify-between text-[11px] text-ink3">
            {ticks.map((t, i) => (
              <span key={t}>{i === ticks.length - 1 ? `Now ${hhmm(t)} UTC` : hhmm(t)}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
