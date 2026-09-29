import { useMemo, useState } from "react"
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { formatBucket, formatNumber } from "../../lib/format"
import { SENTIMENTS, SENTIMENT_COLORS, SENTIMENT_LABELS } from "../../lib/sentiment"
import { Card, EmptyState } from "../ui/Card"
import SegmentedControl from "../ui/SegmentedControl"
import ChartTooltip from "./ChartTooltip"

export default function SentimentTrend({ trend, bucket, unit }) {
  const [mode, setMode] = useState("share")
  const data = useMemo(
    () =>
      trend.map((row) => {
        const total = row.positive + row.neutral + row.negative
        if (mode === "count") return { ...row, total }
        return {
          bucket: row.bucket,
          total,
          ...Object.fromEntries(SENTIMENTS.map((s) => [s, total ? row[s] / total : null])),
        }
      }),
    [trend, mode],
  )
  const hasData = trend.some((row) => row.positive + row.neutral + row.negative > 0)
  const share = mode === "share"

  return (
    <Card
      title="Sentiment over time"
      subtitle={share ? `Share of scored ${unit} per ${bucket}` : `Scored ${unit} per ${bucket}`}
      actions={
        <SegmentedControl
          label="Trend units"
          value={mode}
          onChange={setMode}
          options={[
            { value: "share", label: "Share" },
            { value: "count", label: "Count" },
          ]}
        />
      }
    >
      {hasData ? (
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="bucket"
              tickFormatter={(b) => formatBucket(b, bucket)}
              tick={{ fontSize: 12 }}
              minTickGap={24}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              domain={share ? [0, 1] : [0, "auto"]}
              tickFormatter={share ? (v) => `${Math.round(v * 100)}%` : formatNumber}
              allowDecimals={!share}
              width={48}
            />
            <Tooltip
              content={
                <ChartTooltip
                  labelFormatter={(b) => formatBucket(b, bucket)}
                  valueFormatter={(v) => (v == null ? "-" : share ? `${(v * 100).toFixed(1)}%` : formatNumber(v))}
                />
              }
            />
            <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
            {SENTIMENTS.map((s) => (
              <Area
                key={s}
                type="linear"
                dataKey={s}
                name={SENTIMENT_LABELS[s]}
                stackId="1"
                stroke={SENTIMENT_COLORS[s]}
                fill={SENTIMENT_COLORS[s]}
                fillOpacity={0.35}
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <EmptyState height={300}>No scored {unit} in this range yet.</EmptyState>
      )}
    </Card>
  )
}
