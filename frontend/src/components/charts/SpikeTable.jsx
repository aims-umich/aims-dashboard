import { formatMonth, formatSigned } from "../../lib/format"
import { PLATFORMS } from "../../lib/platforms"
import { EmptyState } from "../ui/Panel"

const COLS = "grid-cols-[110px_150px_minmax(200px,1fr)_80px_100px_minmax(240px,1.2fr)]"
const SCALE = 5

/** Months where a source's volume or sentiment broke from its previous six months. */
export default function SpikeTable({ spikes, events }) {
  if (!spikes.length) return <EmptyState height={140}>No source has broken from its usual pattern yet.</EmptyState>
  const byNumber = Object.fromEntries(events.map((e) => [e.number, e]))
  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-panel">
      <div className="min-w-[920px]">
        <div className={`grid ${COLS} gap-5 border-b border-line2 px-6 py-3.5 text-xs text-ink3`}>
          <span>Month</span>
          <span>Source</span>
          <span>Volume against its usual</span>
          <span className="text-right">Texts</span>
          <span className="text-right">Net</span>
          <span>Matched event</span>
        </div>
        {spikes.map((s) => {
          const event = s.event ? byNumber[s.event] : null
          const width = s.ratio == null ? 0 : (Math.min(SCALE, s.ratio) / SCALE) * 100
          return (
            <div
              key={`${s.platform}${s.month}${s.kind}`}
              className={`grid ${COLS} min-h-14 items-center gap-5 border-b border-line px-6 last:border-b-0`}
            >
              <span className="num text-[13px]">{formatMonth(s.month)}</span>
              <span className="text-sm">{PLATFORMS[s.platform]?.name}</span>
              <div className="flex items-center gap-2.5">
                <div className="relative h-3 flex-1 rounded-[3px] bg-panel2">
                  <div className="absolute inset-y-0 left-0 rounded-[3px] bg-ink3" style={{ width: `${width}%` }} />
                  <div className="absolute -inset-y-[3px] w-[2px] bg-ink" style={{ left: `${100 / SCALE}%` }} />
                </div>
                <span className="num min-w-12 text-right text-xs">
                  {s.ratio == null ? "-" : `${s.ratio.toFixed(1)}×`}
                </span>
              </div>
              <span className="num text-right text-[13px]">{s.n}</span>
              <span className="num flex items-center justify-end gap-2 text-[13px]">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{
                    background:
                      s.net_sentiment > 0.05 ? "var(--pos)" : s.net_sentiment < -0.05 ? "var(--neg)" : "var(--neu)",
                  }}
                  aria-hidden="true"
                />
                {formatSigned(s.net_sentiment)}
              </span>
              {event ? (
                <span className="flex items-center gap-2 text-[13px]">
                  <span className="num flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full border border-line2 text-[11px]">
                    {event.number}
                  </span>
                  <span>
                    {event.title}
                    {s.kind === "sentiment" && <span className="text-ink3"> · sentiment jump</span>}
                  </span>
                </span>
              ) : (
                <span className="justify-self-start rounded-full border border-dashed border-glow px-2.5 py-1 text-xs font-semibold">
                  {s.kind === "sentiment" ? "Sentiment jump, needs a name" : "Needs a name"}
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
