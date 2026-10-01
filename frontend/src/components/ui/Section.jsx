/** A page section's heading: a channel code, a plain title, and a caption only when the chart needs one. */
export default function SectionHeader({ code, title, caption, actions, id }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex min-w-0 flex-col gap-2">
        {code && <span className="num text-xs tracking-[0.1em] text-glow">{code}</span>}
        <h2 id={id} className="m-0 text-[28px] leading-tight font-[750] tracking-[-0.015em] wide text-ink">
          {title}
        </h2>
        {caption && <p className="m-0 max-w-[70ch] text-[15px] text-ink2">{caption}</p>}
      </div>
      {actions}
    </div>
  )
}
