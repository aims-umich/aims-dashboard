import { useMarkHover } from "../../lib/useHover"
import { Panel, PanelHeader } from "../ui/Panel"
import Tooltip from "../ui/Tooltip"

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

/** Texts per hour by UTC weekday over four weeks. Hours before the source was collecting are hatched. */
export default function ActivityHeatmap({ activity, unit }) {
  const { ref, hover, enter, leave } = useMarkHover()
  const rates = activity.counts.map((row, d) =>
    row.map((c, h) => (activity.slots[d][h] ? c / activity.slots[d][h] : null)),
  )
  const max = Math.max(1e-9, ...rates.flat().filter((v) => v != null))
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        title="Activity by hour and weekday"
        caption={`Average ${unit} per hour, by UTC weekday, over the last ${activity.window_days / 7} weeks.`}
        actions={
          <div className="flex items-center gap-2 text-xs text-ink2">
            <span>Fewer</span>
            <span className="flex gap-0.5" aria-hidden="true">
              {[0.08, 0.25, 0.45, 0.7, 0.95].map((a) => (
                <span key={a} className="h-3 w-[18px]" style={{ background: `rgb(var(--heat) / ${a})` }} />
              ))}
            </span>
            <span>More</span>
          </div>
        }
      />
      <div className="overflow-x-auto">
        <div className="min-w-[620px]">
          <div className="grid grid-cols-[44px_minmax(0,1fr)] gap-2">
            <div className="grid grid-rows-[repeat(7,22px)] items-center gap-[3px] text-xs text-ink2">
              {DAYS.map((d) => (
                <span key={d}>{d}</span>
              ))}
            </div>
            <div
              ref={ref}
              className="relative grid grid-cols-[repeat(24,minmax(0,1fr))] grid-rows-[repeat(7,22px)] gap-[3px]"
              onPointerLeave={leave}
            >
              {rates.flatMap((row, d) =>
                row.map((rate, h) => (
                  <span
                    key={`${d}-${h}`}
                    className={`rounded-[3px] ${rate == null ? "hatch" : ""}`}
                    style={
                      rate == null
                        ? undefined
                        : { background: `rgb(var(--heat) / ${(0.06 + (rate / max) * 0.89).toFixed(3)})` }
                    }
                    onPointerEnter={(e) =>
                      enter({ d, h, rate, count: activity.counts[d][h], slots: activity.slots[d][h] }, e)
                    }
                  />
                )),
              )}
              {hover && (
                <Tooltip x={hover.x} y={hover.y + 10} containerWidth={hover.width} width={210}>
                  <span className="font-semibold">
                    {DAYS[hover.item.d]} {String(hover.item.h).padStart(2, "0")}:00 UTC
                  </span>
                  <span className="text-xs text-ink2">
                    {hover.item.rate == null
                      ? "Not collecting yet"
                      : `${hover.item.count} ${unit} over ${hover.item.slots} ${hover.item.slots === 1 ? "hour" : "hours"}, ${hover.item.rate.toFixed(1)} an hour`}
                  </span>
                </Tooltip>
              )}
            </div>
          </div>
          <div className="mt-2 grid grid-cols-[44px_minmax(0,1fr)] gap-2">
            <span />
            <div className="num flex justify-between text-[11px] text-ink3">
              {[0, 4, 8, 12, 16, 20, 23].map((h) => (
                <span key={h}>{String(h).padStart(2, "0")}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Panel>
  )
}
