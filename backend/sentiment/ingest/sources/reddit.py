"""Reddit: search and subreddit /new feeds through the official OAuth API.

Since November 2025 Reddit requires approval for API access (Responsible Builder Policy).
This collector is off until the research-track application is approved: add "reddit" to
ENABLED_SOURCES and set REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET.
Reddit's terms require removing content its authors delete, so a daily compliance job re-checks
every stored post and deletes the ones that are gone.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from sentiment.config import split_csv
from sentiment.ingest.base import (
    DocumentIn,
    Job,
    PollResult,
    SegmentIn,
    SourceDisabledError,
    raise_for_status,
)
from sentiment.text import classify_relevance, normalize

PLATFORM = "reddit"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"  # noqa: S105 - a URL, not a secret
API = "https://oauth.reddit.com"
REMOVED_TEXT = {"[removed]", "[deleted]"}


def is_removed(post: dict[str, Any]) -> bool:
    return bool(
        post.get("removed_by_category")
        or post.get("author") == "[deleted]"
        or (post.get("selftext") or "").strip() in REMOVED_TEXT
    )


def parse_post(post: dict[str, Any]) -> DocumentIn | None:
    if post.get("over_18") or is_removed(post):
        return None
    title = normalize(post.get("title") or "")
    selftext = normalize(post.get("selftext") or "")
    text = f"{title}\n{selftext}".strip() if selftext else title
    if not text:
        return None
    return DocumentIn(
        platform=PLATFORM,
        external_id=post["name"],
        kind="post",
        published_at=datetime.fromtimestamp(float(post["created_utc"]), tz=UTC),
        url=f"https://www.reddit.com{post['permalink']}",
        author_handle=post.get("author"),
        title=title or None,
        body=text,
        segments=[SegmentIn(text, classify_relevance(text))],
        metrics=post_metrics(post),
        raw={"subreddit": post.get("subreddit")},
    )


def post_metrics(post: dict[str, Any]) -> dict[str, Any]:
    return {
        "score": post.get("score", 0),
        "comments": post.get("num_comments", 0),
        "upvote_ratio": post.get("upvote_ratio"),
    }


class _RedditJob(Job):
    platform = PLATFORM
    _token: str | None = None
    _token_expires: float = 0.0

    def secrets(self) -> list[str]:
        values = [self.settings.reddit_client_id, self.settings.reddit_client_secret]
        return [v.get_secret_value() for v in values if v] + ([self._token] if self._token else [])

    async def _auth_header(self) -> dict[str, str]:
        settings = self.settings
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            raise SourceDisabledError("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are not set")
        if not self._token or time.time() > self._token_expires - 60:
            response = await self.client.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=httpx.BasicAuth(
                    settings.reddit_client_id.get_secret_value(),
                    settings.reddit_client_secret.get_secret_value(),
                ),
                headers={"User-Agent": settings.reddit_user_agent},
            )
            raise_for_status(response)
            body = response.json()
            self._token = body["access_token"]
            self._token_expires = time.time() + float(body.get("expires_in", 3600))
        return {"Authorization": f"Bearer {self._token}", "User-Agent": settings.reddit_user_agent}

    async def _get(self, path: str, **params: Any) -> dict[str, Any]:
        response = await self.client.get(
            f"{API}{path}", params={**params, "raw_json": 1}, headers=await self._auth_header()
        )
        raise_for_status(response)
        # Stay well under the per-client limit reported in the headers.
        remaining = float(response.headers.get("x-ratelimit-remaining", "100") or 100)
        if remaining < 10:
            await asyncio.sleep(float(response.headers.get("x-ratelimit-reset", "60") or 60))
        return response.json()


class RedditJob(_RedditJob):
    name = "reddit"

    @property
    def interval_s(self) -> float:
        return self.settings.reddit_interval_s

    def feeds(self) -> list[tuple[str, str, dict[str, Any]]]:
        feeds = [("search", "/search", {"q": self.settings.reddit_query, "sort": "new", "type": "link"})]
        feeds += [(f"r/{sub}", f"/r/{sub}/new", {}) for sub in split_csv(self.settings.reddit_subreddits)]
        return feeds

    async def poll(self, cursor: dict[str, Any]) -> PollResult:
        new_cursor = dict(cursor)
        documents: dict[str, DocumentIn] = {}
        fetched = 0
        for key, path, params in self.feeds():
            newest_seen = float(cursor.get(key, 0))
            data = await self._get(path, limit=100, **params)
            children = [child["data"] for child in data.get("data", {}).get("children", [])]
            fetched += len(children)
            for post in children:
                if float(post.get("created_utc", 0)) <= newest_seen:
                    continue
                doc = parse_post(post)
                if doc:
                    documents[doc.external_id] = doc
            if children:
                new_cursor[key] = max(newest_seen, *(float(p.get("created_utc", 0)) for p in children))
        return PollResult(documents=list(documents.values()), cursor=new_cursor, fetched=fetched)


class RedditComplianceJob(_RedditJob):
    """Deletes stored posts that were removed or deleted on Reddit, and refreshes their scores."""

    name = "reddit_compliance"

    @property
    def interval_s(self) -> float:
        return self.settings.reddit_compliance_interval_s

    async def stored_ids(self) -> list[str]:
        async with self.pool.connection() as conn:
            rows = await (
                await conn.execute("SELECT external_id FROM documents WHERE platform = %s", (PLATFORM,))
            ).fetchall()
        return [row["external_id"] for row in rows]

    async def poll(self, cursor: dict[str, Any]) -> PollResult:
        ids = await self.stored_ids()
        deletions: list[tuple[str, str]] = []
        updates: list[tuple[str, str, dict[str, Any]]] = []
        for start in range(0, len(ids), 100):
            chunk = ids[start : start + 100]
            data = await self._get("/api/info", id=",".join(chunk))
            found = {
                child["data"]["name"]: child["data"] for child in data.get("data", {}).get("children", [])
            }
            for fullname in chunk:
                post = found.get(fullname)
                if post is None or is_removed(post):
                    deletions.append((PLATFORM, fullname))
                else:
                    updates.append((PLATFORM, fullname, post_metrics(post)))
        return PollResult(
            documents=[],
            cursor={"checked": len(ids), "removed": len(deletions)},
            fetched=len(ids),
            metric_updates=updates,
            deletions=deletions,
        )
