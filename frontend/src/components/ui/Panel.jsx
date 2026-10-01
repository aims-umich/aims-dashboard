export function Panel({ as: Tag = "section", className = "", children, ...rest }) {
  return (
    <Tag className={`min-w-0 rounded-2xl border border-line bg-panel ${className}`} {...rest}>
      {children}
    </Tag>
  )
}

/** A panel's own heading: a plain chart name, an optional line on how to read it, and controls. */
export function PanelHeader({ title, caption, actions, level = 2, id }) {
  const Heading = `h${level}`
  return (
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex min-w-0 flex-col gap-1">
        <Heading id={id} className="m-0 text-lg font-bold text-ink">
          {title}
        </Heading>
        {caption && <p className="m-0 max-w-[68ch] text-[13px] leading-snug text-ink2">{caption}</p>}
      </div>
      {actions}
    </header>
  )
}

export function EmptyState({ children, height = 200, className = "" }) {
  return (
    <div
      className={`flex items-center justify-center px-6 text-center text-sm text-ink3 ${className}`}
      style={{ minHeight: height }}
    >
      {children}
    </div>
  )
}

export function Skeleton({ height = 200, className = "" }) {
  return <div className={`w-full animate-pulse rounded-xl bg-panel2 ${className}`} style={{ height }} />
}
