import { lazy } from "react"

// The overview loads with the app; every other page is fetched when first visited.
export const SourcePage = lazy(() => import("./SourcePage"))
export const Compare = lazy(() => import("./Compare"))
export const Topics = lazy(() => import("./Topics"))
export const Events = lazy(() => import("./Events"))
export const Model = lazy(() => import("./Model"))
export const About = lazy(() => import("./About"))
