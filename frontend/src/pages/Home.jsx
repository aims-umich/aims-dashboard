import { ArrowUpRight } from "lucide-react"
import { useState } from "react"
import { Link } from "react-router-dom"
import SignalStrips from "../components/charts/SignalStrips"
import SourceScale from "../components/charts/SourceScale"
import SourceCard from "../components/SourceCard"
import { EmptyState, Skeleton } from "../components/ui/Panel"
import SectionHeader from "../components/ui/Section"
import Segmented from "../components/ui/Segmented"
import { PAPER, PLATFORM_ORDER, PLATFORMS } from "../lib/platforms"
import { useStatus } from "../lib/statusContext"
import { useDocumentTitle } from "../lib/useDocumentTitle"
import { usePolling } from "../lib/usePolling"

const SCALE_RANGES = [
  { value: "30d", label: "30 days" },
  { value: "1y", label: "1 year" },
  { value: "all", label: "All time" },
]

const byOrder = (rows) =>
  [...rows].sort((a, b) => PLATFORM_ORDER.indexOf(a.platform) - PLATFORM_ORDER.indexOf(b.platform))

function Hero() {
  return (
    <section
      aria-labelledby="hero-h"
      className="flex flex-col gap-5 border-b border-line pt-14 pb-12 sm:pt-[72px] sm:pb-14"
    >
      <span className="num text-xs tracking-[0.1em] text-ink3">AIMS LAB · UNIVERSITY OF MICHIGAN</span>
      <h1 id="hero-h" className="m-0 text-[40px] leading-none font-extrabold tracking-[-0.03em] wider sm:text-[64px]">
        Nuclear Sentiment Analysis
      </h1>
      <p className="m-0 max-w-[680px] text-base leading-relaxed text-ink2 sm:text-lg">
        Public sentiment toward nuclear energy across social media and news, scored live by a language model fine-tuned
        on nuclear-energy discourse.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <a
          href={PAPER.href}
          target="_blank"
          rel="noopener noreferrer"
          className="flex min-h-11 items-center gap-2.5 rounded-[10px] bg-ink px-5 text-[15px] font-semibold text-bg no-underline"
        >
          Read the paper
          <ArrowUpRight size={15} aria-hidden="true" />
        </a>
        <Link
          to="/about"
          className="flex min-h-11 items-center rounded-[10px] border border-line2 px-5 text-[15px] font-medium text-ink no-underline"
        >
          How it works
        </Link>
      </div>
      <p className="m-0 max-w-[680px] text-[13px] leading-normal text-ink3">
        {PAPER.authors}. <span className="italic">{PAPER.title}.</span> {PAPER.venue}.
      </p>
    </section>
  )
}

export default function Home() {
  useDocumentTitle(null)
  const [range, setRange] = useState("all")
  const { data: status } = useStatus()
  const scale = usePolling(`/platforms?range=${range}`)
  const month = usePolling("/platforms?range=30d")
  const strip = usePolling("/strip")
  const statuses = Object.fromEntries((status?.platforms ?? []).map((p) => [p.platform, p]))
  const unitOf = (row) => PLATFORMS[row.platform]?.unitLabel ?? "texts"

  return (
    <>
      <Hero />

      <section aria-labelledby="scale-h" className="flex flex-col gap-6 border-b border-line py-14">
        <SectionHeader
          id="scale-h"
          code="CH-01"
          title="Where each source stands"
          caption="Net sentiment with its 95% interval. A dot is gray when its interval crosses zero, meaning we cannot yet tell that source apart from neutral."
          actions={<Segmented label="Time range" value={range} onChange={setRange} options={SCALE_RANGES} />}
        />
        {scale.data ? (
          <SourceScale platforms={byOrder(scale.data.platforms)} unitOf={unitOf} />
        ) : scale.error ? (
          <EmptyState>Could not load the sources. Retrying every minute.</EmptyState>
        ) : (
          <Skeleton height={380} />
        )}
      </section>

      <section aria-labelledby="strip-h" className="flex flex-col gap-6 border-b border-line py-14">
        <SectionHeader
          id="strip-h"
          code="CH-02"
          title="Last 24 hours"
          caption="One tick per scored post, comment or sentence, placed at the moment it was published."
        />
        {strip.data ? (
          <SignalStrips data={{ ...strip.data, platforms: byOrder(strip.data.platforms) }} />
        ) : (
          <Skeleton height={320} />
        )}
      </section>

      <section aria-labelledby="src-h" className="flex flex-col gap-6 pt-14">
        <SectionHeader
          id="src-h"
          code="CH-03"
          title="Last 30 days"
          actions={<span className="text-[13px] text-ink3">Bars show monthly volume over the past 13 months.</span>}
        />
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(220px,100%),1fr))] gap-4">
          {month.data
            ? byOrder(month.data.platforms).map((p) => (
                <SourceCard key={p.platform} summary={p} status={statuses[p.platform]} />
              ))
            : Array.from({ length: 5 }, (_, i) => <Skeleton key={i} height={300} />)}
        </div>
      </section>
    </>
  )
}
