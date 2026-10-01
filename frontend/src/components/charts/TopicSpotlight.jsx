import { formatDate, formatSigned } from "../../lib/format"
import { PLATFORMS } from "../../lib/platforms"
import { SENTIMENT_LABELS, SENTIMENT_VARS } from "../../lib/sentiment"
import { usePolling } from "../../lib/usePolling"
import { Panel, Skeleton } from "../ui/Panel"
import Sparkbars from "./Sparkbars"

const NET_H = 70

/** One topic up close: weekly volume, net sentiment underneath, its words, and two example texts. */
export default function TopicSpotlight({ topic, range, label }) {
  const { data } = usePolling(`/topics/${topic.id}?range=${range}`, 300_000)
  const weeks = data?.weeks ?? []
  const N = weeks.length
  const x = (i) => ((i + 0.5) / Math.max(1, N)) * 600
  const y = (v) => NET_H / 2 - (Math.max(-0.6, Math.min(0.6, v)) / 0.6) * (NET_H / 2 - 4)
  let line = ""
  let open = false
  weeks.forEach((w, i) => {
    if (w.net_sentiment == null || w.count < 5) {
      open = false
      return
    }
    line += `${open ? "L" : "M"}${x(i).toFixed(1)} ${y(w.net_sentiment).toFixed(1)}`
    open = true
  })
  return (
    <Panel className="flex flex-col gap-5 border-glow p-6">
      <div className="flex flex-col gap-1">
        <span className="num text-[11px] tracking-[0.1em] text-glow">{label}</span>
        <h2 className="m-0 text-[22px] font-bold">{topic.name}</h2>
        <span className="text-sm text-ink2">Texts per week, and net sentiment underneath on its own scale.</span>
      </div>
      {!data ? (
        <Skeleton height={320} />
      ) : (
        <>
          <div className="flex flex-col gap-1.5">
            <Sparkbars values={weeks.map((w) => w.count)} height={110} />
            <div className="relative border-t border-line" style={{ height: NET_H }}>
              <div className="absolute inset-x-0 h-px bg-line2" style={{ top: NET_H / 2 }} />
              <svg
                viewBox={`0 0 600 ${NET_H}`}
                preserveAspectRatio="none"
                aria-hidden="true"
                className="absolute inset-0 h-full w-full"
              >
                <path
                  d={line}
                  fill="none"
                  stroke="var(--ink)"
                  strokeWidth="2"
                  vectorEffect="non-scaling-stroke"
                  strokeLinejoin="round"
                />
              </svg>
              <span className="num absolute top-0.5 left-0 text-[10px] text-ink3">+0.6</span>
              <span className="num absolute bottom-0 left-0 text-[10px] text-ink3">{"−"}0.6</span>
            </div>
            <div className="num flex justify-between text-[11px] text-ink3">
              <span>Week of {weeks[0] ? formatDate(weeks[0].week) : ""}</span>
              <span>This week</span>
            </div>
          </div>
          {data.words.length > 0 && (
            <div className="flex flex-wrap gap-2">
              <span className="w-full text-xs text-ink3">Words that travel with this topic</span>
              {data.words.map((w) => (
                <span key={w.word} className="rounded-lg border border-line2 bg-panel2 px-2.5 py-1.5 text-[13px]">
                  {w.word}
                </span>
              ))}
            </div>
          )}
          {data.examples.length > 0 && (
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(220px,100%),1fr))] gap-3">
              {data.examples.map((e) => (
                <blockquote key={e.url ?? e.text} className="m-0 flex flex-col gap-2.5 rounded-xl bg-panel2 p-4">
                  <span className="flex items-center gap-2 text-xs font-semibold">
                    <span
                      className="h-[9px] w-[9px] rounded-full"
                      style={{ background: SENTIMENT_VARS[e.sentiment] }}
                      aria-hidden="true"
                    />
                    {SENTIMENT_LABELS[e.sentiment]} · {PLATFORMS[e.platform]?.name} · {Math.round(e.confidence * 100)}%
                    sure
                  </span>
                  <span className="line-clamp-5 text-sm leading-relaxed text-ink2">{e.text}</span>
                  {e.url && (
                    <a href={e.url} target="_blank" rel="noopener noreferrer" className="text-xs text-ink2 underline">
                      Read the original
                    </a>
                  )}
                </blockquote>
              ))}
            </div>
          )}
          <span className="text-xs text-ink3">
            Overall net sentiment {formatSigned(topic.net_sentiment)} across {topic.count} texts.
          </span>
        </>
      )}
    </Panel>
  )
}
