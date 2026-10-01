import { useState } from "react"
import { formatNumber } from "../../lib/format"
import { SENTIMENT_LABELS, SENTIMENT_VARS, SENTIMENTS } from "../../lib/sentiment"
import { Legend, LegendItem } from "../ui/Legend"
import { EmptyState, Panel, PanelHeader } from "../ui/Panel"
import Segmented from "../ui/Segmented"

/** Words far more common in positive than negative texts, and the reverse, by log-odds z-score. */
export function DistinctiveWords({ words, sampled, unit }) {
  const rows = [
    ...(words?.negative ?? []).map((w) => ({ ...w, side: -1 })),
    ...[...(words?.positive ?? [])].reverse().map((w) => ({ ...w, side: 1 })),
  ]
  const max = Math.max(1, ...rows.map((r) => Math.abs(r.z)))
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        level={3}
        title="Distinctive words"
        caption="Words far more common in one sentiment than the other. Shared words like “power” are left out."
      />
      {rows.length ? (
        <>
          <div className="grid grid-cols-2 border-b border-line pb-2 text-xs text-ink3">
            <span>← More negative</span>
            <span className="text-right">More positive →</span>
          </div>
          <div className="flex flex-col gap-0.5">
            {rows.map((w) => {
              const width = `${(Math.abs(w.z) / max) * 58}%`
              const label = (
                <span className="text-sm whitespace-nowrap">
                  {w.word}{" "}
                  <span className="num text-[11px] text-ink3">
                    {w.positive} / {w.negative}
                  </span>
                </span>
              )
              return (
                <div key={`${w.side}${w.word}`} className="grid h-[30px] grid-cols-2 items-center">
                  <div className="relative flex h-full items-center justify-end gap-2.5 border-r border-line2">
                    {w.side < 0 && (
                      <>
                        {label}
                        <span className="h-3.5 shrink-0 rounded-l bg-neg" style={{ width }} />
                      </>
                    )}
                  </div>
                  <div className="relative flex h-full items-center gap-2.5">
                    {w.side > 0 && (
                      <>
                        <span className="h-3.5 shrink-0 rounded-r bg-pos" style={{ width }} />
                        {label}
                      </>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
          <span className="text-xs text-ink3">
            Counts are positive / negative {unit} containing the word, from the {formatNumber(sampled)} most recent.
          </span>
        </>
      ) : (
        <EmptyState height={240}>Not enough scored {unit} yet to tell which words lean one way.</EmptyState>
      )}
    </Panel>
  )
}

export function TopWords({ words, unit }) {
  const [tab, setTab] = useState("negative")
  const list = words?.[tab] ?? []
  const max = Math.max(1, ...list.map((w) => w.count))
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        level={3}
        title="Top words by sentiment"
        caption={`Most frequent words in ${tab} ${unit}.`}
        actions={
          <Segmented
            size="sm"
            label="Sentiment"
            value={tab}
            onChange={setTab}
            options={SENTIMENTS.map((s) => ({ value: s, label: SENTIMENT_LABELS[s] }))}
          />
        }
      />
      {list.length ? (
        <div className="flex flex-col gap-1.5">
          {list.slice(0, 10).map((w) => (
            <div key={w.word} className="grid h-[30px] grid-cols-[96px_minmax(0,1fr)_40px] items-center gap-3">
              <span className="truncate text-right text-sm">{w.word}</span>
              <span
                className="h-3.5 rounded-r"
                style={{ width: `${(w.count / max) * 100}%`, background: SENTIMENT_VARS[tab] }}
              />
              <span className="num text-xs text-ink2">{w.count}</span>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState height={240}>
          No {tab} {unit} in this range.
        </EmptyState>
      )}
    </Panel>
  )
}

function lean(word) {
  const sided = word.positive + word.negative
  if (sided < 3) return "var(--neu)"
  const share = (word.positive - word.negative) / sided
  if (share >= 0.3) return "var(--pos)"
  if (share <= -0.3) return "var(--neg)"
  return "var(--neu)"
}

/** The most common words, sized by frequency, underlined by which way they lean. */
export function WordField({ cloud }) {
  const words = [...(cloud ?? [])].slice(0, 30).sort((a, b) => a.value.localeCompare(b.value))
  const max = Math.max(1, ...words.map((w) => w.count))
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        level={3}
        title="Word field"
        caption="The most common words. Size is frequency. The underline shows which way each word leans."
        actions={
          <Legend className="text-xs">
            <LegendItem color="var(--pos)" shape="bar">
              Leans positive
            </LegendItem>
            <LegendItem color="var(--neu)" shape="bar">
              Balanced
            </LegendItem>
            <LegendItem color="var(--neg)" shape="bar">
              Leans negative
            </LegendItem>
          </Legend>
        }
      />
      {words.length ? (
        <div className="flex flex-wrap items-baseline justify-center gap-x-6 gap-y-2.5 px-2 pt-2 pb-4 sm:px-6">
          {words.map((w) => {
            const size = Math.round(14 + Math.sqrt(w.count / max) * 30)
            return (
              <span
                key={w.value}
                title={`${w.value}: ${w.count} texts, ${w.positive} positive, ${w.negative} negative`}
                className="wide pb-1 leading-[1.1] tracking-[-0.01em]"
                style={{
                  fontSize: size,
                  fontWeight: w.count / max > 0.6 ? 750 : w.count / max > 0.3 ? 600 : 450,
                  borderBottom: `3px solid ${lean(w)}`,
                }}
              >
                {w.value}
              </span>
            )
          })}
        </div>
      ) : (
        <EmptyState height={160}>No words yet.</EmptyState>
      )}
    </Panel>
  )
}
