export default function ChartTooltip({ active, payload, label, labelFormatter, valueFormatter }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs shadow-md dark:border-gray-700 dark:bg-gray-900">
      <p className="mb-1 font-medium text-gray-900 dark:text-white">{labelFormatter ? labelFormatter(label) : label}</p>
      {payload.map((item) => (
        <p key={item.dataKey} className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
          <span className="h-2 w-2 rounded-full" style={{ background: item.color ?? item.payload?.fill }} />
          <span>{item.name}</span>
          <span className="ml-auto pl-3 font-medium tabular-nums text-gray-900 dark:text-white">
            {valueFormatter ? valueFormatter(item.value, item) : item.value}
          </span>
        </p>
      ))}
    </div>
  )
}
