import { formatDate, formatSigned } from "../../lib/format"

const VERDICT = {
  shift: { label: "Clear shift", className: "" },
  within_noise: { label: "Within noise", className: "" },
  too_few: { label: "Too few to call", className: "hatch" },
  no_data: { label: "Before collection", className: "hatch" },
}

const COLS = "grid-cols-[40px_minmax(260px,1.2fr)_minmax(300px,1.3fr)_90px_150px]"

/** Each listed event's month against the six months before it, with the event month's 95% interval. */
export default function EventImpact({ events, noun }) {
  const px = (v) => ((v + 1) / 2) * 100
  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-panel">
      <div className="min-w-[980px]">
        {events.map((e) => {
          const has = e.net_sentiment != null && e.baseline_net != null
          const verdict = VERDICT[e.verdict]
          const up = has && e.net_sentiment > e.baseline_net
          const shift = e.verdict === "shift"
          return (
            <div
              key={e.number}
              className={`grid ${COLS} min-h-[72px] items-center gap-5 border-b border-line px-6 py-2`}
            >
              <span
                className="num flex h-7 w-7 items-center justify-center rounded-full border border-line2 text-xs font-semibold"
                style={{
                  background: shift ? "var(--ink)" : "var(--panel2)",
                  color: shift ? "var(--bg)" : "var(--ink2)",
                }}
              >
                {e.number}
              </span>
              <span className="flex flex-col leading-snug">
                <span className="text-[15px] font-semibold">{e.title}</span>
                <span className="text-xs text-ink3">
                  {formatDate(e.date)} · {e.n} {noun} that month
                </span>
              </span>
              <div className="relative h-10">
                <div className="absolute inset-y-0 left-1/2 w-px bg-line2" />
                {has && (
                  <>
                    <div
                      className="absolute top-[19px] h-[2px] bg-line2"
                      style={{
                        left: `${Math.min(px(e.baseline_net), px(e.net_sentiment))}%`,
                        width: `${Math.abs(px(e.net_sentiment) - px(e.baseline_net))}%`,
                      }}
                    />
                    {e.verdict !== "too_few" && (
                      <div
                        className="absolute top-[19px] h-[2px] bg-ink"
                        style={{
                          left: `${px(Math.max(-1, e.net_sentiment - e.interval))}%`,
                          width: `${px(Math.min(1, e.net_sentiment + e.interval)) - px(Math.max(-1, e.net_sentiment - e.interval))}%`,
                        }}
                      />
                    )}
                    <div
                      className="absolute top-3.5 -ml-1.5 box-border h-3 w-3 rounded-full border-2 border-ink3 bg-panel"
                      style={{ left: `${px(e.baseline_net)}%` }}
                    />
                    <div
                      className="absolute top-3 -ml-2 h-4 w-4 rounded-full"
                      style={{
                        left: `${px(e.net_sentiment)}%`,
                        background: e.verdict === "too_few" ? "var(--neu)" : up ? "var(--pos)" : "var(--neg)",
                        boxShadow: "0 0 0 3px var(--panel)",
                      }}
                    />
                  </>
                )}
              </div>
              <span className="num text-right text-[15px]">
                {has ? formatSigned(e.net_sentiment - e.baseline_net) : "-"}
              </span>
              <span
                className={`justify-self-start rounded-full border border-line2 px-2.5 py-1 text-xs font-semibold ${verdict.className}`}
                style={shift ? { background: up ? "var(--posw)" : "var(--negw)" } : undefined}
              >
                {verdict.label}
              </span>
            </div>
          )
        })}
        <div className={`grid ${COLS} gap-5 px-6 pt-2.5 pb-3.5`}>
          <span />
          <span />
          <div className="num flex justify-between text-[11px] text-ink3">
            <span>{"−"}1</span>
            <span>{"−"}0.5</span>
            <span>0</span>
            <span>+0.5</span>
            <span>+1</span>
          </div>
          <span className="text-right text-[11px] text-ink3">Change</span>
          <span />
        </div>
      </div>
    </div>
  )
}
