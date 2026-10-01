import { Legend } from "../ui/Legend"

const CLOSE = 0.7

/** Each text placed by its three probabilities: corners are confident calls, edges are two-way doubts. */
export default function Ternary({ sample }) {
  // A fixed pseudo-random offset per point, so the same data always draws the same picture.
  const jitter = (i, k) => {
    const v = Math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return (v - Math.floor(v) - 0.5) * 2
  }
  const points = sample.map(([neg, neu, pos], i) => {
    const total = neg + neu + pos || 1
    const n = neg / total
    const u = neu / total
    const p = pos / total
    const top = Math.max(n, u, p)
    const close = top < CLOSE
    // Confident calls pile up in the corners; a little jitter keeps the pile readable.
    const j = close ? 0 : 1.1
    return {
      x: (u * 0.5 + p) * 100 + jitter(i, 1) * j,
      y: (1 - u) * 100 + jitter(i, 2) * j * 0.8,
      close,
      color: top === p ? "var(--pos)" : top === n ? "var(--neg)" : "var(--neu)",
    }
  })
  const closeCount = points.filter((p) => p.close).length
  return (
    <div className="flex flex-col gap-4">
      <div className="relative mx-auto mt-7 mb-8 aspect-[1.1547] w-full max-w-[560px]">
        <svg
          viewBox="0 0 100 86.6"
          preserveAspectRatio="none"
          aria-hidden="true"
          className="absolute inset-0 h-full w-full overflow-visible"
        >
          <path
            d="M50 0L0 86.6L100 86.6Z"
            fill="var(--panel2)"
            stroke="var(--line2)"
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />
          <path
            d="M50 57.73L50 86.6M50 57.73L25 43.3M50 57.73L75 43.3"
            fill="none"
            stroke="var(--ink3)"
            strokeWidth="1"
            strokeDasharray="3 3"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        {points
          .filter((p) => !p.close)
          .map((p, i) => (
            <span
              key={`c${i}`}
              className="absolute -mt-[3.5px] -ml-[3.5px] h-[7px] w-[7px] rounded-full opacity-55"
              style={{ left: `${p.x}%`, top: `${p.y}%`, background: p.color }}
            />
          ))}
        {points
          .filter((p) => p.close)
          .map((p, i) => (
            <span
              key={`h${i}`}
              className="absolute -mt-[5.5px] -ml-[5.5px] h-[11px] w-[11px] rounded-full bg-ink"
              style={{ left: `${p.x}%`, top: `${p.y}%`, boxShadow: "0 0 0 2px var(--glow)" }}
            />
          ))}
        <span className="absolute -top-[26px] left-1/2 -translate-x-1/2 text-[13px] font-[650]">Neutral</span>
        <span className="absolute -bottom-7 -left-1 text-[13px] font-[650]">Negative</span>
        <span className="absolute -right-1 -bottom-7 text-[13px] font-[650]">Positive</span>
      </div>
      <Legend>
        <span className="flex items-center gap-2">
          <span
            className="h-2.5 w-2.5 rounded-full bg-ink"
            style={{ boxShadow: "0 0 0 2px var(--glow)" }}
            aria-hidden="true"
          />
          Close call, top label under 70%
        </span>
        <span className="num text-ink3">
          {closeCount} OF {points.length}
        </span>
      </Legend>
    </div>
  )
}
