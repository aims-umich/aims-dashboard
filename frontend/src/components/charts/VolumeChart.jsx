import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { formatBucket, formatNumber } from "../../lib/format"
import { Card, EmptyState } from "../ui/Card"
import ChartTooltip from "./ChartTooltip"

export default function VolumeChart({ trend, bucket, title, seriesName, accent }) {
  const hasData = trend.some((row) => row.documents > 0)
  return (
    <Card title={title} subtitle={`Per ${bucket}`}>
      {hasData ? (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={trend} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="bucket" tickFormatter={(b) => formatBucket(b, bucket)} tick={{ fontSize: 12 }} minTickGap={24} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={formatNumber} allowDecimals={false} width={48} />
            <Tooltip
              content={<ChartTooltip labelFormatter={(b) => formatBucket(b, bucket)} valueFormatter={formatNumber} />}
              cursor={{ fillOpacity: 0.1 }}
            />
            <Bar dataKey="documents" name={seriesName} fill={accent} radius={[3, 3, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <EmptyState height={280}>Nothing collected in this range yet.</EmptyState>
      )}
    </Card>
  )
}
