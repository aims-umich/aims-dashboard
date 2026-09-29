import { motion } from "framer-motion"
import { ArrowRight } from "lucide-react"
import { Link } from "react-router-dom"
import PlatformIcon from "../components/PlatformIcon"
import FreshnessBadge from "../components/ui/FreshnessBadge"
import { formatNumber, formatSigned } from "../lib/format"
import { PLATFORMS, PLATFORM_ORDER } from "../lib/platforms"
import { SENTIMENTS, SENTIMENT_COLORS } from "../lib/sentiment"
import { useStatus } from "../lib/statusContext"
import { useDocumentTitle } from "../lib/useDocumentTitle"
import { usePolling } from "../lib/usePolling"

function SentimentBar({ sentiment }) {
  const total = SENTIMENTS.reduce((sum, s) => sum + (sentiment?.[s] ?? 0), 0)
  if (!total) return <div className="h-2 w-full rounded-full bg-gray-100 dark:bg-gray-700" />
  return (
    <div className="flex h-2 w-full overflow-hidden rounded-full" aria-hidden="true">
      {SENTIMENTS.map((s) => (
        <div key={s} style={{ width: `${(sentiment[s] / total) * 100}%`, background: SENTIMENT_COLORS[s] }} />
      ))}
    </div>
  )
}

function PlatformCard({ config, summary, status, index }) {
  const scored = summary?.totals?.scored
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}>
      <Link
        to={config.route}
        className="group flex h-full flex-col rounded-xl border border-gray-200/70 bg-white p-5 transition hover:-translate-y-0.5 hover:shadow-lg focus-visible:outline-2 focus-visible:outline-indigo-500 dark:border-gray-700/60 dark:bg-gray-800"
      >
        <div className={`-mx-5 -mt-5 mb-4 h-1.5 rounded-t-xl bg-gradient-to-r ${config.gradient}`} />
        <div className="flex items-center gap-3">
          <PlatformIcon platform={config.key} size={32} />
          <div className="min-w-0">
            <h2 className="font-semibold text-gray-900 dark:text-white">{config.name}</h2>
            <p className="truncate text-xs text-gray-500 dark:text-gray-400">{config.tagline}</p>
          </div>
          <ArrowRight
            size={18}
            className="ml-auto text-gray-400 transition-transform group-hover:translate-x-1 group-hover:text-gray-900 dark:group-hover:text-white"
            aria-hidden="true"
          />
        </div>
        <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-xs text-gray-500 dark:text-gray-400">Scored {config.unitLabel}, 30 days</dt>
            <dd className="mt-0.5 text-lg font-semibold tabular-nums text-gray-900 dark:text-white">
              {summary ? formatNumber(scored) : "…"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-gray-500 dark:text-gray-400">Net sentiment</dt>
            <dd className="mt-0.5 text-lg font-semibold tabular-nums text-gray-900 dark:text-white">
              {summary ? formatSigned(summary.net_sentiment) : "…"}
            </dd>
          </div>
        </dl>
        <div className="mt-4">
          <SentimentBar sentiment={summary?.sentiment} />
        </div>
        <div className="mt-auto pt-4">
          <FreshnessBadge status={status} />
        </div>
      </Link>
    </motion.div>
  )
}

export default function Home() {
  useDocumentTitle(null)
  const { data: status } = useStatus()
  const { data: overview } = usePolling("/platforms?range=30d")
  const enabled = new Set((status?.platforms ?? overview?.platforms ?? []).map((p) => p.platform))
  const keys = PLATFORM_ORDER.filter((key) => enabled.has(key))
  const summaries = Object.fromEntries((overview?.platforms ?? []).map((p) => [p.platform, p]))
  const statuses = Object.fromEntries((status?.platforms ?? []).map((p) => [p.platform, p]))

  return (
    <div className="mx-auto max-w-7xl">
      <header className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-400">
          AIMS Lab · University of Michigan
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-4xl">
          Public sentiment toward nuclear energy, live
        </h1>
        <p className="mt-4 text-base leading-7 text-gray-600 dark:text-gray-300">
          We collect public posts, comments, and news coverage about nuclear energy as they are published, and a
          sentiment model fine-tuned on nuclear-energy discourse labels each one as positive, neutral, or negative.{" "}
          <Link to="/about" className="font-medium text-indigo-600 hover:underline dark:text-indigo-400">
            How it works
          </Link>
        </p>
      </header>
      <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {keys.length
          ? keys.map((key, i) => (
              <PlatformCard
                key={key}
                index={i}
                config={PLATFORMS[key]}
                summary={summaries[key]}
                status={statuses[key]}
              />
            ))
          : Array.from({ length: 6 }, (_, i) => (
              <div key={i} className="h-[228px] animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800" />
            ))}
      </div>
    </div>
  )
}
