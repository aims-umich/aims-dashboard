import { useState } from "react"
import { Link } from "react-router-dom"
import EventImpact from "../components/charts/EventImpact"
import EventsTimeline from "../components/charts/EventsTimeline"
import SpikeTable from "../components/charts/SpikeTable"
import { EmptyState, Panel, Skeleton } from "../components/ui/Panel"
import Segmented from "../components/ui/Segmented"
import { PLATFORM_ORDER, PLATFORMS } from "../lib/platforms"
import { useStatus } from "../lib/statusContext"
import { useDocumentTitle } from "../lib/useDocumentTitle"
import { usePolling } from "../lib/usePolling"

export default function Events() {
  useDocumentTitle("Events")
  const { data: status } = useStatus()
  const live = PLATFORM_ORDER.filter((k) => (status?.platforms ?? []).some((p) => p.platform === k))
  const [focus, setFocus] = useState("nyt")
  const { data, error } = usePolling(`/events?platform=${focus}`, 300_000)
  const config = PLATFORMS[focus]
  const noun = config.articles ? (focus === "guardian" ? "sentences" : "articles") : config.unitLabel
  const shifts = data?.events.filter((e) => e.verdict === "shift").length ?? 0

  return (
    <div className="flex flex-col gap-6">
      <section
        aria-labelledby="ev-h"
        className="flex flex-wrap items-end justify-between gap-6 border-b border-line pt-14 pb-8"
      >
        <div className="flex flex-col gap-4">
          <span className="num text-xs tracking-[0.1em] text-glow">EVENTS</span>
          <h1 id="ev-h" className="m-0 text-[40px] leading-none font-extrabold tracking-[-0.03em] wider sm:text-[56px]">
            Events
          </h1>
        </div>
        {live.length > 0 && (
          <Segmented
            label="Source"
            value={focus}
            onChange={setFocus}
            options={live.map((k) => ({ value: k, label: PLATFORMS[k].name }))}
          />
        )}
      </section>

      {!data ? (
        error ? (
          <EmptyState>Could not load events. Retrying.</EmptyState>
        ) : (
          <Skeleton height={560} />
        )
      ) : (
        <>
          {data.months.length > 1 ? (
            <EventsTimeline months={data.months} events={data.events} noun={noun} />
          ) : (
            <EmptyState height={220}>{config.name} does not have enough history for a timeline yet.</EmptyState>
          )}

          <section aria-labelledby="impact-h" className="flex flex-col gap-4">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div className="flex max-w-[760px] flex-col gap-1">
                <h2 id="impact-h" className="m-0 text-[22px] font-bold">
                  Event impact on {config.name}
                </h2>
                <p className="m-0 text-sm text-ink2">
                  Each event month against the six months before it. A shift counts when the event month&apos;s 95%
                  interval clears that baseline.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-4 text-xs text-ink2">
                <span className="flex items-center gap-1.5">
                  <span className="box-border h-2.5 w-2.5 rounded-full border-2 border-ink3" aria-hidden="true" />
                  Six months before
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-3 w-3 rounded-full bg-ink" aria-hidden="true" />
                  Event month, 95% interval
                </span>
                <span className="num text-ink3">
                  {shifts} OF {data.events.length} SHIFTS
                </span>
              </div>
            </div>
            <EventImpact events={data.events} noun={noun} />
          </section>

          <section aria-labelledby="spikes-h" className="flex flex-col gap-4">
            <div className="flex max-w-[800px] flex-col gap-1">
              <span className="num text-[11px] tracking-[0.1em] text-glow">DETECTED AUTOMATICALLY · EVERY SOURCE</span>
              <h2 id="spikes-h" className="m-0 text-[22px] font-bold">
                Detected spikes
              </h2>
              <p className="m-0 text-sm text-ink2">
                Months where a source&apos;s volume ran at least 2.5 times its six-month average, or its net sentiment
                jumped clear of its interval. The vertical tick marks the usual monthly volume; bars are scaled to 5
                times usual.
              </p>
            </div>
            <SpikeTable spikes={data.spikes} events={data.events} />
          </section>

          <Panel className="flex flex-col gap-4 p-6">
            <h2 className="m-0 text-[22px] font-bold">How events are chosen</h2>
            <p className="m-0 max-w-[80ch] text-[15px] leading-relaxed text-ink2">
              Events come from two places. The lab keeps a short, fixed list of widely covered nuclear-energy news,
              chosen before looking at any sentiment data so the list is not tuned to the spikes it lines up with. The
              spike detector then flags any month the list missed.
            </p>
            <p className="m-0 max-w-[80ch] text-[15px] leading-relaxed text-ink2">
              Months with fewer than 8 texts, or a baseline with fewer than 8, are marked too few to call.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/about"
                className="flex min-h-11 items-center rounded-[10px] border border-line2 px-[18px] text-sm font-semibold text-ink no-underline"
              >
                Read the method
              </Link>
              <a
                href="https://www.aims-umich.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex min-h-11 items-center rounded-[10px] border border-line2 px-[18px] text-sm font-semibold text-ink2 no-underline"
              >
                Suggest an event
              </a>
            </div>
          </Panel>
        </>
      )}
    </div>
  )
}
