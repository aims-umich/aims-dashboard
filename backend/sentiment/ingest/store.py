"""Idempotent writes for collectors.

Documents are upserted on (platform, external_id), so retries and overlapping polls never duplicate.
Segments are only written for newly inserted documents.
A job's documents and its new cursor commit in one transaction, so a crash never skips data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from sentiment.db import NEW_SEGMENTS_CHANNEL
from sentiment.ingest.base import DocumentIn, PollResult
from sentiment.text import RELEVANT, classify_relevance

UPSERT_DOCUMENT_SQL = """
    INSERT INTO documents (platform, external_id, kind, parent_id, url, author_handle, title, body,
                           lang, published_at, metrics, metrics_updated_at, origin, raw)
    VALUES (%(platform)s, %(external_id)s, %(kind)s, %(parent_id)s, %(url)s, %(author_handle)s, %(title)s,
            %(body)s, %(lang)s, %(published_at)s, %(metrics)s,
            CASE WHEN %(has_metrics)s THEN now() END, %(origin)s, %(raw)s)
    ON CONFLICT (platform, external_id) DO UPDATE SET
        metrics = CASE WHEN %(has_metrics)s THEN EXCLUDED.metrics ELSE documents.metrics END,
        metrics_updated_at = CASE WHEN %(has_metrics)s THEN now() ELSE documents.metrics_updated_at END,
        -- A purged document stays purged even when a later poll returns it again.
        url = CASE WHEN documents.text_purged_at IS NULL THEN COALESCE(EXCLUDED.url, documents.url) END,
        author_handle = CASE WHEN documents.text_purged_at IS NULL
                             THEN COALESCE(EXCLUDED.author_handle, documents.author_handle) END,
        title = CASE WHEN documents.text_purged_at IS NULL THEN COALESCE(EXCLUDED.title, documents.title) END
    RETURNING id, (xmax = 0) AS inserted
"""

INSERT_SEGMENT_SQL = """
    INSERT INTO segments (document_id, ordinal, text, relevance, relevance_reason)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (document_id, ordinal) DO NOTHING
"""


@dataclass(slots=True)
class SaveResult:
    new_documents: int = 0
    new_segments: int = 0
    updated_metrics: int = 0
    deleted: int = 0


async def save_documents(conn: AsyncConnection, documents: list[DocumentIn]) -> SaveResult:
    """Upsert documents and their segments inside the caller's transaction."""
    result = SaveResult()
    parents: dict[tuple[str, str], int] = {}
    for doc in documents:
        parent_id = None
        if doc.parent_external_id:
            key = (doc.platform, doc.parent_external_id)
            if key not in parents:
                row = await (
                    await conn.execute(
                        "SELECT id FROM documents WHERE platform = %s AND external_id = %s", key
                    )
                ).fetchone()
                if row is None:
                    continue  # The parent was deleted or never stored; skip the orphan.
                parents[key] = row["id"]
            parent_id = parents[key]
        row = await (
            await conn.execute(
                UPSERT_DOCUMENT_SQL,
                {
                    "platform": doc.platform,
                    "external_id": doc.external_id,
                    "kind": doc.kind,
                    "parent_id": parent_id,
                    "url": doc.url,
                    "author_handle": doc.author_handle,
                    "title": doc.title,
                    "body": doc.body,
                    "lang": doc.lang,
                    "published_at": doc.published_at,
                    "metrics": Jsonb(doc.metrics),
                    "has_metrics": bool(doc.metrics),
                    "origin": doc.origin,
                    "raw": Jsonb(doc.raw) if doc.raw is not None else None,
                },
            )
        ).fetchone()
        if not row["inserted"]:
            if doc.metrics:
                result.updated_metrics += 1
            continue
        result.new_documents += 1
        if doc.segments:
            async with conn.cursor() as cur:
                await cur.executemany(
                    INSERT_SEGMENT_SQL,
                    [
                        (row["id"], i, seg.text, seg.relevance.status, seg.relevance.reason)
                        for i, seg in enumerate(doc.segments)
                    ],
                )
            result.new_segments += sum(seg.relevance.status == RELEVANT for seg in doc.segments)
    return result


async def update_metrics(conn: AsyncConnection, updates: list[tuple[str, str, dict[str, Any]]]) -> int:
    """Merge refreshed engagement counts (and optional fields) into existing documents."""
    count = 0
    for platform, external_id, fields in updates:
        metrics = {k: v for k, v in fields.items() if not k.startswith("_")}
        handle = fields.get("_author_handle")
        cur = await conn.execute(
            """
            UPDATE documents
            SET metrics = metrics || %s, metrics_updated_at = now(),
                author_handle = COALESCE(%s, author_handle)
            WHERE platform = %s AND external_id = %s
            """,
            (Jsonb(metrics), handle, platform, external_id),
        )
        count += cur.rowcount
    return count


async def update_texts(conn: AsyncConnection, updates: list[tuple[str, str, str]]) -> int:
    """Replace edited text on single-segment documents and drop their scores so they are scored again."""
    count = 0
    for platform, external_id, text in updates:
        row = await (
            await conn.execute(
                "UPDATE documents SET body = %s WHERE platform = %s AND external_id = %s RETURNING id, kind",
                (text, platform, external_id),
            )
        ).fetchone()
        if row is None:
            continue
        relevance = classify_relevance(text, context_relevant=row["kind"] == "comment")
        segment = await (
            await conn.execute(
                "UPDATE segments SET text = %s, relevance = %s, relevance_reason = %s"
                " WHERE document_id = %s AND ordinal = 0 RETURNING id",
                (text, relevance.status, relevance.reason, row["id"]),
            )
        ).fetchone()
        if segment:
            await conn.execute("DELETE FROM predictions WHERE segment_id = %s", (segment["id"],))
        count += 1
    return count


async def delete_documents(conn: AsyncConnection, keys: list[tuple[str, str]]) -> int:
    """Honor deletions at the source (platform terms require it). Cascades to segments and scores."""
    by_platform: dict[str, list[str]] = {}
    for platform, external_id in keys:
        by_platform.setdefault(platform, []).append(external_id)
    count = 0
    for platform, ids in by_platform.items():
        cur = await conn.execute(
            "DELETE FROM documents WHERE platform = %s AND external_id = ANY(%s)", (platform, ids)
        )
        count += cur.rowcount
    return count


async def commit_run(
    conn: AsyncConnection, job_name: str, result: PollResult, interval_s: float
) -> SaveResult:
    """Save a poll's output and advance the job's cursor atomically."""
    async with conn.transaction():
        saved = await save_documents(conn, result.documents)
        if result.metric_updates:
            saved.updated_metrics += await update_metrics(conn, result.metric_updates)
        if result.deletions:
            saved.deleted = await delete_documents(conn, result.deletions)
        edited = await update_texts(conn, result.text_updates) if result.text_updates else 0
        await conn.execute(
            """
            INSERT INTO ingest_state (source, cursor, interval_s, last_run_at, last_success_at,
                                      consecutive_failures, items_last_run, new_last_run, updated_at)
            VALUES (%s, %s, %s, now(), now(), 0, %s, %s, now())
            ON CONFLICT (source) DO UPDATE SET
                cursor = EXCLUDED.cursor, interval_s = EXCLUDED.interval_s,
                last_run_at = now(), last_success_at = now(), consecutive_failures = 0,
                items_last_run = EXCLUDED.items_last_run, new_last_run = EXCLUDED.new_last_run,
                updated_at = now()
            """,
            (job_name, Jsonb(result.cursor), int(interval_s), result.fetched, saved.new_documents),
        )
        if saved.new_segments or edited:
            await conn.execute(f"NOTIFY {NEW_SEGMENTS_CHANNEL}")
    return saved


async def record_failure(conn: AsyncConnection, job_name: str, message: str, interval_s: float) -> int:
    async with conn.transaction():
        row = await (
            await conn.execute(
                """
                INSERT INTO ingest_state (source, interval_s, last_run_at, last_error, last_error_at,
                                          consecutive_failures, updated_at)
                VALUES (%s, %s, now(), %s, now(), 1, now())
                ON CONFLICT (source) DO UPDATE SET
                    interval_s = EXCLUDED.interval_s, last_run_at = now(), last_error = EXCLUDED.last_error,
                    last_error_at = now(), consecutive_failures = ingest_state.consecutive_failures + 1,
                    updated_at = now()
                RETURNING consecutive_failures
                """,
                (job_name, int(interval_s), message),
            )
        ).fetchone()
    return int(row["consecutive_failures"])


async def load_cursor(conn: AsyncConnection, job_name: str) -> dict[str, Any]:
    row = await (
        await conn.execute("SELECT cursor FROM ingest_state WHERE source = %s", (job_name,))
    ).fetchone()
    return dict(row["cursor"]) if row else {}
