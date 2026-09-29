// Same-origin by default: Vercel rewrites /api/* to the API server, and Vite proxies it in development.
const BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "")

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

export async function getJson(path, { signal } = {}) {
  let response
  try {
    response = await fetch(`${BASE}/api/v1${path}`, { signal, headers: { Accept: "application/json" } })
  } catch (error) {
    if (error.name === "AbortError") throw error
    throw new ApiError(0, "Could not reach the data server.")
  }
  if (!response.ok) {
    throw new ApiError(response.status, `The data server returned an error (${response.status}).`)
  }
  return response.json()
}
