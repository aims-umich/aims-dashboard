import { SENTIMENT_LABELS } from "../../lib/sentiment"

const STYLES = {
  positive: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300",
  neutral: "bg-gray-100 text-gray-700 ring-gray-500/20 dark:bg-gray-500/10 dark:text-gray-300",
  negative: "bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-500/10 dark:text-red-300",
}

export default function SentimentPill({ sentiment, confidence }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STYLES[sentiment]}`}
      title={confidence != null ? `Model confidence ${(confidence * 100).toFixed(0)}%` : undefined}
    >
      {SENTIMENT_LABELS[sentiment]}
      {confidence != null && <span className="tabular-nums opacity-70">{Math.round(confidence * 100)}%</span>}
    </span>
  )
}
