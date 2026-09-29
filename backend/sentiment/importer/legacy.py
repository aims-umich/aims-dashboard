"""One-time import of the pre-2026 dashboard data into Postgres, tagged `origin = 'backfill'`.

Everything is re-segmented and re-filtered with the live rules, then re-scored by the scorer,
so historical and live data points are scored the same way by the same model.
Human labels from the original training/test CSVs are kept in `documents.raw.true_label`.

The scraped Threads data (backend/threads/*, backend/posts.db) is deliberately NOT importable:
it was collected against Meta's terms and must not be published.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import logging
import sqlite3
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sentiment.db import async_pool
from sentiment.ingest.base import DocumentIn, SegmentIn
from sentiment.ingest.store import save_documents
from sentiment.text import classify_relevance, normalize, nuclear_sentences, strip_html

log = logging.getLogger(__name__)

LABEL_NAMES = {"negative": 0, "neutral": 1, "positive": 2}


def _dt(value: str) -> datetime:
    value = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value.replace(" ", "T", 1) if "T" not in value else value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _true_label(value: Any) -> int | None:
    if value is None or str(value).strip() in ("", "nan"):
        return None
    text = str(value).strip().lower()
    if text in LABEL_NAMES:
        return LABEL_NAMES[text]
    try:
        number = int(float(text))
    except ValueError:
        return None
    return number if number in (0, 1, 2) else None


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


# ---------------------------------------------------------------------------


def guardian_documents(db_path: Path) -> Iterator[DocumentIn]:
    """Articles from the old guardian.db, segmented from their stored body text."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        for row in conn.execute(
            "SELECT title, author, section, publish_date, url, word_count, body_text FROM articles"
        ):
            url = row["url"]
            if not url or url == "N/A" or not row["publish_date"] or row["publish_date"] == "N/A":
                continue
            sentences = nuclear_sentences(row["body_text"] or "")
            yield DocumentIn(
                platform="guardian",
                # The Content API id is the URL path, so live polling de-duplicates against these.
                external_id=urlparse(url).path.lstrip("/"),
                kind="article",
                published_at=_dt(row["publish_date"]),
                url=url,
                author_handle=None if row["author"] in (None, "N/A") else row["author"],
                title=row["title"],
                lang="en",
                segments=[SegmentIn(s, classify_relevance(s, lang="en")) for s in sentences],
                metrics={"word_count": _int(row["word_count"])} if _int(row["word_count"]) else {},
                raw={"section": row["section"]},
                origin="backfill",
            )
    finally:
        conn.close()


def mastodon_documents(csv_paths: Iterable[Path]) -> Iterator[DocumentIn]:
    for path in csv_paths:
        for row in _rows(path):
            text = strip_html(row.get("content") or "")
            uri = row.get("uri") or row.get("url")
            if not text or not uri or not row.get("created_at"):
                continue
            try:
                account = ast.literal_eval(row.get("account") or "{}")
            except (ValueError, SyntaxError):
                account = {}
            lang = row.get("language") if row.get("language") not in ("", "nan") else None
            yield DocumentIn(
                platform="mastodon",
                external_id=uri,
                kind="post",
                published_at=_dt(row["created_at"]),
                url=row.get("url") or uri,
                author_handle=account.get("acct") if isinstance(account, dict) else None,
                body=text,
                lang=lang,
                segments=[SegmentIn(text, classify_relevance(text, lang=lang))],
                metrics={
                    "replies": _int(row.get("replies_count")),
                    "reposts": _int(row.get("reblogs_count")),
                    "likes": _int(row.get("favourites_count")),
                    "sensitive": row.get("sensitive") == "True",
                    "has_media": (row.get("media_attachments") or "[]") != "[]",
                },
                raw={"true_label": _true_label(row.get("label")), "legacy_file": path.name},
                origin="backfill",
            )


def youtube_documents(csv_path: Path) -> Iterator[DocumentIn]:
    """Videos first (as parents), then their comments dated by the comment's own timestamp."""
    rows = list(_rows(csv_path))
    videos: dict[str, dict[str, str]] = {}
    for row in rows:
        videos.setdefault(row["video_id"], row)
    for video_id, row in videos.items():
        yield DocumentIn(
            platform="youtube",
            external_id=video_id,
            kind="video",
            published_at=_dt(row["published_at"]),
            url=f"https://www.youtube.com/watch?v={video_id}",
            author_handle=row.get("channel_title") or None,
            title=normalize(row.get("title") or "") or None,
            metrics={
                "views": _int(row.get("view_count")),
                "likes": _int(row.get("like_count")),
                "comments": _int(row.get("comment_count")),
            },
            origin="backfill",
        )
    for row in rows:
        text = normalize(row.get("comment_text") or "")
        if not text:
            continue
        stamp = row.get("comment_published_at") or row["published_at"]
        # The CSV has no comment ids, so derive a stable one from the content.
        digest = hashlib.sha256(f"{row['video_id']}|{stamp}|{text}".encode()).hexdigest()[:24]
        yield DocumentIn(
            platform="youtube",
            external_id=f"legacy-{digest}",
            kind="comment",
            parent_external_id=row["video_id"],
            published_at=_dt(stamp),
            url=f"https://www.youtube.com/watch?v={row['video_id']}",
            author_handle=row.get("comment_author") or None,
            body=text,
            segments=[SegmentIn(text, classify_relevance(text, context_relevant=True))],
            metrics={"likes": _int(row.get("comment_like_count"))},
            raw={"true_label": _true_label(row.get("Sentiment"))},
            origin="backfill",
        )


def nyt_documents(db_path: Path) -> Iterator[DocumentIn]:
    """The old NYT store only kept GPT-written summaries (no URL or headline); kept as-is and flagged."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        for row in conn.execute("SELECT id, date, content FROM records"):
            text = normalize(row["content"] or "").removeprefix("Summary:").strip()
            if not text or not row["date"]:
                continue
            yield DocumentIn(
                platform="nyt",
                external_id=f"legacy-{row['id']}",
                kind="article",
                published_at=_dt(row["date"]),
                body=text,
                lang="en",
                segments=[SegmentIn(text, classify_relevance(text, lang="en"))],
                raw={"text_source": "gpt-summary"},
                origin="backfill",
            )
    finally:
        conn.close()


# ---------------------------------------------------------------------------


async def import_documents(
    database_url: str, documents: Iterable[DocumentIn], batch_size: int = 500
) -> dict[str, int]:
    pool = await async_pool(database_url, max_size=2)
    totals = {"seen": 0, "new_documents": 0, "new_segments": 0}
    try:
        batch: list[DocumentIn] = []

        async def flush() -> None:
            async with pool.connection() as conn, conn.transaction():
                saved = await save_documents(conn, batch)
                if saved.new_segments:
                    await conn.execute("NOTIFY new_segments")
            totals["new_documents"] += saved.new_documents
            totals["new_segments"] += saved.new_segments
            batch.clear()

        for doc in documents:
            totals["seen"] += 1
            batch.append(doc)
            if len(batch) >= batch_size:
                await flush()
        if batch:
            await flush()
    finally:
        await pool.close()
    return totals


def default_paths(backend_dir: Path) -> dict[str, Any]:
    return {
        "guardian": backend_dir / "guardian" / "database" / "guardian.db",
        "mastodon": [
            backend_dir / "mastodon" / "training_mastodon.csv",
            backend_dir / "mastodon" / "testing_mastodon.csv",
        ],
        "youtube": backend_dir / "youtube" / "Youtube_Label.csv",
        "nyt": backend_dir / "newyorktimes" / "var" / "dashdb.sqlite3",
    }


def documents_for(source: str, paths: dict[str, Any]) -> Iterator[DocumentIn]:
    if source == "guardian":
        return guardian_documents(paths["guardian"])
    if source == "mastodon":
        return mastodon_documents(paths["mastodon"])
    if source == "youtube":
        return youtube_documents(paths["youtube"])
    if source == "nyt":
        return nyt_documents(paths["nyt"])
    raise ValueError(f"No legacy importer for {source!r} (Threads data is intentionally excluded)")
