"""Mastodon: public hashtag timelines on the configured instances.

Each (instance, hashtag) pair keeps its own `min_id` cursor, so every poll only reads new posts.
Posts bridged in from Bluesky are skipped because the Bluesky collector already has them.
Accounts that opted out of indexing (`noindex`) and bot accounts are skipped.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from sentiment.config import split_csv
from sentiment.ingest.base import DocumentIn, Job, PollResult, SegmentIn, raise_for_status
from sentiment.text import classify_relevance, strip_html

PLATFORM = "mastodon"
PAGE_SIZE = 40
MAX_PAGES_PER_TAG = 5
BRIDGE_HOSTS = ("brid.gy", "bsky.brid.gy")


def _tokens(raw: str | None) -> dict[str, str]:
    tokens = {}
    for item in split_csv(raw or ""):
        instance, _, token = item.partition("=")
        if token:
            tokens[instance.strip()] = token.strip()
    return tokens


def parse_status(status: dict[str, Any], instance: str) -> DocumentIn | None:
    if status.get("reblog") or status.get("visibility") != "public":
        return None
    uri = status.get("uri") or ""
    if any(host in uri for host in BRIDGE_HOSTS):
        return None
    account = status.get("account") or {}
    # Respect accounts that opted out of indexing, and leave out bots: automated feeds are not opinion.
    if account.get("noindex") or account.get("bot"):
        return None
    text = strip_html(status.get("content") or "")
    if status.get("spoiler_text"):
        text = f"{status['spoiler_text']}\n{text}".strip()
    if not text:
        return None
    acct = account.get("acct") or account.get("username")
    handle = acct if acct is None or "@" in acct else f"{acct}@{instance}"
    lang = status.get("language")
    return DocumentIn(
        platform=PLATFORM,
        external_id=uri,
        kind="post",
        published_at=datetime.fromisoformat(status["created_at"].replace("Z", "+00:00")),
        url=status.get("url") or uri,
        author_handle=handle,
        body=text,
        lang=lang,
        segments=[SegmentIn(text, classify_relevance(text, lang=lang))],
        metrics={
            "replies": status.get("replies_count", 0),
            "reposts": status.get("reblogs_count", 0),
            "likes": status.get("favourites_count", 0),
            "sensitive": bool(status.get("sensitive")),
            "has_media": bool(status.get("media_attachments")),
        },
        raw={
            "id": status.get("id"),
            "instance": instance,
            "tags": [t.get("name") for t in status.get("tags", [])],
        },
    )


class MastodonJob(Job):
    name = "mastodon"
    platform = PLATFORM

    @property
    def interval_s(self) -> float:
        return self.settings.mastodon_interval_s

    def secrets(self) -> list[str]:
        return list(_tokens(self._raw_tokens()).values())

    def _raw_tokens(self) -> str | None:
        token = self.settings.mastodon_access_tokens
        return token.get_secret_value() if token else None

    async def poll(self, cursor: dict[str, Any]) -> PollResult:
        tokens = _tokens(self._raw_tokens())
        new_cursor = dict(cursor)
        documents: dict[str, DocumentIn] = {}
        fetched = 0
        for instance in split_csv(self.settings.mastodon_instances):
            headers = {"Authorization": f"Bearer {tokens[instance]}"} if instance in tokens else {}
            for tag in split_csv(self.settings.mastodon_hashtags):
                key = f"{instance}/{tag}"
                min_id = cursor.get(key)
                for _ in range(MAX_PAGES_PER_TAG if min_id else 1):
                    params: dict[str, Any] = {"limit": PAGE_SIZE}
                    if min_id:
                        params["min_id"] = min_id
                    response = await self.client.get(
                        f"https://{instance}/api/v1/timelines/tag/{tag}", params=params, headers=headers
                    )
                    raise_for_status(response)
                    statuses = response.json()
                    if not statuses:
                        break
                    fetched += len(statuses)
                    for status in statuses:
                        doc = parse_status(status, instance)
                        if doc:
                            documents[doc.external_id] = doc
                    # Status ids are sortable snowflakes; compare as integers.
                    min_id = str(max(int(s["id"]) for s in statuses))
                    new_cursor[key] = min_id
                    if len(statuses) < PAGE_SIZE:
                        break
                await asyncio.sleep(0.5)
        return PollResult(documents=list(documents.values()), cursor=new_cursor, fetched=fetched)
