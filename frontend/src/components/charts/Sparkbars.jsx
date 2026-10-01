/** Monthly volume as thin columns: past months recede, the current month is drawn in ink. */
export default function Sparkbars({ values, height = 32 }) {
  const max = Math.max(1, ...values)
  const w = 10
  const past = []
  const now = []
  values.forEach((v, i) => {
    const h = v === 0 ? 1 : Math.max(2, (v / max) * (height - 2))
    const seg = `M${i * w + 1.5} ${height}h7v-${h.toFixed(1)}h-7Z`
    ;(i === values.length - 1 ? now : past).push(seg)
  })
  return (
    <svg
      viewBox={`0 0 ${values.length * w} ${height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      className="block w-full"
      style={{ height }}
    >
      <path d={past.join("")} fill="var(--ink3)" fillOpacity="0.55" />
      <path d={now.join("")} fill="var(--ink)" />
    </svg>
  )
}
