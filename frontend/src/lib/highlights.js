/** Whether a post's highlighted words pulled both toward positive and toward negative. */
export function isMixed(highlights) {
  const scores = (highlights ?? []).map((h) => h[2])
  return scores.some((s) => s > 0) && scores.some((s) => s < 0)
}
