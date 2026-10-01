import { PLATFORMS } from "../../lib/platforms"
import { Panel, PanelHeader } from "../ui/Panel"

/** Average engagement per post on each social platform, one small bar chart per measure. */
export default function EngagementCompare({ summaries }) {
  const withEngagement = summaries.filter((s) => s.engagement)
  const measures = ["likes", "reposts", "replies"]
  const label = { likes: "Likes", reposts: "Reposts", replies: "Replies" }
  return (
    <Panel className="flex flex-col gap-5 p-6">
      <PanelHeader
        title="Engagement per post"
        caption="Average per post or comment over the last 30 days. Newspapers don't publish engagement, and YouTube has no reposts."
      />
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(280px,100%),1fr))] gap-8">
        {measures.map((m) => {
          const rows = withEngagement
            .map((s) => ({ key: s.platform, value: s.engagement.averages[m] ?? null }))
            .sort((a, b) => (b.value ?? -1) - (a.value ?? -1))
          const max = Math.max(1, ...rows.map((r) => r.value ?? 0))
          return (
            <div key={m} className="flex flex-col gap-2.5">
              <span className="text-sm font-[650]">{label[m]}</span>
              {rows.map((r) => (
                <div key={r.key} className="grid h-7 grid-cols-[86px_minmax(0,1fr)_44px] items-center gap-3">
                  <span className="text-[13px] text-ink2">{PLATFORMS[r.key]?.name}</span>
                  <span
                    className="h-3.5 rounded-r bg-ink3"
                    style={{ width: r.value == null ? 0 : `${(r.value / max) * 100}%` }}
                  />
                  <span className="num text-right text-xs">{r.value == null ? "n/a" : r.value.toFixed(2)}</span>
                </div>
              ))}
            </div>
          )
        })}
      </div>
    </Panel>
  )
}
