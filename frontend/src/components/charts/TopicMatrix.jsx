import { formatSigned } from "../../lib/format"
import { PLATFORMS } from "../../lib/platforms"
import { divergingColor } from "../../lib/stats"
import { Panel, PanelHeader } from "../ui/Panel"

const MIN_N = 20

/** Net sentiment for every topic on every source. Cells with too few texts are hatched. */
export default function TopicMatrix({ topics, platforms }) {
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        title="Topics by source"
        caption={`Net sentiment per cell. Hatched cells have fewer than ${MIN_N} texts.`}
      />
      <div className="overflow-x-auto">
        <div
          className="grid min-w-[480px] items-stretch gap-[3px]"
          style={{ gridTemplateColumns: `150px repeat(${platforms.length}, minmax(0, 1fr))` }}
        >
          <span />
          {platforms.map((p) => (
            <span key={p} className="pb-1.5 text-center text-[11px] text-ink3">
              {PLATFORMS[p]?.short}
            </span>
          ))}
          {topics.map((t) => (
            <div key={t.id} className="contents">
              <span className="flex items-center pr-2 text-[13px]">{t.name}</span>
              {platforms.map((p) => {
                const cell = t.by_platform[p]
                const ok = cell && cell.n >= MIN_N && cell.net != null
                return (
                  <span
                    key={p}
                    title={
                      cell
                        ? `${t.name} on ${PLATFORMS[p]?.name}: ${cell.n} texts${ok ? `, net ${formatSigned(cell.net)}` : ""}`
                        : `${t.name} on ${PLATFORMS[p]?.name}: none`
                    }
                    className={`num flex h-10 items-center justify-center rounded text-xs font-medium ${ok ? "" : "hatch"}`}
                    style={
                      ok
                        ? {
                            background: divergingColor(cell.net),
                            color: Math.abs(cell.net) > 0.3 ? "#fff" : "var(--ink)",
                          }
                        : undefined
                    }
                  >
                    {ok ? formatSigned(cell.net) : ""}
                  </span>
                )
              })}
            </div>
          ))}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2.5 text-xs text-ink2">
        <span>{"−"}0.6</span>
        <span
          className="h-2.5 w-44 rounded-full"
          style={{ background: "linear-gradient(90deg, var(--neg), var(--neu), var(--pos))" }}
          aria-hidden="true"
        />
        <span>+0.6</span>
      </div>
    </Panel>
  )
}
