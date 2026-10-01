import { formatBucket, formatNumber, formatSigned, formatTick } from "../../lib/format"
import { countsTotal, fromCounts } from "../../lib/stats"
import { useColumnHover } from "../../lib/useHover"
import { SentimentLegend } from "../ui/Legend"
import { Panel, PanelHeader } from "../ui/Panel"
import Tooltip, { TooltipRow } from "../ui/Tooltip"

const H = 280
const MID = 140
const NET_H = 110
const MIN_NET_N = 5 // buckets with fewer texts leave a gap in the net line

function niceStep(max) {
  const raw = max / 2
  const magnitude = 10 ** Math.floor(Math.log10(Math.max(1, raw)))
  return [1, 2, 5, 10].map((m) => m * magnitude).find((s) => s >= raw) ?? raw
}

function startIndex(trend, collectingSince) {
  if (!collectingSince) return 0
  const since = new Date(collectingSince).getTime()
  // The first bucket that ends after collection began.
  const next = trend.findIndex((b, i) => {
    const end = trend[i + 1] ? new Date(trend[i + 1].bucket).getTime() : Infinity
    return end > since
  })
  return Math.max(0, next)
}

/**
 * Diverging columns: positive texts rise above the line, negative fall below it, neutral sit across it.
 * Below, net sentiment per bucket with its 95% interval, on its own scale.
 */
export default function SentimentOverTime({ trend, bucket, unit, collectingSince }) {
  const n = trend.length
  const { ref, hover, handlers } = useColumnHover(n)
  const slot = 1000 / Math.max(1, n)
  const barW = Math.min(slot * 0.68, 26)
  const maxHalf = Math.max(1, ...trend.map((b) => Math.max(b.positive + b.neutral / 2, b.negative + b.neutral / 2)))
  const step = niceStep(maxHalf)
  const top = step * Math.ceil(maxHalf / step)
  const s = (MID - 6) / top
  const gap = startIndex(trend, collectingSince)
  let pos = ""
  let neu = ""
  let neg = ""
  trend.forEach((b, i) => {
    const x = (i * slot + (slot - barW) / 2).toFixed(2)
    const hu = (b.neutral / 2) * s
    if (b.neutral)
      neu += `M${x} ${(MID - hu).toFixed(2)}h${barW.toFixed(2)}V${(MID + hu).toFixed(2)}h-${barW.toFixed(2)}Z`
    if (b.positive)
      pos += `M${x} ${(MID - hu - 1.5).toFixed(2)}h${barW.toFixed(2)}v-${(b.positive * s).toFixed(2)}h-${barW.toFixed(2)}Z`
    if (b.negative)
      neg += `M${x} ${(MID + hu + 1.5).toFixed(2)}h${barW.toFixed(2)}v${(b.negative * s).toFixed(2)}h-${barW.toFixed(2)}Z`
  })
  const ny = (v) => NET_H / 2 - v * (NET_H / 2 - 4)
  const points = trend.map((b, i) => ({ i, x: i * slot + slot / 2, ...fromCounts(b) }))
  const segments = []
  let current = []
  for (const p of points) {
    if (p.n >= MIN_NET_N) current.push(p)
    else if (current.length) {
      segments.push(current)
      current = []
    }
  }
  if (current.length) segments.push(current)
  const line = segments
    .map(
      (seg) =>
        seg.map((p, k) => `${k ? "L" : "M"}${p.x.toFixed(1)} ${ny(p.net).toFixed(1)}`).join("") +
        (seg.length === 1 ? "h0.1" : ""),
    )
    .join("")
  const band = segments
    .filter((seg) => seg.length > 1)
    .map(
      (seg) =>
        seg.map((p, k) => `${k ? "L" : "M"}${p.x.toFixed(1)} ${ny(p.hi).toFixed(1)}`).join("") +
        [...seg]
          .reverse()
          .map((p) => `L${p.x.toFixed(1)} ${ny(p.lo).toFixed(1)}`)
          .join("") +
        "Z",
    )
    .join("")
  const tickEvery = Math.max(1, Math.ceil(n / 7))
  const ticks = trend.map((b, i) => ({ i, b })).filter(({ i }) => i % tickEvery === 0)
  const hovered = hover ? trend[hover.index] : null
  const hoveredNet = hovered ? fromCounts(hovered) : null

  return (
    <Panel className="flex flex-col gap-4 p-6">
      <PanelHeader
        title="Sentiment over time"
        caption="Positive texts rise above the line, negative texts fall below it, and neutral ones sit across it. Below: net sentiment with its 95% interval."
        actions={<SentimentLegend />}
      />
      <div className="grid grid-cols-[44px_minmax(0,1fr)] gap-2">
        <div className="num relative text-[11px] text-ink3" style={{ height: H }}>
          {[
            [MID - (MID - 6), top],
            [MID - top * s * 0.5, top / 2],
            [MID, 0],
            [MID + top * s * 0.5, top / 2],
            [MID + (MID - 6), top],
          ].map(([y, v], i) => (
            <span key={i} className="absolute right-0" style={{ top: y - 8 }}>
              {formatNumber(v)}
            </span>
          ))}
        </div>
        <div ref={ref} className="relative" style={{ height: H }} {...handlers}>
          {gap > 0 && (
            <div className="hatch absolute inset-y-0 left-0 rounded" style={{ width: `${(gap / n) * 100}%` }}>
              <span className="absolute top-2 left-2 text-[11px] whitespace-nowrap text-ink3">Not collecting yet</span>
            </div>
          )}
          <div className="absolute inset-x-0 h-px bg-line" style={{ top: MID - top * s * 0.5 }} />
          <div className="absolute inset-x-0 h-px bg-line" style={{ top: MID + top * s * 0.5 }} />
          {hover && (
            <div
              className="absolute inset-y-0 bg-ink/[0.06]"
              style={{ left: `${(hover.index / n) * 100}%`, width: `${100 / n}%` }}
            />
          )}
          <svg
            viewBox={`0 0 1000 ${H}`}
            preserveAspectRatio="none"
            aria-hidden="true"
            className="absolute inset-0 h-full w-full"
          >
            <path d={neu} fill="var(--neu)" />
            <path d={pos} fill="var(--pos)" />
            <path d={neg} fill="var(--neg)" />
          </svg>
          <div className="absolute inset-x-0 h-px bg-line2" style={{ top: MID }} />
          {hovered && (
            <Tooltip x={hover.x} y={Math.min(hover.y, H - 150)} containerWidth={hover.width} width={232}>
              <span className="font-semibold">
                {formatBucket(hovered.bucket, bucket)} · {formatNumber(countsTotal(hovered))} {unit}
              </span>
              <TooltipRow color="var(--pos)" label="Positive" value={hovered.positive} />
              <TooltipRow color="var(--neu)" label="Neutral" value={hovered.neutral} />
              <TooltipRow color="var(--neg)" label="Negative" value={hovered.negative} />
              <div className="flex justify-between border-t border-line pt-2 text-xs">
                <span className="text-ink2">Net sentiment</span>
                <span className="num">{hoveredNet.n ? formatSigned(hoveredNet.net) : "-"}</span>
              </div>
            </Tooltip>
          )}
        </div>
      </div>
      <div className="grid grid-cols-[44px_minmax(0,1fr)] gap-2">
        <div className="num relative text-[11px] text-ink3" style={{ height: NET_H }}>
          <span className="absolute right-0 -top-1">+1</span>
          <span className="absolute right-0" style={{ top: NET_H / 2 - 8 }}>
            0
          </span>
          <span className="absolute right-0 -bottom-1">{"−"}1</span>
        </div>
        <div className="relative border-t border-line" style={{ height: NET_H }}>
          {gap > 0 && (
            <div className="hatch absolute inset-y-0 left-0 rounded" style={{ width: `${(gap / n) * 100}%` }} />
          )}
          <div className="absolute inset-x-0 h-px bg-line2" style={{ top: NET_H / 2 }} />
          <svg
            viewBox={`0 0 1000 ${NET_H}`}
            preserveAspectRatio="none"
            aria-hidden="true"
            className="absolute inset-0 h-full w-full overflow-visible"
          >
            <path d={band} fill="var(--ink3)" fillOpacity="0.18" />
            <path
              d={line}
              fill="none"
              stroke="var(--ink)"
              strokeWidth="2"
              vectorEffect="non-scaling-stroke"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </svg>
          {!segments.length && (
            <span className="absolute inset-0 flex items-center justify-center text-xs text-ink3">
              Too few {unit} per {bucket} for a net sentiment line
            </span>
          )}
        </div>
      </div>
      <div className="grid grid-cols-[44px_minmax(0,1fr)] gap-2">
        <span />
        <div className="num relative h-4 text-[11px] text-ink3">
          {ticks.map(({ i, b }) => (
            <span
              key={b.bucket}
              className="absolute -translate-x-1/2 whitespace-nowrap"
              style={{ left: `${((i + 0.5) / n) * 100}%` }}
            >
              {formatTick(b.bucket, bucket)}
            </span>
          ))}
        </div>
      </div>
    </Panel>
  )
}
