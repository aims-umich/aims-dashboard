import Ternary from "../components/charts/Ternary"
import { EmptyState, Panel, PanelHeader, Skeleton } from "../components/ui/Panel"
import { formatNumber, formatPercent } from "../lib/format"
import { MODEL_ACCURACY, PLATFORMS } from "../lib/platforms"
import { SENTIMENT_LABELS, SENTIMENT_VARS, SENTIMENTS } from "../lib/sentiment"
import { useStatus } from "../lib/statusContext"
import { useDocumentTitle } from "../lib/useDocumentTitle"
import { usePolling } from "../lib/usePolling"

// Mistakes found in live data, kept by hand as examples; each one became a filter change or a test case.
const FAILURES = [
  {
    tag: "TONE IS NOT STANCE",
    title: "Grateful words, critical message",
    body: "The model reads emotional tone. A post that opposes nuclear projects in warm, thankful language comes out positive.",
    quote:
      "Nuclear projects including uranium mining, reactors, & waste impinge on traditional Indigenous lands. We're grateful for the life-affirming values and spiritual guidance…",
    label: "Bluesky · scored positive, 95%",
    status: "Open · needs a stance-aware model",
  },
  {
    tag: "RELEVANCE LEAK",
    title: "Sports coverage slipped through",
    body: "The Guardian search matched a tennis report because of “a nuclear forehand”. Articles now need to be about energy somewhere before any of their sentences count.",
    quote: "Alexander Zverev clinches Laver Cup for Team Europe with victory over Learner Tien.",
    label: "The Guardian · scored positive, 99.8%",
    status: "Filter added 30 Sep 2026",
  },
  {
    tag: "AUTOMATED ACCOUNTS",
    title: "Bot output counted as opinion",
    body: "An account posts raw language-model output, reasoning tags and all. Text like this is now dropped before scoring on every platform.",
    quote:
      "<think> The post is about a startup wanting to build a massive nuclear-powered data center on public land in Utah…",
    label: "Bluesky · scored positive, 90% and 99%",
    status: "Filter added 30 Sep 2026",
  },
]

function Strip({ data, status }) {
  const model = data.model
  const accuracy = model ? MODEL_ACCURACY[model.name] : null
  const jobs = (status?.platforms ?? []).flatMap((p) => p.jobs)
  const healthy = jobs.filter((j) => j.state === "ok").length
  return (
    <section
      aria-label="Model at a glance"
      className="flex flex-wrap items-center gap-x-8 gap-y-3 rounded-2xl border border-line bg-panel px-6 py-[18px] text-[13px] text-ink2"
    >
      <span className="flex items-center gap-2">
        <span className="h-[7px] w-[7px] rounded-full bg-glow" aria-hidden="true" />
        <span className="num text-ink">{model?.name ?? "no active model"}</span>
      </span>
      {accuracy && (
        <span>
          <span className="num text-ink">{formatPercent(accuracy, 1)}</span> held-out accuracy
        </span>
      )}
      <span>
        <span className="num text-ink">{formatPercent(data.confidence, 1)}</span> average confidence
      </span>
      <span>
        <span className="num text-ink">{data.scored ? formatPercent(data.close_calls / data.scored, 1) : "-"}</span>{" "}
        close calls
      </span>
      <span>
        <span className="num text-ink">{formatNumber(status?.scorer?.backlog)}</span> texts waiting
      </span>
      {jobs.length > 0 && (
        <span className="sm:ml-auto">
          {healthy === jobs.length
            ? `All ${jobs.length} collectors healthy`
            : `${healthy} of ${jobs.length} collectors healthy`}
        </span>
      )}
    </section>
  )
}

function CloseCallsByLabel({ byLabel, threshold }) {
  const rows = SENTIMENTS.map((s) => ({ s, ...(byLabel[s] ?? { n: 0, close: 0 }) })).map((r) => ({
    ...r,
    share: r.n ? r.close / r.n : 0,
  }))
  const max = Math.max(0.01, ...rows.map((r) => r.share))
  return (
    <Panel className="flex flex-col gap-4 p-6">
      <PanelHeader
        level={3}
        title="Close calls by label"
        caption={`Share of each label whose top probability is under ${Math.round(threshold * 100)}%.`}
      />
      {rows.map((r) => (
        <div key={r.s} className="grid grid-cols-[84px_minmax(0,1fr)_110px] items-center gap-3">
          <span className="flex items-center gap-2 text-[13px]">
            <span
              className="h-[9px] w-[9px] rounded-full"
              style={{ background: SENTIMENT_VARS[r.s] }}
              aria-hidden="true"
            />
            {SENTIMENT_LABELS[r.s]}
          </span>
          <span className="h-3.5 rounded-r bg-ink3" style={{ width: `${(r.share / max) * 100}%` }} />
          <span className="num text-right text-xs">
            {formatPercent(r.share, 0)} of {formatNumber(r.n)}
          </span>
        </div>
      ))}
    </Panel>
  )
}

function ClosestCalls({ items }) {
  return (
    <Panel className="flex flex-col gap-1 p-6">
      <h3 className="m-0 mb-2 text-lg font-bold">Closest calls</h3>
      {items.length ? (
        items.map((c, i) => {
          const p = c.probabilities
          const ranked = SENTIMENTS.map((s) => [s, p[s]]).sort((a, b) => b[1] - a[1])
          return (
            <div key={i} className="flex flex-col gap-2 border-t border-line py-3.5">
              <div className="flex justify-between gap-3 text-xs text-ink3">
                <span className="font-semibold text-ink2">{PLATFORMS[c.platform]?.name}</span>
                <span className="num">
                  {ranked.map(([s, v]) => `${s.slice(0, 3)} ${Math.round(v * 100)}`).join(" · ")}
                </span>
              </div>
              <p className="m-0 line-clamp-3 text-sm leading-normal">{c.text}</p>
              <div className="flex h-1.5 gap-[2px]" aria-hidden="true">
                {SENTIMENTS.map((s) =>
                  p[s] > 0.004 ? (
                    <span
                      key={s}
                      className="rounded-[2px]"
                      style={{ width: `${p[s] * 100}%`, background: SENTIMENT_VARS[s] }}
                    />
                  ) : null,
                )}
              </div>
            </div>
          )
        })
      ) : (
        <EmptyState height={120}>No close calls among recent posts.</EmptyState>
      )}
    </Panel>
  )
}

function ConfidenceBySource({ rows, edges, threshold }) {
  return (
    <Panel className="flex flex-col gap-4 p-6">
      <PanelHeader
        title="Confidence by source"
        caption={`Texts in each confidence band, by source, each on its own scale. The number is the share of close calls, under ${Math.round(threshold * 100)}%.`}
      />
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(200px,100%),1fr))] gap-4">
        {rows.map((r) => {
          const max = Math.max(1, ...r.bins)
          return (
            <div key={r.platform} className="flex flex-col gap-2.5 rounded-xl bg-panel2 p-4">
              <div className="flex items-baseline justify-between">
                <span className="text-sm font-[650]">{PLATFORMS[r.platform]?.name}</span>
                <span className="num text-lg font-medium">{formatPercent(r.close / r.n, 1)}</span>
              </div>
              <div className="grid h-[90px] grid-cols-7 items-end gap-[3px] border-b border-line2">
                {r.bins.map((count, i) => (
                  <div
                    key={i}
                    className="relative overflow-hidden rounded-t-[3px] bg-ink3"
                    title={`${Math.round(edges[i] * 100)} to ${Math.round(edges[i + 1] * 100)}%: ${count}`}
                    style={{ height: `${(count / max) * 100}%`, minHeight: count ? 2 : 0 }}
                  >
                    {edges[i + 1] <= threshold + 1e-6 && <span className="hatch absolute inset-0" />}
                  </div>
                ))}
              </div>
              <div className="num flex justify-between text-[10px] text-ink3">
                <span>33%</span>
                <span>100%</span>
              </div>
            </div>
          )
        })}
      </div>
    </Panel>
  )
}

export default function Model() {
  useDocumentTitle("Model")
  const { data, error } = usePolling("/model", 300_000)
  const { data: status } = useStatus()
  return (
    <div className="flex flex-col gap-6">
      <section aria-labelledby="mod-h" className="flex flex-col gap-4 border-b border-line pt-14 pb-8">
        <span className="num text-xs tracking-[0.1em] text-glow">MODEL</span>
        <h1 id="mod-h" className="m-0 text-[40px] leading-none font-extrabold tracking-[-0.03em] wider sm:text-[56px]">
          Model
        </h1>
      </section>
      {!data ? (
        error ? (
          <EmptyState>Could not load the model overview. Retrying.</EmptyState>
        ) : (
          <Skeleton height={600} />
        )
      ) : (
        <>
          <Strip data={data} status={status} />
          <section
            aria-labelledby="tern-h"
            className="grid grid-cols-[repeat(auto-fit,minmax(min(520px,100%),1fr))] gap-4"
          >
            <Panel className="flex flex-col gap-4 p-6">
              <PanelHeader
                id="tern-h"
                title="Where the model hesitates"
                caption={`The ${data.sample.length} most recent texts, placed by their three probabilities. A text in a corner is a confident call. The dashed lines are where the label flips.`}
              />
              <Ternary sample={data.sample} />
            </Panel>
            <div className="flex min-w-0 flex-col gap-4">
              <CloseCallsByLabel byLabel={data.by_label} threshold={data.close_call_below} />
              <ClosestCalls items={data.closest} />
            </div>
          </section>
          <ConfidenceBySource rows={data.by_platform} edges={data.bin_edges} threshold={data.close_call_below} />
          <section aria-labelledby="fail-h" className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <h2 id="fail-h" className="m-0 text-[22px] font-bold">
                Known failure modes
              </h2>
              <p className="m-0 text-sm text-ink2">Mistakes found in live data, with what happened to each.</p>
            </div>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(360px,100%),1fr))] gap-4">
              {FAILURES.map((f) => (
                <Panel key={f.tag} as="article" className="flex flex-col gap-3 p-6">
                  <span className="num text-[11px] tracking-[0.1em] text-ink3">{f.tag}</span>
                  <h3 className="m-0 text-[19px] font-bold">{f.title}</h3>
                  <p className="m-0 text-sm leading-relaxed text-ink2">{f.body}</p>
                  <blockquote className="m-0 rounded-[10px] bg-panel2 px-4 py-3.5 text-sm leading-normal">
                    {f.quote}
                  </blockquote>
                  <div className="mt-auto flex justify-between gap-3 text-xs">
                    <span className="text-ink3">{f.label}</span>
                    <span className="font-semibold">{f.status}</span>
                  </div>
                </Panel>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
