export default function Segmented({ options, value, onChange, label, size = "md" }) {
  const height = size === "sm" ? "min-h-[34px]" : "min-h-[38px]"
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="inline-flex flex-wrap rounded-[10px] border border-line2 bg-panel p-[3px]"
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
            className={`${height} rounded-[7px] px-3.5 text-[13px] transition-colors ${
              active
                ? "bg-panel2 font-semibold text-ink shadow-[0_0_0_1px_var(--line2)]"
                : "font-medium text-ink2 hover:text-ink"
            }`}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
