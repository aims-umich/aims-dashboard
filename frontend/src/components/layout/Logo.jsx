import { Link } from "react-router-dom"

export function LogoMark({ size = 30 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 30 30" aria-hidden="true" className="shrink-0">
      <path d="M4 21 A11 11 0 0 1 26 21" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M15 21 L21.5 11.5" stroke="var(--glow)" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="15" cy="21" r="2.6" fill="currentColor" />
      <path
        d="M6.5 14.5 L8.3 15.6 M15 8.5 L15 10.6 M23.5 14.5 L21.7 15.6"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  )
}

export default function Logo({ compact = false }) {
  return (
    <Link
      to="/"
      className="flex items-center gap-3 text-ink no-underline"
      aria-label="Nuclear Sentiment Analysis, home"
    >
      <LogoMark size={compact ? 26 : 30} />
      <span className="flex flex-col gap-px">
        <span className="text-[15px] leading-tight font-[760] tracking-[-0.01em] wider">
          Nuclear Sentiment Analysis
        </span>
        {!compact && (
          <span className="num text-[10px] leading-tight tracking-[0.08em] text-ink3">
            AIMS LAB · UNIVERSITY OF MICHIGAN
          </span>
        )}
      </span>
    </Link>
  )
}
