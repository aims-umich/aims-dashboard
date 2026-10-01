import { useEffect } from "react"

export function useDocumentTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} · Nuclear Sentiment Analysis` : "Nuclear Sentiment Analysis · AIMS Lab"
  }, [title])
}
