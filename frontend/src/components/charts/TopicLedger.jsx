import { formatNumber, formatPercent, formatSigned } from "../../lib/format"
import { MIN_SAMPLE } from "../../lib/stats"
import Sparkbars from "./Sparkbars"
import SplitBar from "../ui/SplitBar"

const COLS = "grid-cols-[minmax(240px,1.3fr)_150px_80px_minmax(180px,1fr)_90px_minmax(170px,0.9fr)]"

function change(t) {
  // Against a near-empty previous period a percentage means nothing.
  if (t.previous_count == null || t.previous_count < 20) return "-"
  const ratio = t.count / t.previous_count - 1
  return `${ratio > 0 ? "+" : ratio < 0 ? "−" : ""}${Math.abs(Math.round(ratio * 100))}%`
}

/** Every topic as a row: weekly volume, share, net sentiment, change, split. Click a row to inspect it. */
export default function TopicLedger({ topics, selected, onSelect }) {
  const rows = [...topics].sort((a, b) => b.count - a.count)
  return (
    <>
      <div className="flex flex-col overflow-hidden rounded-2xl border border-line bg-panel md:hidden">
        {rows.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onSelect(t.id)}
            aria-pressed={t.id === selected}
            className={`flex flex-col gap-2 border-b border-line px-4 py-3.5 text-left last:border-b-0 ${t.id === selected ? "bg-panel2" : ""}`}
          >
            <span className="flex items-baseline justify-between gap-3">
              <span className="text-[15px] font-semibold text-ink">{t.name}</span>
              <span className="num text-xs text-ink2">{formatPercent(t.share, 0)}</span>
            </span>
            <SplitBar sentiment={t.sentiment} height={8} />
            <span className="num flex justify-between text-[11px] text-ink3">
              <span>{formatNumber(t.count)} texts</span>
              <span>net {t.count >= MIN_SAMPLE && t.net_sentiment != null ? formatSigned(t.net_sentiment) : "-"}</span>
              <span>change {change(t)}</span>
            </span>
          </button>
        ))}
      </div>
      <div className="hidden overflow-x-auto rounded-2xl border border-line bg-panel md:block">
        <div className="min-w-[1040px]">
          <div className={`grid ${COLS} items-center gap-5 border-b border-line2 px-6 py-3.5 text-xs text-ink3`}>
            <span>Topic</span>
            <span>Texts per week, 12 weeks</span>
            <span className="text-right">Share</span>
            <span>Net sentiment</span>
            <span className="text-right">Change</span>
            <span>Split</span>
          </div>
          {rows.map((t) => {
            const ok = t.count >= MIN_SAMPLE && t.net_sentiment != null
            const negW = ok && t.net_sentiment < 0 ? Math.min(100, (-t.net_sentiment / 0.6) * 100) : 0
            const posW = ok && t.net_sentiment > 0 ? Math.min(100, (t.net_sentiment / 0.6) * 100) : 0
            const active = t.id === selected
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => onSelect(t.id)}
                aria-pressed={active}
                className={`grid w-full ${COLS} min-h-[68px] items-center gap-5 border-b border-line px-6 py-2 text-left last:border-b-0 ${active ? "bg-panel2" : "hover:bg-panel2/60"}`}
              >
                <span className="flex flex-col leading-snug">
                  <span className="text-[15px] font-semibold text-ink">{t.name}</span>
                  <span className="num truncate text-[11px] text-ink3">{t.keywords.slice(0, 3).join(", ")}…</span>
                </span>
                <span className="w-[150px]">
                  <Sparkbars values={t.weekly} height={28} />
                </span>
                <span className="num text-right text-sm">{formatPercent(t.share, 0)}</span>
                <span className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_52px] items-center">
                  <span className="relative h-3.5 border-r border-line2">
                    <span className="absolute top-0 right-0 h-3.5 rounded-l bg-neg" style={{ width: `${negW}%` }} />
                  </span>
                  <span className="relative h-3.5">
                    <span className="absolute top-0 left-0 h-3.5 rounded-r bg-pos" style={{ width: `${posW}%` }} />
                  </span>
                  <span className="num text-right text-[13px]">{ok ? formatSigned(t.net_sentiment) : "-"}</span>
                </span>
                <span className="num text-right text-[13px] text-ink2">{change(t)}</span>
                <span className="flex flex-col gap-1">
                  <SplitBar sentiment={t.sentiment} height={10} />
                  <span className="num text-[10px] text-ink3">{formatNumber(t.count)} texts</span>
                </span>
              </button>
            )
          })}
        </div>
      </div>
    </>
  )
}
