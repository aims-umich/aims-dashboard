import { countsTotal } from "../../lib/stats"

/** Positive, neutral and negative shares as one bar, with a 2px gap between segments. */
export default function SplitBar({ sentiment, height = 8, labels = false, className = "" }) {
  const total = countsTotal(sentiment)
  if (!total) return <div className={`rounded-full bg-line ${className}`} style={{ height }} />
  const parts = [
    ["positive", "var(--pos)"],
    ["neutral", "var(--neu)"],
    ["negative", "var(--neg)"],
  ].map(([key, color]) => ({ key, color, share: sentiment[key] / total }))
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <div className="flex gap-[2px]" style={{ height }} aria-hidden="true">
        {parts.map((p) =>
          p.share > 0 ? (
            <span key={p.key} className="rounded-[2px]" style={{ width: `${p.share * 100}%`, background: p.color }} />
          ) : null,
        )}
      </div>
      {labels && (
        <div className="num flex justify-between text-[11px] text-ink2">
          {parts.map((p) => (
            <span key={p.key}>{(p.share * 100).toFixed(1)}%</span>
          ))}
        </div>
      )}
    </div>
  )
}
