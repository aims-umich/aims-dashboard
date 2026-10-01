import { useCallback, useEffect, useRef, useState } from "react"

/**
 * Hover over a chart laid out as `count` equal columns. Returns the hovered column and the pointer position
 * in pixels relative to the element, so a tooltip can sit beside it.
 */
export function useColumnHover(count) {
  const ref = useRef(null)
  const [hover, setHover] = useState(null)

  const onPointerMove = useCallback(
    (event) => {
      const el = ref.current
      if (!el || !count) return
      const rect = el.getBoundingClientRect()
      const x = event.clientX - rect.left
      const index = Math.max(0, Math.min(count - 1, Math.floor((x / rect.width) * count)))
      setHover({ index, x, y: event.clientY - rect.top, width: rect.width })
    },
    [count],
  )
  const onPointerLeave = useCallback(() => setHover(null), [])
  return { ref, hover, handlers: { onPointerMove, onPointerLeave } }
}

/** Hover over discrete marks: each mark calls `enter(item, event)`; positions are relative to `ref`. */
export function useMarkHover() {
  const ref = useRef(null)
  const [hover, setHover] = useState(null)
  const enter = useCallback((item, event) => {
    const rect = ref.current?.getBoundingClientRect()
    if (!rect) return
    setHover({ item, x: event.clientX - rect.left, y: event.clientY - rect.top, width: rect.width })
  }, [])
  const leave = useCallback(() => setHover(null), [])
  return { ref, hover, enter, leave }
}

/** The element's current width in pixels, kept up to date as it resizes. */
export function useWidth() {
  const ref = useRef(null)
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])
  return [ref, width]
}

/**
 * Greedy label placement for a scatter: each label tries its preferred side, then the other, then steps
 * up or down until it no longer overlaps a label already placed. Positions are in pixels.
 */
export function placeLabels(points, { width, height, charWidth = 7.4, lineHeight = 18 }) {
  // Every dot is an obstacle from the start, so no label covers any dot.
  const placed = points.map((pt) => ({ x: pt.x - pt.r, y: pt.y - pt.r, w: pt.r * 2, h: pt.r * 2 }))
  const overlaps = (box) =>
    placed.some((p) => box.x < p.x + p.w && box.x + box.w > p.x && box.y < p.y + p.h && box.y + box.h > p.y)
  const order = [...points].sort((a, b) => b.r - a.r)
  const result = {}
  for (const pt of order) {
    const w = pt.label.length * charWidth
    const prefer = pt.x + pt.r + 8 + w > width ? "left" : "right"
    let chosen = null
    outer: for (const dy of [0, -18, 18, -36, 36, -54, 54, -72, 72, -90, 90, -108, 108]) {
      for (const side of [prefer, prefer === "right" ? "left" : "right"]) {
        const x = side === "right" ? pt.x + pt.r + 8 : pt.x - pt.r - 8 - w
        const y = pt.y - lineHeight / 2 + dy
        const box = { x, y, w, h: lineHeight }
        if (x < 0 || x + w > width || y < 0 || y + lineHeight > height) continue
        if (!overlaps(box)) {
          chosen = { ...box, side, dy }
          break outer
        }
      }
    }
    // No clean spot (a crowded or narrow chart): leave the label out; the dot keeps its tooltip.
    if (chosen) placed.push(chosen)
    result[pt.id] = chosen
  }
  return result
}
