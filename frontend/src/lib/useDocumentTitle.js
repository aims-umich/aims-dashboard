import { useEffect } from "react"

export function useDocumentTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} · Nuclear Energy Sentiment` : "Nuclear Energy Sentiment · AIMS Lab"
  }, [title])
}
