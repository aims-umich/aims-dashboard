import { formatNumber, formatRange, formatSigned } from "../../lib/format"
import { countsTotal, fromCounts, MIN_SAMPLE } from "../../lib/stats"
import LowSample from "../ui/LowSample"
import { Panel, PanelHeader } from "../ui/Panel"

const ORDER = [
  ["positive", "Positive", "var(--pos)"],
  ["neutral", "Neutral", "var(--neu)"],
  ["negative", "Negative", "var(--neg)"],
]

/** Round shares to whole squares that add up to exactly 100 (largest remainder). */
function squares(sentiment) {
  const total = countsTotal(sentiment)
  if (!total) return []
  const raw = ORDER.map(([key]) => (sentiment[key] / total) * 100)
  const whole = raw.map(Math.floor)
  let left = 100 - whole.reduce((a, b) => a + b, 0)
  raw
    .map((v, i) => [v - Math.floor(v), i])
    .sort((a, b) => b[0] - a[0])
    .forEach(([, i]) => {
      if (left-- > 0) whole[i] += 1
    })
  return whole.flatMap((count, i) => Array.from({ length: count }, () => ORDER[i][2]))
}

export default function SentimentSplit({ sentiment, unit }) {
  const total = countsTotal(sentiment)
  const { net, lo, hi } = fromCounts(sentiment)
  const cells = squares(sentiment)
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        title="Sentiment split"
        caption={total ? `Every square is 1% of the ${formatNumber(total)} ${unit}.` : undefined}
      />
      {total ? (
        <div
          role="img"
          aria-label={ORDER.map(([k, l]) => `${l} ${((sentiment[k] / total) * 100).toFixed(1)}%`).join(", ")}
          className="grid max-w-[320px] grid-cols-10 gap-1"
        >
          {cells.map((color, i) => (
            <span key={i} className="aspect-square rounded-[3px]" style={{ background: color }} />
          ))}
        </div>
      ) : (
        <p className="m-0 text-sm text-ink3">No scored {unit} in this range.</p>
      )}
      <div className="flex flex-col gap-2.5">
        {ORDER.map(([key, label, color]) => (
          <div key={key} className="grid grid-cols-[14px_1fr_auto_auto] items-center gap-3 text-sm">
            <span className="h-3 w-3 rounded-[3px]" style={{ background: color }} aria-hidden="true" />
            <span>{label}</span>
            <span className="num text-ink2">{formatNumber(sentiment[key])}</span>
            <span className="num min-w-14 text-right font-medium">
              {total ? `${((sentiment[key] / total) * 100).toFixed(1)}%` : "-"}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-auto flex items-baseline justify-between border-t border-line pt-4">
        <span className="text-sm text-ink2">Net sentiment</span>
        {total >= MIN_SAMPLE ? (
          <span className="flex flex-col items-end">
            <span className="num text-2xl font-medium">{formatSigned(net, 3)}</span>
            <span className="num text-[11px] text-ink3">{formatRange(lo, hi, 3)}</span>
          </span>
        ) : (
          <LowSample />
        )}
      </div>
    </Panel>
  )
}
