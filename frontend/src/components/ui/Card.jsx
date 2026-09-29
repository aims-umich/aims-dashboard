export function Card({ title, subtitle, actions, children, flush = false, className = "" }) {
  // `flush` lets lists run edge to edge while the header keeps the card's padding.
  return (
    <section
      className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200/70 dark:border-gray-700/60 min-w-0 ${
        flush ? "overflow-hidden" : "p-5"
      } ${className}`}
    >
      {(title || actions) && (
        <header className={`flex flex-wrap items-start justify-between gap-3 ${flush ? "px-5 pt-5 pb-3" : "mb-4"}`}>
          <div className="min-w-0">
            {title && <h2 className="text-base font-semibold text-gray-900 dark:text-white">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      {children}
    </section>
  )
}

export function MetricCard({ label, value, hint, loading }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200/70 dark:border-gray-700/60 px-4 py-3.5 min-w-0">
      <p className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">{label}</p>
      {loading ? (
        <div className="mt-2 h-7 w-20 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
      ) : (
        <p className="mt-1 text-2xl font-semibold tabular-nums text-gray-900 dark:text-white truncate">{value}</p>
      )}
      {hint && <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400 truncate">{hint}</p>}
    </div>
  )
}

export function EmptyState({ children, height = 260 }) {
  return (
    <div
      className="flex items-center justify-center text-center text-sm text-gray-500 dark:text-gray-400 px-6"
      style={{ height }}
    >
      {children}
    </div>
  )
}

export function Skeleton({ height = 260 }) {
  return <div className="w-full rounded-lg bg-gray-100 dark:bg-gray-700/50 animate-pulse" style={{ height }} />
}
