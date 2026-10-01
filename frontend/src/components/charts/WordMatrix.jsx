import { PLATFORMS } from "../../lib/platforms"
import { divergingColor } from "../../lib/stats"
import { useMarkHover } from "../../lib/useHover"
import { EmptyState, Panel, PanelHeader } from "../ui/Panel"
import Tooltip, { TooltipRow } from "../ui/Tooltip"

const ROWS = 7

/** How the texts that use a word lean on each platform. Bigger dots mean the word is used more there. */
export default function WordMatrix({ words }) {
  const { ref, hover, enter, leave } = useMarkHover()
  const platforms = words.map((w) => w.platform)
  const maps = words.map((w) => Object.fromEntries((w.cloud ?? []).map((c) => [c.value, c])))
  const totals = {}
  maps.forEach((m) =>
    Object.values(m).forEach((c) => {
      totals[c.value] = totals[c.value] ?? { count: 0, places: 0 }
      totals[c.value].count += c.count
      totals[c.value].places += 1
    }),
  )
  const ranked = Object.entries(totals)
    .filter(([, t]) => t.places >= 2)
    .sort((a, b) => b[1].count - a[1].count)
    .map(([w]) => w)
  // "reactors" adds nothing next to "reactor".
  const chosen = ranked.filter((w) => !(w.endsWith("s") && ranked.includes(w.slice(0, -1)))).slice(0, ROWS)
  const max = Math.max(1, ...chosen.flatMap((w) => maps.map((m) => m[w]?.count ?? 0)))
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        title="Word sentiment by platform"
        caption="How the texts that use a word lean on each platform, over the last 30 days. Bigger dots mean the word is used more there."
      />
      {chosen.length ? (
        <div
          ref={ref}
          className="relative grid items-center gap-y-1"
          style={{ gridTemplateColumns: `100px repeat(${platforms.length}, minmax(0, 1fr))` }}
          onPointerLeave={leave}
        >
          <span />
          {platforms.map((p) => (
            <span key={p} className="text-center text-[13px] font-semibold">
              {PLATFORMS[p]?.name}
            </span>
          ))}
          {chosen.map((word) => (
            <div key={word} className="contents">
              <span className="flex h-[52px] items-center text-sm">{word}</span>
              {maps.map((m, i) => {
                const c = m[word]
                const sided = c ? c.positive + c.negative : 0
                const leanValue = sided >= 3 ? (c.positive - c.negative) / sided : null
                const size = c ? Math.round(12 + Math.sqrt(c.count / max) * 30) : 0
                return (
                  <span key={platforms[i]} className="flex h-[52px] items-center justify-center">
                    {c ? (
                      <span
                        className="rounded-full"
                        style={{
                          width: size,
                          height: size,
                          background: leanValue == null ? "var(--neu)" : divergingColor(leanValue, 0.6),
                        }}
                        onPointerEnter={(e) => enter({ word, platform: platforms[i], c, leanValue }, e)}
                      />
                    ) : (
                      <span className="text-xs text-ink3">rare</span>
                    )}
                  </span>
                )
              })}
            </div>
          ))}
          {hover && (
            <Tooltip x={hover.x} y={hover.y + 10} containerWidth={hover.width} width={210}>
              <span className="font-semibold">
                “{hover.item.word}” on {PLATFORMS[hover.item.platform]?.name}
              </span>
              <TooltipRow color="var(--pos)" label="Positive" value={hover.item.c.positive} />
              <TooltipRow color="var(--neg)" label="Negative" value={hover.item.c.negative} />
              <TooltipRow label="All texts" value={hover.item.c.count} />
            </Tooltip>
          )}
        </div>
      ) : (
        <EmptyState height={240}>Not enough shared vocabulary between platforms yet.</EmptyState>
      )}
      <div className="flex flex-wrap items-center gap-2.5 text-xs text-ink2">
        <span>Leans negative</span>
        <span
          className="h-2.5 w-40 rounded-full"
          style={{ background: "linear-gradient(90deg, var(--neg), var(--neu), var(--pos))" }}
          aria-hidden="true"
        />
        <span>Leans positive</span>
      </div>
    </Panel>
  )
}
