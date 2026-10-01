import { useState } from "react"
import { formatNumber } from "../../lib/format"
import { Panel, PanelHeader } from "../ui/Panel"
import Segmented from "../ui/Segmented"

const ROWS = [
  ["positive", "Positive", "var(--pos)"],
  ["neutral", "Neutral", "var(--neu)"],
  ["negative", "Negative", "var(--neg)"],
]

function niceMax(value) {
  if (value <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(value))
  return [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= value)
}

/** Average engagement per post, by the post's sentiment, with 95% intervals of the mean. */
export default function EngagementBySentiment({ engagement, unit }) {
  const fields = engagement.fields
  const [metric, setMetric] = useState(fields[0]?.key)
  const field = fields.find((f) => f.key === metric) ?? fields[0]
  const rows = ROWS.map(([key, label, color]) => {
    const group = engagement.by_sentiment?.[key]
    const stat = group?.[field.key]
    const mean = stat?.mean ?? null
    const half = mean != null && group.n > 1 && stat.sd != null ? (1.96 * stat.sd) / Math.sqrt(group.n) : 0
    return {
      key,
      label,
      color,
      n: group?.n ?? 0,
      mean,
      lo: mean == null ? null : Math.max(0, mean - half),
      hi: mean == null ? null : mean + half,
    }
  })
  const max = niceMax(Math.max(...rows.map((r) => r.hi ?? 0)))
  const x = (v) => (v / max) * 100
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        title="Engagement by sentiment"
        caption={`Average ${field.label.toLowerCase()} per ${unit.replace(/s$/, "")}, by its sentiment. Lines show 95% intervals.`}
        actions={
          fields.length > 1 && (
            <Segmented
              size="sm"
              label="Engagement measure"
              value={field.key}
              onChange={setMetric}
              options={fields.map((f) => ({ value: f.key, label: f.label }))}
            />
          )
        }
      />
      <div className="grid grid-cols-[repeat(auto-fit,minmax(110px,1fr))] gap-3">
        {fields.map((f) => (
          <div key={f.key} className="flex flex-col gap-0.5 rounded-[10px] bg-panel2 px-3.5 py-3">
            <span className="text-xs text-ink2">{f.label}</span>
            <span className="num text-[22px] font-medium">{engagement.averages[f.key]?.toFixed(2) ?? "-"}</span>
            <span className="text-[11px] text-ink3">per {unit.replace(/s$/, "")}, all tones</span>
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-1">
        {rows.map((r) => (
          <div key={r.key} className="grid h-10 grid-cols-[96px_minmax(0,1fr)_64px] items-center gap-3">
            <span className="flex flex-col text-[13px] leading-tight text-ink2">
              {r.label}
              <span className="num text-[10px] text-ink3">n = {formatNumber(r.n)}</span>
            </span>
            <div className="relative h-10">
              <div className="absolute inset-y-0 left-0 w-px bg-line2" />
              {r.mean != null && (
                <>
                  <div
                    className="absolute top-3 h-4 rounded-r"
                    style={{ width: `${x(r.mean)}%`, background: r.color }}
                  />
                  <div
                    className="absolute top-[19px] h-[2px] bg-ink"
                    style={{ left: `${x(r.lo)}%`, width: `${x(r.hi) - x(r.lo)}%` }}
                  />
                </>
              )}
            </div>
            <span className="num text-right text-[13px]">{r.mean == null ? "-" : r.mean.toFixed(2)}</span>
          </div>
        ))}
        <div className="grid grid-cols-[96px_minmax(0,1fr)_64px] gap-3">
          <span />
          <div className="num flex justify-between text-[11px] text-ink3">
            <span>0</span>
            <span>{formatNumber(max / 2)}</span>
            <span>{formatNumber(max)}</span>
          </div>
          <span />
        </div>
      </div>
    </Panel>
  )
}
