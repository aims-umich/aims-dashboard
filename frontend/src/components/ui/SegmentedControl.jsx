export default function SegmentedControl({ options, value, onChange, label }) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="inline-flex rounded-lg bg-gray-100 dark:bg-gray-900/60 p-0.5 text-sm"
    >
      {options.map((option) => {
        const active = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(option.value)}
            className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
              active
                ? "bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white"
                : "text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
            }`}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
