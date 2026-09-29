import { ExternalLink } from "lucide-react"
import { useEffect, useState } from "react"
import { getJson } from "../lib/api"
import { formatCompact, formatDateTime } from "../lib/format"
import { SENTIMENTS, SENTIMENT_LABELS } from "../lib/sentiment"
import { usePolling } from "../lib/usePolling"
import { Card, EmptyState, Skeleton } from "./ui/Card"
import SegmentedControl from "./ui/SegmentedControl"
import SentimentPill from "./ui/SentimentPill"

const PAGE = 15

function Engagement({ metrics, fields }) {
  const parts = fields.filter((f) => metrics?.[f.key] != null).map((f) => `${formatCompact(metrics[f.key])} ${f.label.toLowerCase()}`)
  if (!parts.length) return null
  return <span>{parts.join(" · ")}</span>
}

function PostRow({ item, fields, isArticle }) {
  const heading = isArticle ? item.title : null
  return (
    <li className="px-5 py-4">
      <div className="flex items-start gap-4">
        <div className="min-w-0 flex-1">
          {heading &&
            (item.url ? (
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-gray-900 hover:underline dark:text-white"
              >
                {heading}
              </a>
            ) : (
              <p className="font-medium text-gray-900 dark:text-white">{heading}</p>
            ))}
          {item.text && (
            <p
              className={`whitespace-pre-line break-words text-sm text-gray-700 dark:text-gray-300 ${
                heading ? "mt-1 line-clamp-2" : "line-clamp-4"
              }`}
            >
              {item.text}
            </p>
          )}
          <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
            <time dateTime={item.published_at}>{formatDateTime(item.published_at)}</time>
            {item.author && <span className="max-w-[16rem] truncate">{item.author}</span>}
            {item.parent?.title && (
              <a href={item.parent.url} target="_blank" rel="noopener noreferrer" className="max-w-[22rem] truncate hover:underline">
                on “{item.parent.title}”
              </a>
            )}
            {isArticle && item.segments > 1 && <span>{item.segments} sentences scored</span>}
            <Engagement metrics={item.metrics} fields={fields} />
            {item.url && !isArticle && (
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 hover:text-gray-900 dark:hover:text-white"
              >
                View <ExternalLink size={12} aria-hidden="true" />
              </a>
            )}
          </p>
        </div>
        <SentimentPill sentiment={item.sentiment} confidence={item.confidence} />
      </div>
    </li>
  )
}

export default function RecentPosts({ platform, fields, isArticle, title }) {
  const [sentiment, setSentiment] = useState("all")
  const query = `/platforms/${platform}/posts?limit=${PAGE}${sentiment === "all" ? "" : `&sentiment=${sentiment}`}`
  const { data, error } = usePolling(query)
  const [more, setMore] = useState({ items: [], cursor: undefined, loading: false })

  // A new filter, or a poll that brings in newer items, resets anything loaded with "Show more".
  const head = `${query}|${data?.items?.[0]?.id ?? ""}`
  useEffect(() => setMore({ items: [], cursor: undefined, loading: false }), [head])

  const items = [...(data?.items ?? []), ...more.items]
  const cursor = more.cursor === undefined ? data?.next_cursor : more.cursor

  const loadMore = async () => {
    setMore((m) => ({ ...m, loading: true }))
    try {
      const page = await getJson(`${query}&before=${encodeURIComponent(cursor)}`)
      setMore((m) => ({ items: [...m.items, ...page.items], cursor: page.next_cursor, loading: false }))
    } catch {
      setMore((m) => ({ ...m, loading: false }))
    }
  }

  return (
    <Card
      title={title}
      subtitle="Newest first, with the model's label and confidence"
      flush
      actions={
        <SegmentedControl
          label="Filter by sentiment"
          value={sentiment}
          onChange={setSentiment}
          options={[{ value: "all", label: "All" }, ...SENTIMENTS.map((s) => ({ value: s, label: SENTIMENT_LABELS[s] }))]}
        />
      }
    >
      {!data && !error && (
        <div className="px-5 pb-5">
          <Skeleton height={320} />
        </div>
      )}
      {error && !data && <EmptyState height={200}>Could not load recent items.</EmptyState>}
      {data &&
        (items.length ? (
          <>
            <ul className="divide-y divide-gray-100 dark:divide-gray-700/70">
              {items.map((item) => (
                <PostRow key={item.id} item={item} fields={fields} isArticle={isArticle} />
              ))}
            </ul>
            {cursor && (
              <div className="border-t border-gray-100 px-5 py-3 text-center dark:border-gray-700/70">
                <button
                  type="button"
                  onClick={loadMore}
                  disabled={more.loading}
                  className="text-sm font-medium text-indigo-600 hover:text-indigo-500 disabled:opacity-50 dark:text-indigo-400"
                >
                  {more.loading ? "Loading…" : "Show more"}
                </button>
              </div>
            )}
          </>
        ) : (
          <EmptyState height={200}>Nothing here yet.</EmptyState>
        ))}
    </Card>
  )
}
