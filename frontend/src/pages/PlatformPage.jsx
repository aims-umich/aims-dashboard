import { AlertTriangle } from "lucide-react"
import { useSearchParams } from "react-router-dom"
import ConfidenceHistogram from "../components/charts/ConfidenceHistogram"
import EngagementTrend from "../components/charts/EngagementTrend"
import SentimentBreakdown from "../components/charts/SentimentBreakdown"
import SentimentTrend from "../components/charts/SentimentTrend"
import VolumeChart from "../components/charts/VolumeChart"
import WordPanels from "../components/charts/WordPanels"
import PlatformIcon from "../components/PlatformIcon"
import RecentPosts from "../components/RecentPosts"
import { MetricCard, Skeleton } from "../components/ui/Card"
import FreshnessBadge from "../components/ui/FreshnessBadge"
import SegmentedControl from "../components/ui/SegmentedControl"
import { formatDate, formatNumber, formatPercent, formatSigned } from "../lib/format"
import { PLATFORMS, RANGES } from "../lib/platforms"
import { usePlatformStatus } from "../lib/statusContext"
import { useDocumentTitle } from "../lib/useDocumentTitle"
import { usePolling } from "../lib/usePolling"

const REGIONS = [
  { value: "all", label: "All coverage" },
  { value: "us", label: "U.S." },
]

function PageHeader({ config, status, range, onRange, region, onRegion }) {
  return (
    <header className="flex flex-col gap-4 border-b border-gray-200 pb-6 dark:border-gray-800 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        {config.logo ? (
          <>
            <img src={config.logo.light} alt={config.name} className="h-12 w-auto dark:hidden" />
            <img src={config.logo.dark} alt={config.name} className="hidden h-12 w-auto dark:block" />
          </>
        ) : (
          <div className="flex items-center gap-3">
            <PlatformIcon platform={config.key} size={40} />
            <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">{config.name}</h1>
          </div>
        )}
        <p className="mt-3 max-w-3xl text-sm leading-6 text-gray-600 dark:text-gray-300">{config.description}</p>
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-gray-500 dark:text-gray-400">
          <FreshnessBadge status={status} />
          <span>Collected: {config.cadence}</span>
          {config.credit && <span>Original dashboard by {config.credit}</span>}
          {config.attribution && (
            <a href={config.attribution.href} target="_blank" rel="noopener noreferrer" className="hover:underline">
              {config.attribution.text}
            </a>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 md:justify-end">
        {config.regionFilter && (
          <SegmentedControl label="Coverage" value={region} onChange={onRegion} options={REGIONS} />
        )}
        <SegmentedControl label="Time range" value={range} onChange={onRange} options={RANGES} />
      </div>
    </header>
  )
}

export default function PlatformPage({ platform }) {
  const config = PLATFORMS[platform]
  useDocumentTitle(config.name)
  const status = usePlatformStatus(platform)
  const [params, setParams] = useSearchParams()
  const requested = params.get("range")
  const range = RANGES.some((r) => r.value === requested) ? requested : config.defaultRange
  const region = config.regionFilter && params.get("region") === "us" ? "us" : "all"
  const updateParams = (next) => {
    const merged = { range, region, ...next }
    const query = {}
    if (merged.range !== config.defaultRange) query.range = merged.range
    if (merged.region !== "all") query.region = merged.region
    setParams(query, { replace: true, preventScrollReset: true })
  }
  const regionQuery = region === "us" ? "&region=us" : ""

  const { data, error } = usePolling(`/platforms/${platform}/summary?range=${range}${regionQuery}`)
  const unit = config.unitLabel
  const isArticle = platform === "guardian" || platform === "nyt"
  const loading = !data
  const totals = data?.totals

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        config={config}
        status={status}
        range={range}
        onRange={(value) => updateParams({ range: value })}
        region={region}
        onRegion={(value) => updateParams({ region: value })}
      />

      {error && (
        <div
          role="alert"
          className="flex items-center gap-3 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-200"
        >
          <AlertTriangle size={16} aria-hidden="true" />
          {data ? "Showing the last data we received; retrying every minute." : error.message}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard
          label={`Scored ${unit}`}
          value={formatNumber(totals?.scored)}
          hint={isArticle ? `from ${formatNumber(totals?.documents)} articles` : "in this range"}
          loading={loading}
        />
        <MetricCard
          label="Last 24 hours"
          value={formatNumber(totals?.last_24h)}
          hint={`new ${isArticle ? "articles" : unit}`}
          loading={loading}
        />
        <MetricCard
          label="Net sentiment"
          value={formatSigned(data?.net_sentiment)}
          hint="positive share minus negative share"
          loading={loading}
        />
        <MetricCard
          label="Average confidence"
          value={formatPercent(totals?.avg_confidence)}
          hint={totals?.first_published ? `since ${formatDate(totals.first_published)}` : "no data yet"}
          loading={loading}
        />
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Skeleton height={380} />
          </div>
          <Skeleton height={380} />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="min-w-0 lg:col-span-2">
              <SentimentTrend trend={data.trend} bucket={data.bucket} unit={unit} />
            </div>
            <SentimentBreakdown sentiment={data.sentiment} netSentiment={data.net_sentiment} unit={unit} />
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {data.engagement ? (
              <EngagementTrend engagement={data.engagement} bucket={data.bucket} unit={unit} />
            ) : (
              <VolumeChart
                trend={data.trend}
                bucket={data.bucket}
                title="Articles collected"
                seriesName="Articles"
                accent={config.chartColor ?? config.accent}
              />
            )}
            <ConfidenceHistogram bins={data.confidence} avgConfidence={totals.avg_confidence} unit={unit} />
          </div>
        </>
      )}

      <WordPanels platform={platform} range={range} unit={unit} regionQuery={regionQuery} />

      <RecentPosts
        platform={platform}
        isArticle={isArticle}
        regionQuery={regionQuery}
        fields={data?.engagement?.fields ?? []}
        title={isArticle ? "Recent articles" : `Recent ${unit}`}
        note={config.listNote}
      />
    </div>
  )
}
