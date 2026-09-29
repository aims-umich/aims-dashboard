import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { formatNumber, formatPercent } from "../../lib/format"
import { Card, EmptyState } from "../ui/Card"
import ChartTooltip from "./ChartTooltip"

export default function ConfidenceHistogram({ bins, avgConfidence, unit }) {
  const data = bins.map((b) => ({ ...b, label: `${Math.round(b.from * 100)}-${Math.round(b.to * 100)}%` }))
  const total = bins.reduce((sum, b) => sum + b.count, 0)
  return (
    <Card
      title="Model confidence"
      subtitle={
        total
          ? `How sure the model is about each label · average ${formatPercent(avgConfidence)}`
          : "How sure the model is about each label"
      }
    >
      {total ? (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={0} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={formatNumber} allowDecimals={false} width={48} />
            <Tooltip content={<ChartTooltip valueFormatter={formatNumber} />} cursor={{ fillOpacity: 0.1 }} />
            <Bar dataKey="count" name={`Scored ${unit}`} fill="#6366F1" radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <EmptyState height={280}>No scored {unit} in this range yet.</EmptyState>
      )}
    </Card>
  )
}
