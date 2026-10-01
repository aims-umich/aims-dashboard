import { Analytics } from "@vercel/analytics/react"
import React from "react"
import ReactDOM from "react-dom/client"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import "./index.css"
import Layout from "./Layout"
import { PLATFORMS } from "./lib/platforms"
import Home from "./pages/Home"
import NotFound from "./pages/NotFound"

import { About, Compare, Events, Model, SourcePage, Topics } from "./pages/lazy"

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          {Object.values(PLATFORMS).map((p) => (
            <Route key={p.key} path={p.route} element={<SourcePage key={p.key} platform={p.key} />} />
          ))}
          <Route path="/compare" element={<Compare />} />
          <Route path="/topics" element={<Topics />} />
          <Route path="/events" element={<Events />} />
          <Route path="/model" element={<Model />} />
          <Route path="/about" element={<About />} />
          {/* Old URLs from the local demo. */}
          <Route path="/times" element={<Navigate to="/nyt" replace />} />
          <Route path="/instagram" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
    {import.meta.env.ON_VERCEL && <Analytics />}
  </React.StrictMode>,
)
