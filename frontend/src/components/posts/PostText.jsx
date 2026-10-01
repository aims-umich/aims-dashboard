/** Post text with the model's most influential words highlighted: green pushed toward positive, red toward negative. */
export default function PostText({ text, highlights, className = "" }) {
  if (!text) return null
  const spans = [...(highlights ?? [])]
    .filter(([start, end]) => start >= 0 && end <= text.length && end > start)
    .sort((a, b) => a[0] - b[0])
  const parts = []
  let cursor = 0
  for (const [start, end, score] of spans) {
    if (start < cursor) continue
    if (start > cursor) parts.push(<span key={`t${cursor}`}>{text.slice(cursor, start)}</span>)
    const positive = score > 0
    parts.push(
      <mark
        key={`h${start}`}
        title={`Pushed toward ${positive ? "positive" : "negative"}`}
        className="rounded-[3px] px-0.5 text-ink"
        style={{
          background: positive ? "var(--posw)" : "var(--negw)",
          borderBottom: `2px solid ${positive ? "var(--pos)" : "var(--neg)"}`,
        }}
      >
        {text.slice(start, end)}
      </mark>,
    )
    cursor = end
  }
  if (cursor < text.length) parts.push(<span key={`t${cursor}`}>{text.slice(cursor)}</span>)
  return <p className={`m-0 whitespace-pre-line break-words ${className}`}>{parts}</p>
}
