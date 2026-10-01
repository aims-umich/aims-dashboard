const SHAPES = {
  dot: "h-3 w-3 rounded-full",
  square: "h-2.5 w-2.5 rounded-[2px]",
  tick: "h-3.5 w-[3px]",
  line: "h-[2px] w-5",
  bar: "h-[3px] w-4",
}

export function LegendItem({ color, shape = "square", hatch = false, children }) {
  return (
    <span className="flex items-center gap-2">
      {hatch ? (
        <span className="hatch h-3 w-4 border border-line2" aria-hidden="true" />
      ) : (
        <span className={SHAPES[shape]} style={{ background: color }} aria-hidden="true" />
      )}
      {children}
    </span>
  )
}

export function Legend({ children, className = "" }) {
  return (
    <div className={`flex flex-wrap items-center gap-x-5 gap-y-2 text-[13px] text-ink2 ${className}`}>{children}</div>
  )
}

export function SentimentLegend({ shape = "square" }) {
  return (
    <Legend className="text-xs">
      <LegendItem color="var(--pos)" shape={shape}>
        Positive
      </LegendItem>
      <LegendItem color="var(--neu)" shape={shape}>
        Neutral
      </LegendItem>
      <LegendItem color="var(--neg)" shape={shape}>
        Negative
      </LegendItem>
    </Legend>
  )
}
