"""The New York Times: Article Search polling.

The API returns the headline, abstract, and (on some articles) the lead paragraph, never full text,
so each article is scored on the text we are allowed to get: one segment of abstract + lead paragraph.
The API allows about 5 requests per minute, so pages are spaced 12 seconds apart.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from sentiment.ingest.base import (
    DocumentIn,
    Job,
    PollResult,
    SegmentIn,
    SourceDisabledError,
    raise_for_status,
)
from sentiment.text import classify_with_headline, has_anchor, normalize

PLATFORM = "nyt"
SEARCH_URL = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
ARCHIVE_URL = "https://api.nytimes.com/svc/archive/v1/{year}/{month}.json"
MAX_PAGES = 3
REQUEST_SPACING_S = 12.5
FIRST_RUN_DAYS = 3


def _published(value: str) -> datetime:
    # NYT uses both "2026-09-29T12:00:00+0000" and "2026-09-29T12:00:00Z".
    value = value.replace("Z", "+00:00")
    if len(value) >= 5 and value[-5] in "+-" and value[-3] != ":":
        value = value[:-2] + ":" + value[-2:]
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_doc(doc: dict[str, Any]) -> DocumentIn | None:
    headline = (doc.get("headline") or {}).get("main") or ""
    parts: list[str] = []
    for key in ("abstract", "lead_paragraph", "snippet"):
        text = normalize(doc.get(key) or "")
        if text and text not in parts and not any(text in p for p in parts):
            parts.append(text)
    text = " ".join(parts)
    if not text:
        return None
    relevance = classify_with_headline(text, headline)
    byline = (doc.get("byline") or {}).get("original")
    return DocumentIn(
        platform=PLATFORM,
        external_id=doc.get("_id") or doc.get("uri") or doc["web_url"],
        kind="article",
        published_at=_published(doc["pub_date"]),
        url=doc.get("web_url"),
        author_handle=byline.removeprefix("By ").strip() if byline else None,
        title=headline or None,
        body=text,
        lang="en",
        segments=[SegmentIn(text, relevance)],
        metrics={"word_count": doc["word_count"]} if doc.get("word_count") else {},
        raw={"section": doc.get("section_name"), "type": doc.get("type_of_material")},
    )


class NytJob(Job):
    name = "nyt"
    platform = PLATFORM

    @property
    def interval_s(self) -> float:
        return self.settings.nyt_interval_s

    def _key(self) -> str:
        if not self.settings.nyt_api_key:
            raise SourceDisabledError("NYT_API_KEY is not set")
        return self.settings.nyt_api_key.get_secret_value()

    def secrets(self) -> list[str]:
        key = self.settings.nyt_api_key
        return [key.get_secret_value()] if key else []

    async def poll(self, cursor: dict[str, Any]) -> PollResult:
        key = self._key()
        if cursor.get("latest"):
            since = datetime.fromisoformat(cursor["latest"]) - timedelta(days=1)
        else:
            since = datetime.now(UTC) - timedelta(days=FIRST_RUN_DAYS)
        documents: list[DocumentIn] = []
        fetched = 0
        latest = cursor.get("latest")
        for page in range(MAX_PAGES):
            if page:
                await asyncio.sleep(REQUEST_SPACING_S)
            response = await self.client.get(
                SEARCH_URL,
                params={
                    "q": self.settings.nyt_query,
                    "begin_date": since.strftime("%Y%m%d"),
                    "sort": "newest",
                    "page": page,
                    "api-key": key,
                },
            )
            raise_for_status(response)
            docs = (response.json().get("response") or {}).get("docs") or []
            fetched += len(docs)
            for raw in docs:
                doc = parse_doc(raw)
                if doc:
                    documents.append(doc)
                    stamp = doc.published_at.astimezone(UTC).isoformat()
                    latest = max(latest, stamp) if latest else stamp
            if len(docs) < 10:
                break
        return PollResult(documents=documents, cursor={"latest": latest} if latest else {}, fetched=fetched)


async def archive_month(
    client: httpx.AsyncClient, key: str, year: int, month: int
) -> tuple[int, list[DocumentIn]]:
    """Every NYT article of one month (Archive API), narrowed to those that mention a nuclear term.

    Returns (articles in the month, documents kept). One call per month; the response is large.
    """
    response = await client.get(
        ARCHIVE_URL.format(year=year, month=month), params={"api-key": key}, timeout=120
    )
    raise_for_status(response)
    docs = (response.json().get("response") or {}).get("docs") or []
    kept = []
    for raw in docs:
        headline = (raw.get("headline") or {}).get("main") or ""
        text = " ".join(filter(None, (headline, raw.get("abstract"), raw.get("lead_paragraph"))))
        if not has_anchor(text) or not raw.get("pub_date"):
            continue
        doc = parse_doc(raw)
        if doc:
            doc.origin = "backfill"
            kept.append(doc)
    return len(docs), kept
