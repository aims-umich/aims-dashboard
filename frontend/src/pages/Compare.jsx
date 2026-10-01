import { useState } from "react"
import CompareTable from "../components/charts/CompareTable"
import CorrelationMatrix from "../components/charts/CorrelationMatrix"
import EngagementCompare from "../components/charts/EngagementCompare"
import SocialVsNews from "../components/charts/SocialVsNews"
import SourceMultiples from "../components/charts/SourceMultiples"
import WordMatrix from "../components/charts/WordMatrix"
import { Skeleton } from "../components/ui/Panel"
import Segmented from "../components/ui/Segmented"
import { PLATFORM_ORDER, PLATFORMS } from "../lib/platforms"
import { useStatus } from "../lib/statusContext"
import { useDocumentTitle } from "../lib/useDocumentTitle"
import { usePolling, usePollingAll } from "../lib/usePolling"

const RANGES = [
  { value: "30d", label: "30 days" },
  { value: "1y", label: "1 year" },
  { value: "all", label: "All time" },
]

const ordered = (keys) => PLATFORM_ORDER.filter((k) => keys.includes(k))

export default function Compare() {
  useDocumentTitle("Compare sources")
  const [range, setRange] = useState("all")
  const { data: status } = useStatus()
  const live = ordered((status?.platforms ?? []).map((p) => p.platform))
  const social = live.filter((k) => PLATFORMS[k].group === "social")
  const table = usePolling(`/platforms?range=${range}`)
  const monthly = usePolling("/series?bucket=month", 300_000)
  const weekly = usePolling("/series?bucket=week", 300_000)
  const strip = usePolling("/strip", 300_000)
  const words = usePollingAll(social.map((k) => `/platforms/${k}/words?range=30d`))
  const engagement = usePollingAll(social.map((k) => `/platforms/${k}/summary?range=30d`))
  const pick = (byKey) => Object.fromEntries(ordered(Object.keys(byKey ?? {})).map((k) => [k, byKey[k]]))
  const firstSeen = Object.fromEntries((strip.data?.platforms ?? []).map((p) => [p.platform, p.collecting_since]))

  return (
    <div className="flex flex-col gap-6">
      <section
        aria-labelledby="cmp-h"
        className="flex flex-wrap items-end justify-between gap-6 border-b border-line pt-14 pb-8"
      >
        <div className="flex flex-col gap-4">
          <span className="num text-xs tracking-[0.1em] text-glow">COMPARE</span>
          <h1
            id="cmp-h"
            className="m-0 text-[40px] leading-none font-extrabold tracking-[-0.03em] wider sm:text-[56px]"
          >
            Compare sources
          </h1>
        </div>
        <Segmented label="Time range" value={range} onChange={setRange} options={RANGES} />
      </section>

      <section aria-labelledby="table-h" className="flex flex-col gap-4">
        <h2 id="table-h" className="m-0 text-[22px] font-bold">
          Side by side
        </h2>
        {table.data ? (
          <CompareTable
            platforms={[...table.data.platforms].sort(
              (a, b) => PLATFORM_ORDER.indexOf(a.platform) - PLATFORM_ORDER.indexOf(b.platform),
            )}
          />
        ) : (
          <Skeleton height={360} />
        )}
      </section>

      {monthly.data ? <SocialVsNews series={monthly.data.platforms} /> : <Skeleton height={420} />}

      <section aria-labelledby="sm-h" className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 id="sm-h" className="m-0 text-[22px] font-bold">
            Each source over time
          </h2>
          <p className="m-0 text-sm text-ink2">
            Monthly net sentiment, three-month rolling, on a shared scale. Months with fewer than 8 texts are left out.
          </p>
        </div>
        {monthly.data ? (
          <SourceMultiples series={pick(monthly.data.platforms)} firstSeen={firstSeen} />
        ) : (
          <Skeleton height={420} />
        )}
      </section>

      <section
        aria-label="Language and co-movement"
        className="grid grid-cols-[repeat(auto-fit,minmax(min(460px,100%),1fr))] gap-4"
      >
        {words.data ? <WordMatrix words={words.data} /> : <Skeleton height={460} />}
        {weekly.data ? <CorrelationMatrix series={pick(weekly.data.platforms)} /> : <Skeleton height={460} />}
      </section>

      {engagement.data ? <EngagementCompare summaries={engagement.data} /> : <Skeleton height={220} />}
    </div>
  )
}
