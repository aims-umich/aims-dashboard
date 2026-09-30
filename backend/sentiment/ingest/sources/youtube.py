"""YouTube: find new nuclear-energy videos, then follow their comment threads.

Comments are what gets scored (as in the original YouTube dashboard); a comment inherits its topic
from the video, so it only has to be English, not mention "nuclear" itself.
Quota (10,000 units/day by default): search.list costs 100 units, so search runs every 30 minutes
(~4,800 units/day); commentThreads.list and videos.list cost 1 unit each.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sentiment.ingest.base import (
    DocumentIn,
    Job,
    PollResult,
    RateLimitedError,
    SegmentIn,
    SourceDisabledError,
    raise_for_status,
)
from sentiment.text import RELEVANT, classify_relevance, normalize

PLATFORM = "youtube"
API = "https://www.googleapis.com/youtube/v3"
FIRST_RUN_HOURS = 48
MAX_COMMENT_PAGES = 3


def seconds_until_quota_reset(now: datetime | None = None) -> float:
    """YouTube quotas reset at midnight Pacific time."""
    pacific = ZoneInfo("America/Los_Angeles")
    now = (now or datetime.now(UTC)).astimezone(pacific)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
    return (tomorrow - now).total_seconds()


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def parse_video(item: dict[str, Any]) -> DocumentIn | None:
    snippet = item.get("snippet") or {}
    title = normalize(snippet.get("title") or "")
    description = normalize(snippet.get("description") or "")
    lang = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage")
    relevance = classify_relevance(f"{title}. {description[:1000]}", lang=lang)
    if relevance.status != RELEVANT:
        return None
    stats = item.get("statistics") or {}
    return DocumentIn(
        platform=PLATFORM,
        external_id=item["id"],
        kind="video",
        published_at=_time(snippet["publishedAt"]),
        url=video_url(item["id"]),
        author_handle=snippet.get("channelTitle"),
        title=title,
        body=description[:2000] or None,
        lang=lang,
        metrics=video_metrics(stats),
        raw={"channel_id": snippet.get("channelId")},
    )


def video_metrics(stats: dict[str, Any]) -> dict[str, int]:
    return {
        "views": _int(stats.get("viewCount")),
        "likes": _int(stats.get("likeCount")),
        "comments": _int(stats.get("commentCount")),
    }


def parse_comment_thread(item: dict[str, Any], video_id: str) -> DocumentIn | None:
    top = (item.get("snippet") or {}).get("topLevelComment") or {}
    snippet = top.get("snippet") or {}
    text = normalize(snippet.get("textOriginal") or snippet.get("textDisplay") or "")
    if not text:
        return None
    return DocumentIn(
        platform=PLATFORM,
        external_id=top.get("id") or item["id"],
        kind="comment",
        parent_external_id=video_id,
        published_at=_time(snippet["publishedAt"]),
        url=f"{video_url(video_id)}&lc={top.get('id') or item['id']}",
        author_handle=snippet.get("authorDisplayName"),
        body=text,
        segments=[SegmentIn(text, classify_relevance(text, context_relevant=True))],
        metrics={
            "likes": _int(snippet.get("likeCount")),
            "replies": _int((item.get("snippet") or {}).get("totalReplyCount")),
        },
    )


class _YouTubeJob(Job):
    platform = PLATFORM

    def _key(self) -> str:
        if not self.settings.youtube_api_key:
            raise SourceDisabledError("YOUTUBE_API_KEY is not set")
        return self.settings.youtube_api_key.get_secret_value()

    def secrets(self) -> list[str]:
        key = self.settings.youtube_api_key
        return [key.get_secret_value()] if key else []

    async def _get(self, path: str, **params: Any) -> dict[str, Any]:
        response = await self.client.get(f"{API}/{path}", params={**params, "key": self._key()})
        if response.status_code == 403 and "quotaExceeded" in response.text:
            raise RateLimitedError(seconds_until_quota_reset(), "YouTube daily quota exceeded")
        raise_for_status(response)
        return response.json()

    async def videos(self, ids: list[str]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for start in range(0, len(ids), 50):
            data = await self._get("videos", part="snippet,statistics", id=",".join(ids[start : start + 50]))
            items.extend(data.get("items", []))
        return items


class YouTubeSearchJob(_YouTubeJob):
    name = "youtube"

    @property
    def interval_s(self) -> float:
        return self.settings.youtube_search_interval_s

    async def poll(self, cursor: dict[str, Any]) -> PollResult:
        if cursor.get("latest"):
            since = datetime.fromisoformat(cursor["latest"]) - timedelta(hours=1)
        else:
            since = datetime.now(UTC) - timedelta(hours=FIRST_RUN_HOURS)
        data = await self._get(
            "search",
            part="id",
            q=self.settings.youtube_query,
            type="video",
            order="date",
            maxResults=50,
            publishedAfter=since.strftime("%Y-%m-%dT%H:%M:%SZ"),
            relevanceLanguage="en",
            regionCode=self.settings.youtube_region_code,
        )
        ids = [item["id"]["videoId"] for item in data.get("items", []) if item.get("id", {}).get("videoId")]
        documents = [doc for item in await self.videos(ids) if (doc := parse_video(item))]
        latest = cursor.get("latest")
        for doc in documents:
            stamp = doc.published_at.astimezone(UTC).isoformat()
            latest = max(latest, stamp) if latest else stamp
        return PollResult(documents=documents, cursor={"latest": latest} if latest else {}, fetched=len(ids))


class YouTubeCommentsJob(_YouTubeJob):
    """Reads new top-level comments on recently published tracked videos and refreshes their stats."""

    name = "youtube_comments"

    @property
    def interval_s(self) -> float:
        return self.settings.youtube_comments_interval_s

    async def tracked_videos(self) -> list[str]:
        async with self.pool.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    SELECT external_id FROM documents
                    WHERE platform = %s AND kind = 'video'
                      AND published_at > now() - make_interval(days => %s)
                    ORDER BY published_at DESC LIMIT %s
                    """,
                    (PLATFORM, self.settings.youtube_track_days, self.settings.youtube_max_tracked_videos),
                )
            ).fetchall()
        return [row["external_id"] for row in rows]

    async def poll(self, cursor: dict[str, Any]) -> PollResult:
        video_ids = await self.tracked_videos()
        seen: dict[str, str] = cursor.get("seen", {})
        disabled: list[str] = cursor.get("disabled", [])
        documents: list[DocumentIn] = []
        fetched = 0
        for video_id in video_ids:
            if video_id in disabled:
                continue
            newest = seen.get(video_id)
            page_token = None
            for _ in range(MAX_COMMENT_PAGES):
                try:
                    params: dict[str, Any] = {
                        "part": "snippet",
                        "videoId": video_id,
                        "order": "time",
                        "maxResults": 100,
                        "textFormat": "plainText",
                    }
                    if page_token:
                        params["pageToken"] = page_token
                    data = await self._get("commentThreads", **params)
                except Exception as exc:
                    if "commentsDisabled" in str(exc) or "HTTP 404" in str(exc):
                        disabled.append(video_id)
                        break
                    raise
                items = data.get("items", [])
                fetched += len(items)
                reached_seen = False
                for item in items:
                    doc = parse_comment_thread(item, video_id)
                    if not doc:
                        continue
                    stamp = doc.published_at.astimezone(UTC).isoformat()
                    if newest and stamp <= newest:
                        reached_seen = True
                        continue
                    documents.append(doc)
                page_token = data.get("nextPageToken")
                if reached_seen or not page_token:
                    break
            stamps = [
                d.published_at.astimezone(UTC).isoformat()
                for d in documents
                if d.parent_external_id == video_id
            ]
            if stamps:
                seen[video_id] = max([*stamps, newest] if newest else stamps)
        updates = [
            (PLATFORM, item["id"], video_metrics(item.get("statistics") or {}))
            for item in await self.videos(video_ids)
        ]
        tracked = set(video_ids)
        new_cursor = {
            "seen": {vid: stamp for vid, stamp in seen.items() if vid in tracked},
            "disabled": [vid for vid in disabled if vid in tracked],
        }
        return PollResult(documents=documents, cursor=new_cursor, fetched=fetched, metric_updates=updates)


class YouTubeRefreshJob(_YouTubeJob):
    """Keeps stored YouTube data inside the 30-day limit of the Developer Policies (III.E.4.d-e).

    Comments and videos older than `youtube_refresh_after_days` since their last refresh are re-fetched
    (50 per call, 1 quota unit each): edits are applied and re-scored, and anything YouTube no longer
    returns is deleted. Whatever still could not be refreshed within `youtube_max_age_days` (for example
    during a quota outage) is deleted as a backstop, so nothing is ever kept past 30 days unrefreshed.
    """

    name = "youtube_refresh"
    MAX_PER_RUN = 5000

    @property
    def interval_s(self) -> float:
        return self.settings.youtube_refresh_interval_s

    async def _due(self, kind: str, days: int, limit: int) -> list[str]:
        async with self.pool.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    SELECT external_id FROM documents
                    WHERE platform = %s AND kind = %s
                      AND COALESCE(metrics_updated_at, collected_at) < now() - make_interval(days => %s)
                    ORDER BY COALESCE(metrics_updated_at, collected_at) LIMIT %s
                    """,
                    (PLATFORM, kind, days, limit),
                )
            ).fetchall()
        return [row["external_id"] for row in rows]

    async def poll(self, cursor: dict[str, Any]) -> PollResult:
        refresh_days = self.settings.youtube_refresh_after_days
        updates: list[tuple[str, str, dict[str, Any]]] = []
        deletions: list[tuple[str, str]] = []
        text_updates: list[tuple[str, str, str]] = []

        comment_ids = await self._due("comment", refresh_days, self.MAX_PER_RUN)
        for start in range(0, len(comment_ids), 50):
            chunk = comment_ids[start : start + 50]
            data = await self._get("comments", part="snippet", id=",".join(chunk), textFormat="plainText")
            found = {item["id"]: item.get("snippet") or {} for item in data.get("items", [])}
            for comment_id in chunk:
                snippet = found.get(comment_id)
                if snippet is None:
                    deletions.append((PLATFORM, comment_id))
                    continue
                updates.append((PLATFORM, comment_id, {"likes": _int(snippet.get("likeCount"))}))
                text = normalize(snippet.get("textOriginal") or snippet.get("textDisplay") or "")
                if text:
                    text_updates.append((PLATFORM, comment_id, text))

        video_ids = await self._due("video", refresh_days, self.MAX_PER_RUN)
        returned = {item["id"]: item for item in await self.videos(video_ids)}
        for video_id in video_ids:
            item = returned.get(video_id)
            if item is None:
                deletions.append((PLATFORM, video_id))  # Cascades to the video's comments.
            else:
                updates.append((PLATFORM, video_id, video_metrics(item.get("statistics") or {})))

        # Backstop: anything still unrefreshed past the hard limit is deleted, never kept.
        max_days = self.settings.youtube_max_age_days
        refreshed = {external_id for _, external_id, _ in updates}
        for kind in ("comment", "video"):
            deletions += [
                (PLATFORM, external_id)
                for external_id in await self._due(kind, max_days, 100_000)
                if external_id not in refreshed
            ]
        # Unchanged text is a no-op rewrite; only keep real edits so scores are not recomputed needlessly.
        text_updates = await self._only_changed(text_updates)
        return PollResult(
            documents=[],
            cursor={"refreshed": len(updates), "deleted": len(deletions), "edited": len(text_updates)},
            fetched=len(comment_ids) + len(video_ids),
            metric_updates=updates,
            deletions=deletions,
            text_updates=text_updates,
        )

    async def _only_changed(self, text_updates: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
        if not text_updates:
            return []
        ids = [external_id for _, external_id, _ in text_updates]
        async with self.pool.connection() as conn:
            rows = await (
                await conn.execute(
                    "SELECT external_id, body FROM documents WHERE platform = %s AND external_id = ANY(%s)",
                    (PLATFORM, ids),
                )
            ).fetchall()
        current = {row["external_id"]: row["body"] for row in rows}
        return [update for update in text_updates if current.get(update[1]) != update[2]]
