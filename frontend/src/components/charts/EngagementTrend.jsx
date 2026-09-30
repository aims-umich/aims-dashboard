import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { formatBucket, formatNumber } from "../../lib/format"
import { Card, EmptyState } from "../ui/Card"
import ChartTooltip from "./ChartTooltip"

const COLORS = ["#10B981", "#6366F1", "#F59E0B", "#EC4899"]
const CHART_AREA = 280

export default function EngagementTrend({ engagement, bucket, unit }) {
  const { fields, trend, averages } = engagement
  const hasData = trend.length > 0
  // Split a fixed height between the small multiples so this card lines up with its neighbour.
  const chartHeight = Math.max(48, Math.floor((CHART_AREA - fields.length * 36) / fields.length))
  return (
    <Card
      title="Engagement"
      subtitle={`Average per ${unit.replace(/s$/, "")}, by ${bucket} of posting · counts refresh as they change`}
    >
      {hasData ? (
        <div className="flex flex-col justify-between gap-3" style={{ height: CHART_AREA }}>
          {fields.map((field, i) => (
            <div key={field.key}>
              <div className="mb-0.5 flex items-baseline justify-between text-sm">
                <span className="font-medium text-gray-700 dark:text-gray-200">{field.label}</span>
                <span className="tabular-nums text-gray-500 dark:text-gray-400">
                  avg {averages[field.key] == null ? "-" : averages[field.key].toFixed(1)}
                </span>
              </div>
              <ResponsiveContainer width="100%" height={chartHeight}>
                <LineChart data={trend} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="bucket" hide />
                  <YAxis tick={{ fontSize: 10 }} width={48} tickFormatter={formatNumber} allowDecimals={false} />
                  <Tooltip
                    content={
                      <ChartTooltip
                        labelFormatter={(b) => formatBucket(b, bucket)}
                        valueFormatter={(v) => (v == null ? "-" : v.toFixed(1))}
                      />
                    }
                  />
                  <Line
                    type="linear"
                    dataKey={field.key}
                    name={field.label}
                    stroke={COLORS[i % COLORS.length]}
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState height={CHART_AREA}>No engagement data in this range yet.</EmptyState>
      )}
    </Card>
  )
}
