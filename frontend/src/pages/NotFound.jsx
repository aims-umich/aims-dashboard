import { Link } from "react-router-dom"
import { useDocumentTitle } from "../lib/useDocumentTitle"

export default function NotFound() {
  useDocumentTitle("Not found")
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center py-24 text-center">
      <p className="text-sm font-semibold text-indigo-600 dark:text-indigo-400">404</p>
      <h1 className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">This page does not exist</h1>
      <p className="mt-3 text-gray-600 dark:text-gray-300">
        The dashboard you are looking for may have moved or is not collecting data right now.
      </p>
      <Link to="/" className="mt-6 font-medium text-indigo-600 hover:underline dark:text-indigo-400">
        Go to all dashboards
      </Link>
    </div>
  )
}
