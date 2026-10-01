import PlatformIcon from "../PlatformIcon"

/** The platform's own mark in a neutral tile, so brand colors never compete with the data colors. */
export default function PlatformMark({ platform, size = 36 }) {
  const inner = Math.round(size * 0.62)
  return (
    <span
      className="flex shrink-0 items-center justify-center rounded-[9px] border border-line2 bg-panel2"
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <PlatformIcon platform={platform} size={inner} />
    </span>
  )
}
