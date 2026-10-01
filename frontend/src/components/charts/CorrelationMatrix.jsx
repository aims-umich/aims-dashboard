import { formatSigned } from "../../lib/format"
import { PLATFORMS } from "../../lib/platforms"
import { countsTotal, divergingColor, pearson } from "../../lib/stats"
import { useMarkHover } from "../../lib/useHover"
import { Panel, PanelHeader } from "../ui/Panel"
import Tooltip from "../ui/Tooltip"

const NEED_WEEKS = 12
const MIN_WEEK_N = 5

/** Correlation of weekly net sentiment between every pair of sources, once they overlap long enough. */
export default function CorrelationMatrix({ series }) {
  const { ref, hover, enter, leave } = useMarkHover()
  const keys = Object.keys(series)
  const nets = Object.fromEntries(
    keys.map((k) => [
      k,
      series[k].map((w) => (countsTotal(w) >= MIN_WEEK_N ? (w.positive - w.negative) / countsTotal(w) : null)),
    ]),
  )
  const pairs = {}
  let bestOverlap = 0
  for (const a of keys)
    for (const b of keys) {
      if (a === b) continue
      const xs = []
      const ys = []
      nets[a].forEach((v, i) => {
        if (v != null && nets[b][i] != null) {
          xs.push(v)
          ys.push(nets[b][i])
        }
      })
      bestOverlap = Math.max(bestOverlap, xs.length)
      pairs[`${a}|${b}`] = { r: xs.length >= NEED_WEEKS ? pearson(xs, ys) : null, weeks: xs.length }
    }
  const ready = bestOverlap >= NEED_WEEKS
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        title="Correlation between sources"
        caption="Correlation of weekly net sentiment between every pair of sources, over weeks where both have at least 5 texts."
      />
      <div
        ref={ref}
        className="relative grid items-center gap-1"
        style={{ gridTemplateColumns: `90px repeat(${keys.length}, minmax(0, 1fr))` }}
        onPointerLeave={leave}
      >
        <span />
        {keys.map((k) => (
          <span key={k} className="text-center text-[11px] text-ink3">
            {PLATFORMS[k]?.short}
          </span>
        ))}
        {keys.map((a) => (
          <div key={a} className="contents">
            <span className="text-xs text-ink2">{PLATFORMS[a]?.name}</span>
            {keys.map((b) => {
              const pair = pairs[`${a}|${b}`]
              const diagonal = a === b
              return (
                <span
                  key={b}
                  className={`flex aspect-square items-center justify-center rounded border border-line ${!diagonal && pair.r == null ? "hatch" : ""}`}
                  style={
                    diagonal
                      ? { background: "var(--line2)" }
                      : pair.r != null
                        ? { background: divergingColor(pair.r, 1) }
                        : undefined
                  }
                  onPointerEnter={(e) => !diagonal && enter({ a, b, ...pair }, e)}
                >
                  {!diagonal && pair.r != null && (
                    <span className="num text-[11px] font-medium text-white">{formatSigned(pair.r)}</span>
                  )}
                </span>
              )
            })}
          </div>
        ))}
        {!ready && (
          <div className="absolute inset-y-0 right-0 left-[90px] flex items-center justify-center">
            <div className="flex w-[min(300px,90%)] flex-col gap-3 rounded-xl border border-line2 bg-panel2 p-5 shadow-pop">
              <span className="text-[15px] font-[650]">Needs {NEED_WEEKS} weeks of overlap</span>
              <span className="text-[13px] leading-normal text-ink2">
                The best-covered pair of sources shares {bestOverlap} {bestOverlap === 1 ? "week" : "weeks"} with enough
                texts in both.
              </span>
              <div className="flex flex-col gap-1.5">
                <div className="h-1.5 rounded-full bg-line">
                  <div
                    className="h-1.5 rounded-full bg-glow"
                    style={{ width: `${(bestOverlap / NEED_WEEKS) * 100}%` }}
                  />
                </div>
                <span className="num text-[11px] text-ink3">
                  {bestOverlap} OF {NEED_WEEKS} WEEKS
                </span>
              </div>
            </div>
          </div>
        )}
        {hover && ready && (
          <Tooltip x={hover.x} y={hover.y + 10} containerWidth={hover.width} width={220}>
            <span className="font-semibold">
              {PLATFORMS[hover.item.a]?.name} and {PLATFORMS[hover.item.b]?.name}
            </span>
            <span className="text-xs text-ink2">
              {hover.item.r == null
                ? `Only ${hover.item.weeks} shared weeks`
                : `r = ${formatSigned(hover.item.r)} over ${hover.item.weeks} weeks`}
            </span>
          </Tooltip>
        )}
      </div>
    </Panel>
  )
}
