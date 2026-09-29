import { useMemo, useState } from "react"
import { TagCloud } from "react-tagcloud"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { formatNumber } from "../../lib/format"
import { SENTIMENTS, SENTIMENT_COLORS, SENTIMENT_LABELS } from "../../lib/sentiment"
import { usePolling } from "../../lib/usePolling"
import { Card, EmptyState, Skeleton } from "../ui/Card"
import SegmentedControl from "../ui/SegmentedControl"
import ChartTooltip from "./ChartTooltip"

export default function WordPanels({ platform, range, unit }) {
  const { data, error } = usePolling(`/platforms/${platform}/words?range=${range}`, 300_000)
  const [tab, setTab] = useState("positive")
  const words = data?.[tab] ?? []
  // Alphabetical order keeps the cloud stable between polls instead of reshuffling it.
  const cloud = useMemo(
    () => [...(data?.cloud ?? [])].map((t) => ({ ...t, key: t.value })).sort((a, b) => a.value.localeCompare(b.value)),
    [data],
  )
  const maxCount = Math.max(1, ...cloud.map((t) => t.count))

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card
        title="Top words by sentiment"
        subtitle={data ? `From the ${formatNumber(data.sampled)} most recent scored ${unit}` : " "}
        actions={
          <SegmentedControl
            label="Sentiment"
            value={tab}
            onChange={setTab}
            options={SENTIMENTS.map((s) => ({ value: s, label: SENTIMENT_LABELS[s] }))}
          />
        }
      >
        {!data && !error && <Skeleton height={300} />}
        {error && !data && <EmptyState height={300}>Could not load words.</EmptyState>}
        {data &&
          (words.length ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={words} layout="vertical" margin={{ top: 0, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                <YAxis type="category" dataKey="word" width={96} tick={{ fontSize: 12 }} interval={0} />
                <Tooltip content={<ChartTooltip valueFormatter={formatNumber} />} cursor={{ fillOpacity: 0.1 }} />
                <Bar
                  dataKey="count"
                  name={`${SENTIMENT_LABELS[tab]} ${unit}`}
                  fill={SENTIMENT_COLORS[tab]}
                  radius={[0, 3, 3, 0]}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState height={300}>No {SENTIMENT_LABELS[tab].toLowerCase()} {unit} in this range.</EmptyState>
          ))}
      </Card>
      <Card title="Word cloud" subtitle="Most common words across all sentiments">
        {!data && !error && <Skeleton height={300} />}
        {error && !data && <EmptyState height={300}>Could not load words.</EmptyState>}
        {data &&
          (cloud.length ? (
            <div className="flex h-[300px] items-center justify-center overflow-hidden px-2">
              <TagCloud
                minSize={12}
                maxSize={30}
                tags={cloud}
                shuffle={false}
                className="text-center leading-tight"
                renderer={(tag, size) => (
                  <span
                    key={tag.value}
                    className="inline-block px-1.5 py-0.5 transition-transform hover:scale-110"
                    style={{
                      fontSize: size,
                      fontWeight: tag.count > maxCount * 0.5 ? 700 : 500,
                      color: tag.count > maxCount * 0.5 ? "#6366F1" : tag.count > maxCount * 0.25 ? "#8B5CF6" : "#9CA3AF",
                    }}
                    title={`${tag.value}: ${formatNumber(tag.count)}`}
                  >
                    {tag.value}
                  </span>
                )}
              />
            </div>
          ) : (
            <EmptyState height={300}>No words in this range yet.</EmptyState>
          ))}
      </Card>
    </div>
  )
}
