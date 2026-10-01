import { formatBucket, formatNumber, formatTick } from "../../lib/format"
import { useColumnHover } from "../../lib/useHover"
import { Panel, PanelHeader } from "../ui/Panel"
import Tooltip, { TooltipRow } from "../ui/Tooltip"

const H = 220

/** Documents per bucket as columns, for sources without engagement (the newspapers). */
export default function VolumeOverTime({ trend, bucket, title, noun }) {
  const n = trend.length
  const { ref, hover, handlers } = useColumnHover(n)
  const max = Math.max(1, ...trend.map((b) => b.documents))
  const slot = 1000 / Math.max(1, n)
  const w = Math.min(slot * 0.68, 26)
  const path = trend
    .map((b, i) =>
      b.documents
        ? `M${(i * slot + (slot - w) / 2).toFixed(2)} ${H}h${w.toFixed(2)}v-${((b.documents / max) * (H - 8)).toFixed(2)}h-${w.toFixed(2)}Z`
        : "",
    )
    .join("")
  const every = Math.max(1, Math.ceil(n / 6))
  const hovered = hover ? trend[hover.index] : null
  return (
    <Panel className="flex flex-col gap-4 p-6">
      <PanelHeader title={title} caption={`${noun[0].toUpperCase()}${noun.slice(1)} published per ${bucket}.`} />
      <div className="grid grid-cols-[36px_minmax(0,1fr)] gap-2">
        <div className="num relative text-[11px] text-ink3" style={{ height: H }}>
          <span className="absolute right-0 top-0">{formatNumber(max)}</span>
          <span className="absolute right-0 bottom-0">0</span>
        </div>
        <div ref={ref} className="relative border-b border-line2" style={{ height: H }} {...handlers}>
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
            <path d={path} fill="var(--ink3)" />
          </svg>
          {hovered && (
            <Tooltip x={hover.x} y={20} containerWidth={hover.width} width={200}>
              <span className="font-semibold">{formatBucket(hovered.bucket, bucket)}</span>
              <TooltipRow label={noun} value={formatNumber(hovered.documents)} />
            </Tooltip>
          )}
        </div>
      </div>
      <div className="grid grid-cols-[36px_minmax(0,1fr)] gap-2">
        <span />
        <div className="num relative h-4 text-[11px] text-ink3">
          {trend.map((b, i) =>
            i % every === 0 ? (
              <span
                key={b.bucket}
                className="absolute -translate-x-1/2 whitespace-nowrap"
                style={{ left: `${((i + 0.5) / n) * 100}%` }}
              >
                {formatTick(b.bucket, bucket)}
              </span>
            ) : null,
          )}
        </div>
      </div>
    </Panel>
  )
}
