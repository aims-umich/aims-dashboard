import { formatNumber, formatPercent } from "../../lib/format"
import { Legend, LegendItem } from "../ui/Legend"
import { Panel, PanelHeader } from "../ui/Panel"

const CLOSE = 0.7

/** How sure the model was of each text's top label. Bands below 70% are close calls. */
export default function ConfidenceHistogram({ bins, avgConfidence, unit }) {
  const total = bins.reduce((a, b) => a + b.count, 0)
  const max = Math.max(1, ...bins.map((b) => b.count))
  const close = bins.filter((b) => b.to <= CLOSE + 1e-6).reduce((a, b) => a + b.count, 0)
  const sure = bins.filter((b) => b.from >= 0.9 - 1e-6).reduce((a, b) => a + b.count, 0)
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        title="Model confidence"
        caption={`${unit[0].toUpperCase()}${unit.slice(1)} by the model's confidence in its top label.`}
        actions={
          <Legend className="text-xs">
            <LegendItem hatch>Close calls, under 70%</LegendItem>
          </Legend>
        }
      />
      <div className="grid h-[220px] grid-cols-7 items-end gap-1.5 border-b border-line2">
        {bins.map((b) => (
          <div key={b.from} className="flex h-full flex-col items-center justify-end gap-1.5">
            <span className="num text-[11px] text-ink2">{formatNumber(b.count)}</span>
            <div
              className="relative w-full max-w-6 overflow-hidden rounded-t"
              style={{ height: `${(b.count / max) * 86}%`, minHeight: b.count ? 2 : 0, background: "var(--ink3)" }}
            >
              {b.to <= CLOSE + 1e-6 && <span className="hatch absolute inset-0" />}
            </div>
          </div>
        ))}
      </div>
      <div className="num grid grid-cols-7 gap-1.5 text-center text-[11px] text-ink3">
        {bins.map((b) => (
          <span key={b.from}>{Math.round(b.from * 100)}%</span>
        ))}
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-2 border-t border-line pt-3 text-[13px] text-ink2">
        <span>
          Average <span className="num text-ink">{formatPercent(avgConfidence, 1)}</span>
        </span>
        <span>
          90% or more <span className="num text-ink">{total ? formatPercent(sure / total, 1) : "-"}</span>
        </span>
        <span>
          Close calls{" "}
          <span className="num text-ink">
            {formatNumber(close)} {unit}, {total ? formatPercent(close / total, 1) : "-"}
          </span>
        </span>
      </div>
    </Panel>
  )
}
