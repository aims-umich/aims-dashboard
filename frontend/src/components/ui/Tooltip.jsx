/**
 * A hover card positioned inside a `relative` chart container.
 * `x` and `y` are pixels from the container's top-left; the card flips to stay inside it.
 */
export default function Tooltip({ x, y, width, containerWidth, children, offset = 14 }) {
  if (x == null) return null
  const w = width ?? 240
  const flip = containerWidth != null && x + offset + w > containerWidth
  const left = flip ? Math.max(4, x - offset - w) : x + offset
  return (
    <div
      role="tooltip"
      className="pointer-events-none absolute z-10 flex flex-col gap-2 rounded-xl border border-line2 bg-panel2 px-4 py-3 text-[13px] shadow-pop"
      style={{ left, top: y, width: w }}
    >
      {children}
    </div>
  )
}

export function TooltipRow({ color, label, value }) {
  return (
    <div className="flex items-center justify-between gap-4 text-xs">
      <span className="flex items-center gap-1.5 text-ink2">
        {color && <span className="h-2 w-2 rounded-[2px]" style={{ background: color }} aria-hidden="true" />}
        {label}
      </span>
      <span className="num text-ink">{value}</span>
    </div>
  )
}
