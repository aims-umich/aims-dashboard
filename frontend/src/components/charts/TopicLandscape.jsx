import { formatNumber, formatPercent, formatSigned } from "../../lib/format"
import { divergingColor } from "../../lib/stats"
import { placeLabels, useMarkHover, useWidth } from "../../lib/useHover"
import { Panel, PanelHeader } from "../ui/Panel"
import SplitBar from "../ui/SplitBar"
import Tooltip from "../ui/Tooltip"

const H = 460
const MIN_N = 20

/** Every topic by its share of texts (x) and net sentiment (y); dot size is the number of texts. */
export default function TopicLandscape({ topics, texts, onSelect, selected }) {
  const { ref, hover, enter, leave } = useMarkHover()
  const [sizeRef, width] = useWidth()
  const shown = topics.filter((t) => t.count >= MIN_N)
  const maxShare = Math.max(0.05, ...shown.map((t) => t.share ?? 0))
  const xMax = Math.ceil(maxShare * 20 + 0.5) / 20
  const lo = Math.min(-0.4, Math.floor(Math.min(0, ...shown.map((t) => t.net_sentiment)) * 5 - 0.5) / 5)
  const hi = Math.max(0.2, Math.ceil(Math.max(0, ...shown.map((t) => t.net_sentiment)) * 5 + 0.5) / 5)
  const x = (v) => (v / xMax) * 100
  const y = (v) => ((hi - v) / (hi - lo)) * 100
  const maxN = Math.max(1, ...shown.map((t) => t.count))
  const dots = shown.map((t) => ({
    id: t.id,
    label: t.name,
    r: Math.round(18 + Math.sqrt(t.count / maxN) * 40) / 2,
    x: (x(t.share) / 100) * width,
    y: (y(t.net_sentiment) / 100) * H,
  }))
  const labels = width ? placeLabels(dots, { width, height: H }) : {}
  const someUnlabeled = width > 0 && dots.some((d) => !labels[d.id])
  const yTicks = []
  for (let v = hi; v >= lo - 1e-9; v -= 0.2) yTicks.push(Math.round(v * 10) / 10)
  const xTicks = []
  for (let v = 0; v <= xMax + 1e-9; v += xMax > 0.3 ? 0.1 : 0.05) xTicks.push(Math.round(v * 100) / 100)
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        title="Topic landscape"
        caption={`Share of texts against net sentiment. Dot size is the number of texts. Topics with fewer than ${MIN_N} texts are left out.${someUnlabeled ? " Unlabeled dots show their name on hover or tap." : ""}`}
        actions={<span className="num text-xs text-ink3">{formatNumber(texts)} SCORED TEXTS</span>}
      />
      <div className="grid grid-cols-[52px_minmax(0,1fr)] gap-2">
        <div className="num relative text-[11px] text-ink3" style={{ height: H }}>
          {yTicks.map((v) => (
            <span key={v} className="absolute right-0" style={{ top: `calc(${y(v)}% - 8px)` }}>
              {v === 0 ? "0" : formatSigned(v, 1)}
            </span>
          ))}
        </div>
        <div
          ref={(el) => {
            ref.current = el
            sizeRef.current = el
          }}
          className="relative border-b border-l border-line2"
          style={{ height: H }}
          onPointerLeave={leave}
        >
          <div className="absolute inset-x-0 top-0 bg-posw opacity-40" style={{ height: `${y(0)}%` }} />
          <div className="absolute inset-x-0 bottom-0 bg-negw opacity-40" style={{ top: `${y(0)}%` }} />
          {yTicks.map((v) => (
            <div
              key={v}
              className={`absolute inset-x-0 h-px ${v === 0 ? "bg-line2" : "bg-line"}`}
              style={{ top: `${y(v)}%` }}
            />
          ))}
          <span className="num absolute top-3 left-3.5 hidden text-[11px] tracking-[0.08em] text-ink3 sm:inline">
            NICHE AND WARM
          </span>
          <span className="num absolute top-3 right-3.5 hidden text-[11px] tracking-[0.08em] text-ink3 sm:inline">
            BIG AND WARM
          </span>
          <span className="num absolute bottom-3 left-3.5 hidden text-[11px] tracking-[0.08em] text-ink3 sm:inline">
            NICHE AND CRITICAL
          </span>
          <span className="num absolute right-3.5 bottom-3 hidden text-[11px] tracking-[0.08em] text-ink3 sm:inline">
            BIG AND CRITICAL
          </span>
          <svg className="pointer-events-none absolute inset-0 h-full w-full overflow-visible" aria-hidden="true">
            {dots.map((dot) => {
              const label = labels[dot.id]
              if (!label || !label.dy) return null
              const lx = label.side === "right" ? label.x - 3 : label.x + label.w + 3
              const ly = label.y + label.h / 2
              const len = Math.hypot(lx - dot.x, ly - dot.y) || 1
              const sx = dot.x + ((lx - dot.x) / len) * (dot.r + 2)
              const sy = dot.y + ((ly - dot.y) / len) * (dot.r + 2)
              return <line key={dot.id} x1={sx} y1={sy} x2={lx} y2={ly} stroke="var(--ink3)" strokeWidth="1" />
            })}
          </svg>
          {shown.map((t) => {
            const d = Math.round(18 + Math.sqrt(t.count / maxN) * 40)
            const label = labels[t.id]
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => onSelect(t.id)}
                onPointerEnter={(e) => enter(t, e)}
                aria-label={`${t.name}: ${formatPercent(t.share, 1)} of texts, net ${formatSigned(t.net_sentiment)}`}
                className="absolute"
                style={{ left: `${x(t.share)}%`, top: `${y(t.net_sentiment)}%` }}
                onFocus={(e) =>
                  enter(t, {
                    clientX: e.currentTarget.getBoundingClientRect().left,
                    clientY: e.currentTarget.getBoundingClientRect().top,
                  })
                }
                onBlur={leave}
              >
                <span
                  className="absolute rounded-full"
                  style={{
                    width: d,
                    height: d,
                    left: -d / 2,
                    top: -d / 2,
                    background: divergingColor(t.net_sentiment),
                    boxShadow:
                      selected === t.id ? "0 0 0 2px var(--panel), 0 0 0 4px var(--glow)" : "0 0 0 2px var(--panel)",
                  }}
                />
                {label && (
                  <span
                    className="absolute text-[13px] leading-[18px] font-semibold whitespace-nowrap text-ink"
                    style={{
                      left: label.x - dots.find((p) => p.id === t.id).x,
                      top: label.y - dots.find((p) => p.id === t.id).y,
                      textShadow: "0 0 6px var(--panel), 0 0 2px var(--panel)",
                    }}
                  >
                    {t.name}
                  </span>
                )}
              </button>
            )
          })}
          {hover && (
            <Tooltip x={hover.x} y={hover.y + 12} containerWidth={hover.width} width={250}>
              <span className="font-semibold">{hover.item.name}</span>
              <SplitBar sentiment={hover.item.sentiment} labels />
              <span className="text-xs text-ink3">
                {formatNumber(hover.item.count)} texts · {formatPercent(hover.item.share, 1)} of all · net{" "}
                {formatSigned(hover.item.net_sentiment)}
              </span>
            </Tooltip>
          )}
        </div>
      </div>
      <div className="grid grid-cols-[52px_minmax(0,1fr)] gap-2">
        <span />
        <div className="num relative h-4 text-[11px] text-ink3">
          {xTicks.map((v) => (
            <span key={v} className="absolute -translate-x-1/2" style={{ left: `${x(v)}%` }}>
              {Math.round(v * 100)}%
            </span>
          ))}
        </div>
      </div>
    </Panel>
  )
}
