import { ExternalLink } from "lucide-react"
import { useState } from "react"
import { getJson } from "../../lib/api"
import { formatCompact, formatDateTime, timeAgo } from "../../lib/format"
import { SENTIMENT_LABELS, SENTIMENT_VARS, SENTIMENTS } from "../../lib/sentiment"
import { usePolling } from "../../lib/usePolling"
import { EmptyState, Skeleton } from "../ui/Panel"
import { isMixed } from "../../lib/highlights"
import PostText from "./PostText"

const PAGE = 15
const FILTERS = [{ value: "all", label: "All" }, ...SENTIMENTS.map((s) => ({ value: s, label: SENTIMENT_LABELS[s] }))]

function Probabilities({ item }) {
  const p = item.probabilities
  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-sm font-semibold">
          <span
            className="h-2.5 w-2.5 rounded-full"
            style={{ background: SENTIMENT_VARS[item.sentiment] }}
            aria-hidden="true"
          />
          {SENTIMENT_LABELS[item.sentiment]}
        </span>
        <span className="num text-[13px] text-ink2">{(item.confidence * 100).toFixed(1)}%</span>
      </div>
      <div className="flex h-2 gap-[2px]" aria-hidden="true">
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
      <div className="num grid grid-cols-3 text-[11px] text-ink3">
        <span>pos {(p.positive * 100).toFixed(0)}%</span>
        <span className="text-center">neu {(p.neutral * 100).toFixed(0)}%</span>
        <span className="text-right">neg {(p.negative * 100).toFixed(0)}%</span>
      </div>
    </div>
  )
}

function PostRow({ item, fields, config }) {
  const article = config.articles
  // The attribution measures the pull toward positive versus negative, which explains those two labels only.
  const highlights = !article && item.sentiment !== "neutral" ? item.highlights : null
  const metrics = fields.filter((f) => item.metrics?.[f.key] != null)
  return (
    <article className="grid grid-cols-1 gap-4 border-b border-line px-6 py-5 last:border-b-0 md:grid-cols-[minmax(0,1fr)_260px] md:gap-8">
      <div className="flex min-w-0 flex-col gap-2.5">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-ink3">
          {item.author && <span className="max-w-[18rem] truncate font-semibold text-ink2">{item.author}</span>}
          <time dateTime={item.published_at} title={formatDateTime(item.published_at)}>
            {timeAgo(item.published_at)}
          </time>
          {item.parent?.title && (
            <a
              href={item.parent.url}
              target="_blank"
              rel="noopener noreferrer"
              className="max-w-[24rem] truncate text-ink3 hover:text-ink"
            >
              on “{item.parent.title}”
            </a>
          )}
          {article && item.segments > 1 && <span>{item.segments} sentences scored</span>}
        </div>
        {article && item.title && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-base font-semibold text-ink no-underline hover:underline"
          >
            {item.title}
          </a>
        )}
        <PostText
          text={item.text}
          highlights={highlights}
          className={
            article ? "line-clamp-2 text-[15px] leading-relaxed text-ink2" : "line-clamp-6 text-base leading-[1.7]"
          }
        />
        <div className="num flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink3">
          {metrics.map((f) => (
            <span key={f.key}>
              {formatCompact(item.metrics[f.key])} {f.label.toLowerCase()}
            </span>
          ))}
          {item.url && !article && (
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 font-sans text-ink2 underline hover:text-ink"
            >
              {config.viewLabel ?? "View"} <ExternalLink size={12} aria-hidden="true" />
            </a>
          )}
        </div>
      </div>
      <div className="flex flex-col gap-2.5">
        <Probabilities item={item} />
        {isMixed(highlights) && (
          <span className="self-start rounded-full border border-line2 px-2.5 py-1 text-xs text-ink2">
            Mixed signals: words pulled both ways
          </span>
        )}
      </div>
    </article>
  )
}

export default function RecentPosts({ platform, config, fields, regionQuery = "" }) {
  const [sentiment, setSentiment] = useState("all")
  const query = `/platforms/${platform}/posts?limit=${PAGE}${sentiment === "all" ? "" : `&sentiment=${sentiment}`}${regionQuery}`
  const { data, error } = usePolling(query)
  // Pages loaded with "Load more" belong to one first page; a new filter or newer items reset them.
  const head = `${query}|${data?.items?.[0]?.id ?? ""}`
  const [loaded, setLoaded] = useState({ head: null, items: [], cursor: undefined, loading: false })
  const more = loaded.head === head ? loaded : { head, items: [], cursor: undefined, loading: false }
  const items = [...(data?.items ?? []), ...more.items]
  const cursor = more.cursor === undefined ? data?.next_cursor : more.cursor
  const showHighlights = !config.articles && items.some((i) => i.sentiment !== "neutral" && i.highlights?.length)

  const loadMore = async () => {
    setLoaded({ ...more, loading: true })
    try {
      const page = await getJson(`${query}&before=${encodeURIComponent(cursor)}`)
      setLoaded({ head, items: [...more.items, ...page.items], cursor: page.next_cursor, loading: false })
    } catch {
      setLoaded({ ...more, loading: false })
    }
  }

  return (
    <section aria-labelledby="posts-h" className="flex flex-col gap-4 pt-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-2">
          <span className="num text-xs tracking-[0.1em] text-glow">READ THE SOURCE</span>
          <h2 id="posts-h" className="m-0 text-[28px] font-[750] tracking-[-0.015em] wide">
            {config.articles ? "Recent articles" : `Recent ${config.unitLabel}`}
          </h2>
        </div>
        <div role="radiogroup" aria-label="Filter by sentiment" className="flex flex-wrap gap-2">
          {FILTERS.map((f) => {
            const active = f.value === sentiment
            return (
              <button
                key={f.value}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setSentiment(f.value)}
                className={`min-h-[38px] rounded-full border px-3.5 text-[13px] ${
                  active
                    ? "border-ink bg-ink font-semibold text-bg"
                    : "border-line2 bg-transparent font-medium text-ink2 hover:text-ink"
                }`}
              >
                {f.label}
              </button>
            )
          })}
        </div>
      </div>
      {showHighlights && (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-[13px] text-ink2">
          <span className="flex items-center gap-2">
            <span className="border-b-2 border-pos bg-posw px-1">word</span>pushed toward positive
          </span>
          <span className="flex items-center gap-2">
            <span className="border-b-2 border-neg bg-negw px-1">word</span>pushed toward negative
          </span>
          <span className="text-ink3">Measured from the model&apos;s own gradients when each post is scored.</span>
        </div>
      )}
      <div className="overflow-hidden rounded-2xl border border-line bg-panel">
        {!data && !error && <Skeleton height={420} className="rounded-none" />}
        {error && !data && (
          <EmptyState height={200}>Could not load {config.unitLabel}. Retrying every minute.</EmptyState>
        )}
        {data && !items.length && (
          <EmptyState height={200}>
            No {sentiment === "all" ? "" : `${sentiment} `}
            {config.articles ? "articles" : config.unitLabel} yet.
          </EmptyState>
        )}
        {items.map((item) => (
          <PostRow key={item.id} item={item} fields={fields} config={config} />
        ))}
        {cursor && (
          <div className="flex justify-center border-t border-line p-4">
            <button
              type="button"
              onClick={loadMore}
              disabled={more.loading}
              className="min-h-11 rounded-[10px] border border-line2 bg-transparent px-5 text-sm font-semibold text-ink disabled:opacity-60"
            >
              {more.loading ? "Loading…" : "Load more"}
            </button>
          </div>
        )}
      </div>
      {config.listNote && <p className="m-0 text-xs text-ink3">{config.listNote}</p>}
    </section>
  )
}
