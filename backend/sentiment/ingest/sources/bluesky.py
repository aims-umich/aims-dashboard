"""Bluesky: the full public post stream through Jetstream, plus an hourly engagement refresh.

Jetstream needs no account or key.
We filter the stream for nuclear-energy posts ourselves, honor deletions as they arrive,
and later refresh likes/reposts/replies (and the author's handle) through the public AppView.
"""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import certifi
import websockets

from sentiment.config import split_csv
from sentiment.ingest.base import DocumentIn, Job, PollResult, SegmentIn, raise_for_status
from sentiment.observability import Heartbeat
from sentiment.text import RELEVANT, classify_relevance, has_anchor, normalize

log = logging.getLogger(__name__)

PLATFORM = "bluesky"
POST_COLLECTION = "app.bsky.feed.post"
# Self-applied content labels that mark a post as adult content; never shown on the dashboard.
ADULT_LABELS = frozenset({"porn", "sexual", "nudity", "graphic-media", "gore"})
# Moderation labels from Bluesky's own labeler that mean the post should not be displayed.
HIDE_LABELS = ADULT_LABELS | {"spam", "!hide", "!takedown", "!warn"}
COMMIT_EVERY_S = 30.0
STALL_AFTER_S = 90.0
REWIND_US = 5_000_000  # Re-read 5 s on reconnect; upserts make the overlap harmless.


def at_uri(did: str, rkey: str) -> str:
    return f"at://{did}/{POST_COLLECTION}/{rkey}"


def post_url(did: str, rkey: str) -> str:
    return f"https://bsky.app/profile/{did}/post/{rkey}"


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_event(event: dict[str, Any]) -> DocumentIn | tuple[str, str] | None:
    """Turn one Jetstream event into a document, a deletion key, or None (not ours)."""
    if event.get("kind") != "commit":
        return None
    commit = event.get("commit") or {}
    if commit.get("collection") != POST_COLLECTION:
        return None
    did, rkey = event.get("did"), commit.get("rkey")
    if not did or not rkey:
        return None
    if commit.get("operation") == "delete":
        return (PLATFORM, at_uri(did, rkey))
    if commit.get("operation") != "create":
        return None
    record = commit.get("record") or {}
    text = normalize(record.get("text") or "")
    if not text or not has_anchor(text):
        return None
    self_labels = {
        v.get("val") for v in (record.get("labels") or {}).get("values", []) if isinstance(v, dict)
    }
    if self_labels & ADULT_LABELS:
        return None
    langs = record.get("langs") or []
    lang = langs[0] if langs else None
    relevance = classify_relevance(text, lang=lang)
    if relevance.status != RELEVANT:
        return None  # The stream is huge; only keep what we will score.
    event_time = datetime.fromtimestamp(event["time_us"] / 1_000_000, tz=UTC)
    created = _parse_time(record.get("createdAt"))
    # Clients set createdAt themselves; distrust it when it is far from when the relay saw the post.
    published = created if created and abs(created - event_time) < timedelta(days=1) else event_time
    reply = record.get("reply")
    embed_type = (record.get("embed") or {}).get("$type")
    return DocumentIn(
        platform=PLATFORM,
        external_id=at_uri(did, rkey),
        kind="post",
        published_at=published,
        url=post_url(did, rkey),
        body=text,
        lang=lang,
        segments=[SegmentIn(text, relevance)],
        raw={"cid": commit.get("cid"), "is_reply": bool(reply), "embed": embed_type, "langs": langs},
    )


class BlueskyStreamJob(Job):
    name = "bluesky"
    platform = PLATFORM

    @property
    def interval_s(self) -> float:
        return COMMIT_EVERY_S

    async def stream(
        self,
        cursor: dict[str, Any],
        commit: Callable[[PollResult], Awaitable[Any]],
        heartbeat: Heartbeat,
        stopping: asyncio.Event,
    ) -> None:
        urls = split_csv(self.settings.bluesky_jetstream_urls)
        endpoint = urls[int(cursor.get("endpoint", 0)) % len(urls)]
        time_us = cursor.get("time_us")
        params = f"?wantedCollections={POST_COLLECTION}"
        if time_us:
            params += f"&cursor={int(time_us) - REWIND_US}"
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        pending: list[DocumentIn] = []
        deletions: list[tuple[str, str]] = []
        seen = 0
        last_commit = last_message = time.monotonic()
        last_time_us = int(time_us) if time_us else None
        endpoint_index = urls.index(endpoint)
        log.info("connecting to jetstream", extra={"endpoint": endpoint, "resume": bool(time_us)})
        try:
            async with websockets.connect(
                endpoint + params, ssl=ssl_context, max_size=2**22, open_timeout=20, ping_interval=30
            ) as ws:
                while not stopping.is_set():
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=5)
                        last_message = time.monotonic()
                    except TimeoutError:
                        message = None
                        if time.monotonic() - last_message > STALL_AFTER_S:
                            # The network never goes quiet this long; the connection is dead.
                            raise ConnectionError("jetstream stalled") from None
                    if message is not None:
                        event = json.loads(message)
                        seen += 1
                        last_time_us = event.get("time_us", last_time_us)
                        parsed = parse_event(event)
                        if isinstance(parsed, DocumentIn):
                            pending.append(parsed)
                        elif isinstance(parsed, tuple):
                            deletions.append(parsed)
                    if time.monotonic() - last_commit >= COMMIT_EVERY_S:
                        await commit(
                            PollResult(
                                documents=pending,
                                cursor={"time_us": last_time_us, "endpoint": endpoint_index},
                                fetched=seen,
                                deletions=deletions,
                            )
                        )
                        await heartbeat.ping()
                        pending, deletions, seen = [], [], 0
                        last_commit = time.monotonic()
        except (OSError, websockets.WebSocketException):
            # Fail over to the next public Jetstream instance on the next attempt.
            await commit(
                PollResult(
                    documents=pending,
                    cursor={"time_us": last_time_us, "endpoint": endpoint_index + 1},
                    fetched=seen,
                    deletions=deletions,
                )
            )
            raise
        if pending or deletions:
            await commit(
                PollResult(
                    documents=pending,
                    cursor={"time_us": last_time_us, "endpoint": endpoint_index},
                    fetched=seen,
                    deletions=deletions,
                )
            )


class BlueskyMetricsJob(Job):
    """Refreshes engagement counts for recent posts and drops posts Bluesky has removed or labeled."""

    name = "bluesky_metrics"
    platform = PLATFORM
    BATCH = 25  # app.bsky.feed.getPosts accepts up to 25 URIs.

    @property
    def interval_s(self) -> float:
        return self.settings.bluesky_metrics_interval_s

    async def recent_uris(self) -> list[str]:
        async with self.pool.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    SELECT external_id FROM documents
                    WHERE platform = %s AND published_at > now() - make_interval(days => %s)
                    ORDER BY published_at DESC
                    """,
                    (PLATFORM, self.settings.bluesky_metrics_window_days),
                )
            ).fetchall()
        return [row["external_id"] for row in rows]

    async def poll(self, cursor: dict[str, Any]) -> PollResult:
        uris = await self.recent_uris()
        updates: list[tuple[str, str, dict[str, Any]]] = []
        deletions: list[tuple[str, str]] = []
        base = self.settings.bluesky_appview_url.rstrip("/")
        for start in range(0, len(uris), self.BATCH):
            chunk = uris[start : start + self.BATCH]
            response = await self.client.get(f"{base}/xrpc/app.bsky.feed.getPosts", params={"uris": chunk})
            raise_for_status(response)
            found = {}
            for post in response.json().get("posts", []):
                found[post["uri"]] = post
            for uri in chunk:
                post = found.get(uri)
                labels = {label.get("val") for label in (post or {}).get("labels", [])}
                if post is None or labels & HIDE_LABELS:
                    deletions.append((PLATFORM, uri))
                    continue
                updates.append(
                    (
                        PLATFORM,
                        uri,
                        {
                            "likes": post.get("likeCount", 0),
                            "reposts": post.get("repostCount", 0),
                            "replies": post.get("replyCount", 0),
                            "quotes": post.get("quoteCount", 0),
                            "_author_handle": (post.get("author") or {}).get("handle"),
                        },
                    )
                )
            await asyncio.sleep(0.2)
        return PollResult(
            documents=[],
            cursor={"refreshed": len(updates), "removed": len(deletions)},
            fetched=len(uris),
            metric_updates=updates,
            deletions=deletions,
        )
