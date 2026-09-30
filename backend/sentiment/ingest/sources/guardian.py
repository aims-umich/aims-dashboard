"""The Guardian: Content API search, scored sentence by sentence.

Each article becomes one document with one segment per sentence that mentions a nuclear term,
matching the extract-then-score approach of the original Guardian dashboard.
Sentence extraction is rule-based (the old GPT step used a retired model and cost money).
Only the standfirst and the extracted sentences are stored, not the full article body.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from sentiment.ingest.base import (
    DocumentIn,
    Job,
    PollResult,
    SegmentIn,
    SourceDisabledError,
    raise_for_status,
)
from sentiment.text import classify_relevance, nuclear_sentences, strip_html

PLATFORM = "guardian"
SEARCH_URL = "https://content.guardianapis.com/search"
PAGE_SIZE = 50
MAX_PAGES = 10
FIRST_RUN_DAYS = 3


def is_about_us(result: dict[str, Any]) -> bool:
    """The Guardian's own classification: the US news section, or a US tag on an article elsewhere."""
    if result.get("sectionId") == "us-news":
        return True
    return any(
        tag.get("id") == "world/usa" or str(tag.get("id", "")).startswith("us-news/")
        for tag in result.get("tags") or []
    )


def parse_result(result: dict[str, Any]) -> DocumentIn | None:
    if result.get("type") not in (None, "article"):
        return None
    fields = result.get("fields") or {}
    body = fields.get("bodyText") or ""
    sentences = nuclear_sentences(body)
    segments = [SegmentIn(s, classify_relevance(s, lang="en")) for s in sentences]
    word_count = fields.get("wordcount")
    return DocumentIn(
        platform=PLATFORM,
        external_id=result["id"],
        kind="article",
        published_at=datetime.fromisoformat(result["webPublicationDate"].replace("Z", "+00:00")),
        url=result.get("webUrl"),
        author_handle=fields.get("byline") or None,
        title=result.get("webTitle"),
        body=strip_html(fields.get("trailText") or "") or None,
        lang="en",
        segments=segments,
        metrics={"word_count": int(word_count)} if str(word_count or "").isdigit() else {},
        raw={"section": result.get("sectionName"), "us": is_about_us(result)},
    )


class GuardianJob(Job):
    name = "guardian"
    platform = PLATFORM

    @property
    def interval_s(self) -> float:
        return self.settings.guardian_interval_s

    def _key(self) -> str:
        if not self.settings.guardian_api_key:
            raise SourceDisabledError("GUARDIAN_API_KEY is not set")
        return self.settings.guardian_api_key.get_secret_value()

    def secrets(self) -> list[str]:
        key = self.settings.guardian_api_key
        return [key.get_secret_value()] if key else []

    async def poll(self, cursor: dict[str, Any]) -> PollResult:
        key = self._key()
        if cursor.get("latest"):
            since = datetime.fromisoformat(cursor["latest"]) - timedelta(days=1)
        else:
            since = datetime.now(UTC) - timedelta(days=FIRST_RUN_DAYS)
        params: dict[str, Any] = {
            "q": self.settings.guardian_query,
            "type": "article",
            "from-date": since.date().isoformat(),
            "use-date": "published",
            "order-by": "newest",
            "page-size": PAGE_SIZE,
            "show-fields": "bodyText,byline,wordcount,trailText",
            "show-tags": "keyword",
            "api-key": key,
        }
        if self.settings.guardian_section:
            params["section"] = self.settings.guardian_section
        documents: list[DocumentIn] = []
        fetched = 0
        latest = cursor.get("latest")
        for page in range(1, MAX_PAGES + 1):
            response = await self.client.get(SEARCH_URL, params={**params, "page": page})
            raise_for_status(response)
            body = response.json()["response"]
            results = body.get("results", [])
            fetched += len(results)
            for result in results:
                doc = parse_result(result)
                if doc:
                    documents.append(doc)
                    stamp = doc.published_at.astimezone(UTC).isoformat()
                    latest = max(latest, stamp) if latest else stamp
            if page >= int(body.get("pages", 1)):
                break
            await asyncio.sleep(1)
        return PollResult(documents=documents, cursor={"latest": latest} if latest else {}, fetched=fetched)
