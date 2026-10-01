// Small, exact helpers for the numbers every chart shows. Net sentiment is (positive - negative) / total.

/** Net sentiment and its 95% interval (normal approximation to the multinomial). */
export function netInterval(positive = 0, negative = 0, total = 0) {
  if (!total) return { net: null, lo: null, hi: null, n: 0 }
  const a = positive / total
  const b = negative / total
  const net = a - b
  const half = 1.96 * Math.sqrt(Math.max(0, a + b - net * net) / total)
  return { net, lo: Math.max(-1, net - half), hi: Math.min(1, net + half), n: total }
}

export const countsTotal = (s) => (s ? (s.positive ?? 0) + (s.neutral ?? 0) + (s.negative ?? 0) : 0)

export const fromCounts = (s) => netInterval(s?.positive, s?.negative, countsTotal(s))

/** Gray when the interval crosses zero (we cannot tell it from neutral), otherwise the side it is on. */
export function leanColor({ lo, hi }) {
  if (lo == null) return "var(--neu)"
  if (hi < 0) return "var(--neg)"
  if (lo > 0) return "var(--pos)"
  return "var(--neu)"
}

/** Below this many texts a net sentiment is too noisy to show as a number. */
export const MIN_SAMPLE = 30

/** Sum sentiment counts over rows of {positive, neutral, negative}. */
export function sumCounts(rows) {
  return rows.reduce(
    (acc, r) => ({
      positive: acc.positive + (r?.positive ?? 0),
      neutral: acc.neutral + (r?.neutral ?? 0),
      negative: acc.negative + (r?.negative ?? 0),
    }),
    { positive: 0, neutral: 0, negative: 0 },
  )
}

/** Rolling pooled net sentiment over `window` rows; null where the pooled total is under `minN`. */
export function rollingNet(rows, window = 3, minN = 1) {
  return rows.map((_, i) => {
    const pooled = sumCounts(rows.slice(Math.max(0, i - window + 1), i + 1))
    const n = countsTotal(pooled)
    return { n, net: n >= minN ? (pooled.positive - pooled.negative) / n : null }
  })
}

export function pearson(xs, ys) {
  const n = xs.length
  if (n < 3) return null
  const mx = xs.reduce((a, b) => a + b, 0) / n
  const my = ys.reduce((a, b) => a + b, 0) / n
  let sxy = 0
  let sxx = 0
  let syy = 0
  for (let i = 0; i < n; i++) {
    sxy += (xs[i] - mx) * (ys[i] - my)
    sxx += (xs[i] - mx) ** 2
    syy += (ys[i] - my) ** 2
  }
  return sxx && syy ? sxy / Math.sqrt(sxx * syy) : null
}

/** A CSS color between negative, neutral and positive for a value in [-limit, limit]. */
export function divergingColor(value, limit = 0.6) {
  if (value == null) return "var(--neu)"
  const amount = Math.round(Math.min(1, Math.abs(value) / limit) * 100)
  return `color-mix(in oklab, ${value > 0 ? "var(--pos)" : "var(--neg)"} ${amount}%, var(--neu))`
}
