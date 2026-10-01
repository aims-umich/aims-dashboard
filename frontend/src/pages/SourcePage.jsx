import { AlertTriangle } from "lucide-react"
import { useSearchParams } from "react-router-dom"
import ActivityHeatmap from "../components/charts/ActivityHeatmap"
import ConfidenceHistogram from "../components/charts/ConfidenceHistogram"
import EngagementBySentiment from "../components/charts/EngagementBySentiment"
import SentimentOverTime from "../components/charts/SentimentOverTime"
import SentimentSplit from "../components/charts/SentimentSplit"
import Sparkline from "../components/charts/Sparkline"
import VolumeOverTime from "../components/charts/VolumeOverTime"
import { DistinctiveWords, TopWords, WordField } from "../components/charts/Words"
import SourceTabs from "../components/layout/SourceTabs"
import RecentPosts from "../components/posts/RecentPosts"
import Freshness from "../components/ui/Freshness"
import LowSample from "../components/ui/LowSample"
import { Skeleton } from "../components/ui/Panel"
import PlatformMark from "../components/ui/PlatformMark"
import Segmented from "../components/ui/Segmented"
import { formatDate, formatNumber, formatPercent, formatRange, formatSigned } from "../lib/format"
import { PLATFORMS, RANGES } from "../lib/platforms"
import { countsTotal, fromCounts, MIN_SAMPLE } from "../lib/stats"
import { usePlatformStatus } from "../lib/statusContext"
import { useDocumentTitle } from "../lib/useDocumentTitle"
import { usePolling } from "../lib/usePolling"

const REGIONS = [
  { value: "all", label: "All coverage" },
  { value: "us", label: "U.S." },
]

function Tile({ label, value, hint, spark, loading }) {
  return (
    <div className="flex min-w-0 flex-col gap-2.5 rounded-2xl border border-line bg-panel px-[22px] py-5">
      <span className="text-[13px] text-ink2">{label}</span>
      {loading ? (
        <span className="h-10 w-24 animate-pulse rounded bg-panel2" />
      ) : (
        <div className="flex items-end justify-between gap-3">
          <span className="num text-[40px] leading-none font-medium tracking-[-0.03em]">{value}</span>
          {spark}
        </div>
      )}
      <span className="truncate text-xs text-ink3">{hint}</span>
    </div>
  )
}

function Header({ config, status, range, onRange, region, onRegion, collectingSince }) {
  return (
    <section
      aria-labelledby="src-title"
      className="flex flex-wrap items-end justify-between gap-6 border-b border-line pt-10 pb-8"
    >
      <div className="flex max-w-[760px] flex-col gap-4">
        <div className="flex items-center gap-4">
          <PlatformMark platform={config.key} size={56} />
          <h1
            id="src-title"
            className="m-0 text-[40px] leading-none font-extrabold tracking-[-0.03em] wider sm:text-[56px]"
          >
            {config.name}
          </h1>
        </div>
        <p className="m-0 text-base leading-relaxed text-ink2 sm:text-[17px]">{config.description}</p>
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-[13px] text-ink2">
          <Freshness status={status} className="text-[13px]" />
          <span>Collected: {config.cadence.toLowerCase()}</span>
          {collectingSince && <span>Collecting since {formatDate(collectingSince)}</span>}
          {config.credit && <span>Early collector script by {config.credit}</span>}
          {config.attribution && (
            <a
              href={config.attribution.href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-ink2 underline hover:text-ink"
            >
              {config.attribution.text}
            </a>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {config.regionFilter && <Segmented label="Coverage" value={region} onChange={onRegion} options={REGIONS} />}
        <Segmented label="Time range" value={range} onChange={onRange} options={RANGES} />
      </div>
    </section>
  )
}

export default function SourcePage({ platform }) {
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
  const words = usePolling(`/platforms/${platform}/words?range=${range}${regionQuery}`, 300_000)
  const unit = config.unitLabel
  const totals = data?.totals
  const scored = data ? countsTotal(data.sentiment) : 0
  const net = data ? fromCounts(data.sentiment) : null
  const trend = data?.trend ?? []
  const volumes = trend.map(countsTotal)
  const cumulative = volumes.reduce((acc, v) => [...acc, (acc.at(-1) ?? 0) + v], [])
  const nets = trend.map((b) => (countsTotal(b) >= 5 ? fromCounts(b).net : null))
  const closeShare = data
    ? data.confidence.filter((b) => b.to <= 0.7 + 1e-6).reduce((a, b) => a + b.count, 0) / Math.max(1, scored)
    : null

  return (
    <div className="flex flex-col gap-6">
      <div className="pt-6 md:pt-0">
        <SourceTabs />
      </div>
      <Header
        config={config}
        status={status}
        range={range}
        onRange={(value) => updateParams({ range: value })}
        region={region}
        onRegion={(value) => updateParams({ region: value })}
        collectingSince={totals?.collecting_since}
      />

      {error && (
        <div
          role="alert"
          className="flex items-center gap-3 rounded-xl border border-line2 bg-panel2 px-4 py-3 text-sm text-ink2"
        >
          <AlertTriangle size={16} aria-hidden="true" />
          {data ? "Showing the last data we received; retrying every minute." : error.message}
        </div>
      )}

      <section aria-label="Key figures" className="grid grid-cols-[repeat(auto-fit,minmax(min(250px,100%),1fr))] gap-4">
        <Tile
          loading={!data}
          label={`Scored ${unit}`}
          value={formatNumber(scored)}
          hint={
            config.articles && platform === "guardian"
              ? `from ${formatNumber(totals?.documents)} articles`
              : "in this range"
          }
          spark={<Sparkline values={cumulative} />}
        />
        <Tile
          loading={!data}
          label="Last 24 hours"
          value={formatNumber(totals?.last_24h)}
          hint={`new ${config.articles ? "articles" : unit}`}
          spark={<Sparkline values={volumes} />}
        />
        <Tile
          loading={!data}
          label="Net sentiment"
          value={scored >= MIN_SAMPLE ? formatSigned(net?.net, 3) : <LowSample />}
          hint={
            scored >= MIN_SAMPLE
              ? `95% interval ${formatRange(net.lo, net.hi, 3)}`
              : `only ${scored} ${unit} in this range`
          }
          spark={<Sparkline values={nets} />}
        />
        <Tile
          loading={!data}
          label="Average confidence"
          value={formatPercent(totals?.avg_confidence, 1)}
          hint={closeShare == null ? "" : `${formatPercent(closeShare, 1)} of ${unit} are close calls`}
        />
      </section>

      {!data ? (
        <Skeleton height={520} />
      ) : (
        <>
          <section aria-label="Sentiment" className="flex flex-wrap gap-4">
            <div className="min-w-0 flex-[2_1_640px]">
              <SentimentOverTime
                trend={trend}
                bucket={data.bucket}
                unit={unit}
                collectingSince={range === "all" ? null : totals.collecting_since}
              />
            </div>
            <div className="min-w-0 flex-[1_1_300px]">
              <SentimentSplit sentiment={data.sentiment} unit={unit} />
            </div>
          </section>
          <section
            aria-label="Engagement and confidence"
            className="grid grid-cols-[repeat(auto-fit,minmax(min(420px,100%),1fr))] gap-4"
          >
            {data.engagement ? (
              <EngagementBySentiment engagement={data.engagement} unit={unit} />
            ) : (
              <VolumeOverTime trend={trend} bucket={data.bucket} title="Articles collected" noun="articles" />
            )}
            <ConfidenceHistogram bins={data.confidence} avgConfidence={totals.avg_confidence} unit={unit} />
          </section>
        </>
      )}

      <section aria-labelledby="words-h" className="flex flex-col gap-4 pt-8">
        <div className="flex flex-col gap-2">
          <span className="num text-xs tracking-[0.1em] text-glow">LANGUAGE</span>
          <h2 id="words-h" className="m-0 text-[28px] font-[750] tracking-[-0.015em] wide">
            Language
          </h2>
        </div>
        {words.data ? (
          <>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(420px,100%),1fr))] gap-4">
              <DistinctiveWords words={words.data.distinctive} sampled={words.data.sampled} unit={unit} />
              <TopWords words={words.data} unit={unit} />
            </div>
            <WordField cloud={words.data.cloud} />
          </>
        ) : (
          <Skeleton height={360} />
        )}
      </section>

      {data && !config.articles && <ActivityHeatmap activity={data.activity} unit={unit} />}

      <RecentPosts
        platform={platform}
        config={config}
        fields={data?.engagement?.fields ?? []}
        regionQuery={regionQuery}
      />
    </div>
  )
}
