export default function LowSample({ children = "Too few to call" }) {
  return (
    <span className="hatch inline-flex self-start rounded-md whitespace-nowrap border border-line2 px-2 py-[3px] text-xs text-ink2">
      {children}
    </span>
  )
}
