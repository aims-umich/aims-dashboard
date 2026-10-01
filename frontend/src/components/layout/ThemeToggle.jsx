import { Moon, Sun } from "lucide-react"

export default function ThemeToggle({ theme, onToggle }) {
  const next = theme === "light" ? "dark" : "light"
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={`Switch to ${next} theme`}
      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[10px] border border-line2 bg-transparent text-ink2 transition-colors hover:text-ink"
    >
      {theme === "light" ? <Moon size={18} aria-hidden="true" /> : <Sun size={18} aria-hidden="true" />}
    </button>
  )
}
