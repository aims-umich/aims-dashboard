import { useState } from "react"
import TopicLandscape from "../components/charts/TopicLandscape"
import TopicLedger from "../components/charts/TopicLedger"
import TopicMatrix from "../components/charts/TopicMatrix"
import TopicSpotlight from "../components/charts/TopicSpotlight"
import { EmptyState, Panel, Skeleton } from "../components/ui/Panel"
import Segmented from "../components/ui/Segmented"
import { PLATFORM_ORDER } from "../lib/platforms"
import { useDocumentTitle } from "../lib/useDocumentTitle"
import { usePolling } from "../lib/usePolling"

const RANGES = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "1y", label: "1 year" },
  { value: "all", label: "All time" },
]

/** The topic that grew most against the previous period (with enough texts), else the biggest one. */
function fastestGrowing(topics) {
  const grown = topics
    .filter((t) => t.count >= 20 && t.previous_count >= 20)
    .sort((a, b) => b.count / b.previous_count - a.count / a.previous_count)
  return grown[0]
    ? { id: grown[0].id, label: "SPOTLIGHT · FASTEST GROWING" }
    : { id: [...topics].sort((a, b) => b.count - a.count)[0]?.id, label: "SPOTLIGHT · MOST DISCUSSED" }
}

export default function Topics() {
  useDocumentTitle("Topics")
  const [range, setRange] = useState("30d")
  const [chosen, setChosen] = useState(null)
  const { data, error } = usePolling(`/topics?range=${range}`, 300_000)
  const topics = data?.topics ?? []
  const fallback = data ? fastestGrowing(topics) : null
  const selectedId = chosen ?? fallback?.id
  const selected = topics.find((t) => t.id === selectedId)
  const platforms = PLATFORM_ORDER.filter((p) => data?.platforms.includes(p))

  return (
    <div className="flex flex-col gap-6">
      <section
        aria-labelledby="top-h"
        className="flex flex-wrap items-end justify-between gap-6 border-b border-line pt-14 pb-8"
      >
        <div className="flex max-w-[780px] flex-col gap-4">
          <span className="num text-xs tracking-[0.1em] text-glow">TOPICS</span>
          <h1
            id="top-h"
            className="m-0 text-[40px] leading-none font-extrabold tracking-[-0.03em] wider sm:text-[56px]"
          >
            Topics
          </h1>
          <p className="m-0 text-base leading-relaxed text-ink2 sm:text-[17px]">
            Each text is tagged with every topic it touches, using the keyword rules at the bottom of this page, so one
            text can count toward two topics.
          </p>
        </div>
        <Segmented label="Time range" value={range} onChange={setRange} options={RANGES} />
      </section>

      {!data ? (
        error ? (
          <EmptyState>Could not load topics. Retrying.</EmptyState>
        ) : (
          <Skeleton height={560} />
        )
      ) : (
        <>
          <TopicLandscape topics={topics} texts={data.texts} selected={selectedId} onSelect={setChosen} />
          <section aria-labelledby="ledger-h" className="flex flex-col gap-4">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <h2 id="ledger-h" className="m-0 text-[22px] font-bold">
                Topic ledger
              </h2>
              <span className="text-[13px] text-ink3">
                {range === "all"
                  ? "Sorted by volume."
                  : "Sorted by volume. Change compares with the previous period of the same length."}{" "}
                Select a row to inspect it.
              </span>
            </div>
            <TopicLedger topics={topics} selected={selectedId} onSelect={setChosen} />
          </section>
          <section
            aria-label="Topics by source and spotlight"
            className="grid grid-cols-[repeat(auto-fit,minmax(min(520px,100%),1fr))] gap-4"
          >
            <TopicMatrix topics={topics} platforms={platforms} />
            {selected && (
              <TopicSpotlight topic={selected} range={range} label={chosen ? "SPOTLIGHT" : fallback.label} />
            )}
          </section>
          <section aria-labelledby="rules-h" className="flex flex-col gap-4 pt-6">
            <div className="flex flex-col gap-1">
              <h2 id="rules-h" className="m-0 text-[22px] font-bold">
                How topics are assigned
              </h2>
              <p className="m-0 max-w-[760px] text-sm text-ink2">
                Keyword rules, applied after relevance filtering, so weapons, medicine and idioms never reach this page.
              </p>
            </div>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(280px,100%),1fr))] gap-3">
              {topics.map((t) => (
                <Panel key={t.id} as="div" className="flex flex-col gap-2 rounded-xl px-[18px] py-4">
                  <span className="text-sm font-[650]">{t.name}</span>
                  <span className="num text-xs leading-relaxed text-ink2">{t.keywords.join(", ")}</span>
                </Panel>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
