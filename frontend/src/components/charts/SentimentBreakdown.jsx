import { formatNumber, formatPercent, formatSigned } from "../../lib/format"
import { SENTIMENTS, SENTIMENT_COLORS, SENTIMENT_LABELS } from "../../lib/sentiment"
import { Card, EmptyState } from "../ui/Card"

export default function SentimentBreakdown({ sentiment, netSentiment, unit }) {
  const total = SENTIMENTS.reduce((sum, s) => sum + sentiment[s], 0)
  return (
    <Card title="Sentiment breakdown" subtitle={`All scored ${unit} in this range`}>
      {total === 0 ? (
        <EmptyState height={240}>No scored {unit} in this range yet.</EmptyState>
      ) : (
        <div className="flex h-[240px] flex-col justify-between">
          <div>
            <div className="flex h-4 w-full overflow-hidden rounded-full" role="img" aria-label="Sentiment shares">
              {SENTIMENTS.map((s) => (
                <div key={s} style={{ width: `${(sentiment[s] / total) * 100}%`, background: SENTIMENT_COLORS[s] }} />
              ))}
            </div>
            <dl className="mt-5 space-y-3">
              {SENTIMENTS.map((s) => (
                <div key={s} className="flex items-center gap-3 text-sm">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: SENTIMENT_COLORS[s] }} />
                  <dt className="text-gray-600 dark:text-gray-300">{SENTIMENT_LABELS[s]}</dt>
                  <dd className="ml-auto flex gap-3 tabular-nums">
                    <span className="text-gray-500 dark:text-gray-400">{formatNumber(sentiment[s])}</span>
                    <span className="w-12 text-right font-semibold text-gray-900 dark:text-white">
                      {formatPercent(sentiment[s] / total)}
                    </span>
                  </dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-gray-900/40">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Net sentiment
            </p>
            <p className="mt-0.5 text-sm text-gray-600 dark:text-gray-300">
              <span
                className={`mr-2 text-xl font-semibold tabular-nums ${
                  netSentiment > 0.05
                    ? "text-emerald-600 dark:text-emerald-400"
                    : netSentiment < -0.05
                      ? "text-red-600 dark:text-red-400"
                      : "text-gray-900 dark:text-white"
                }`}
              >
                {formatSigned(netSentiment)}
              </span>
              share positive minus share negative
            </p>
          </div>
        </div>
      )}
    </Card>
  )
}
