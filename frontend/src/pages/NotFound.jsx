import { Link } from "react-router-dom"
import { useDocumentTitle } from "../lib/useDocumentTitle"

export default function NotFound() {
  useDocumentTitle("Not found")
  return (
    <section className="flex flex-col items-start gap-4 py-24">
      <span className="num text-xs tracking-[0.1em] text-ink3">404</span>
      <h1 className="m-0 text-4xl font-extrabold tracking-[-0.02em] wider">This page does not exist</h1>
      <p className="m-0 text-ink2">The address may be from an older version of the dashboard.</p>
      <Link to="/" className="flex min-h-11 items-center rounded-[10px] bg-ink px-5 font-semibold text-bg no-underline">
        Back to the overview
      </Link>
    </section>
  )
}
