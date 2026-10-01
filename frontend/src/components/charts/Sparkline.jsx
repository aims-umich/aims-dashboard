/** A small trend line in the de-emphasis ink; gaps (null values) break the line. */
export default function Sparkline({ values, width = 96, height = 28 }) {
  const finite = values.filter((v) => v != null)
  if (finite.length < 2) return <span style={{ width, height }} aria-hidden="true" />
  const min = Math.min(...finite)
  const max = Math.max(...finite)
  const y = (v) => height - 2 - ((v - min) / (max - min || 1)) * (height - 4)
  let d = ""
  let open = false
  values.forEach((v, i) => {
    if (v == null) {
      open = false
      return
    }
    const x = (i / (values.length - 1)) * 100
    d += `${open ? "L" : "M"}${x.toFixed(1)} ${y(v).toFixed(1)}`
    open = true
  })
  return (
    <svg
      viewBox={`0 0 100 ${height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      style={{ width, height }}
      className="shrink-0"
    >
      <path
        d={d}
        fill="none"
        stroke="var(--ink3)"
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
        strokeLinejoin="round"
      />
    </svg>
  )
}
