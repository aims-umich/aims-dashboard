"""Operational jobs run by hand from the CLI."""

from __future__ import annotations

from collections import Counter

from sentiment.db import NEW_SEGMENTS_CHANNEL, connect
from sentiment.text import classify_relevance


def recompute_relevance(database_url: str, *, dry_run: bool = False) -> dict[str, int]:
    """Re-apply the current relevance rules to every stored segment.

    Run this after changing the rules in `sentiment.text`. Segments that become relevant are queued for
    scoring automatically; segments that become excluded simply stop counting (their scores are kept).
    """
    changes: Counter[str] = Counter()
    with connect(database_url) as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.text, s.relevance, s.relevance_reason, d.lang, d.kind
            FROM segments s JOIN documents d ON d.id = s.document_id
            WHERE d.text_purged_at IS NULL
            """
        ).fetchall()
        updates = []
        for row in rows:
            result = classify_relevance(
                row["text"], lang=row["lang"], context_relevant=row["kind"] == "comment"
            )
            if (result.status, result.reason) != (row["relevance"], row["relevance_reason"]):
                changes[f"{row['relevance']}->{result.status}"] += 1
                updates.append((result.status, result.reason, row["id"]))
        if updates and not dry_run:
            with conn.transaction(), conn.cursor() as cur:
                cur.executemany(
                    "UPDATE segments SET relevance = %s, relevance_reason = %s WHERE id = %s", updates
                )
                cur.execute(f"NOTIFY {NEW_SEGMENTS_CHANNEL}")
    return {"checked": len(rows), "changed": sum(changes.values()), **changes}


DEMO_TEXTS = (
    ("Nuclear power keeps the grid clean and reliable.", 2),
    ("The new reactor design looks promising for cheap clean energy.", 2),
    ("Regulators are reviewing the plant's license renewal this month.", 1),
    ("Utilities discussed nuclear energy costs at the hearing.", 1),
    ("Spent fuel storage at the plant still worries residents.", 0),
    ("The reactor outage raised prices and safety concerns.", 0),
)
DEMO_KINDS = {"youtube": "comment", "guardian": "article", "nyt": "article"}

INSERT_DEMO_DOC = """
    INSERT INTO documents
        (platform, external_id, kind, parent_id, url, title, author_handle, body, lang, published_at, metrics,
         metrics_updated_at)
    VALUES (%s, %s, %s, %s, 'https://example.com/demo', %s, 'demo-author', %s, 'en', %s, %s, now())
    ON CONFLICT (platform, external_id) DO NOTHING RETURNING id
"""
INSERT_DEMO_SEGMENT = """
    INSERT INTO segments (document_id, ordinal, text, relevance) VALUES (%s, 0, %s, 'relevant') RETURNING id
"""
INSERT_DEMO_PREDICTION = """
    INSERT INTO predictions (segment_id, model_id, label, p_neg, p_neu, p_pos, confidence)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
"""
MARK_DEMO_SOURCE = """
    INSERT INTO ingest_state (source, interval_s, last_run_at, last_success_at, consecutive_failures)
    VALUES (%s, 120, now(), now(), 0)
    ON CONFLICT (source) DO UPDATE SET last_success_at = now(), consecutive_failures = 0
"""


def _demo_parent(conn, platform: str, published) -> int | None:
    if platform != "youtube":
        return None
    row = conn.execute(
        """
        INSERT INTO documents (platform, external_id, kind, url, title, published_at)
        VALUES ('youtube', 'demo-video', 'video', 'https://example.com/video', 'Demo: how reactors work', %s)
        ON CONFLICT (platform, external_id) DO UPDATE SET title = EXCLUDED.title RETURNING id
        """,
        (published,),
    ).fetchone()
    return row["id"]


def seed_demo(database_url: str, platforms: list[str], *, days: int = 90, per_day: int = 6) -> dict[str, int]:
    """Fill an empty development or CI database with synthetic, clearly fake data for every platform.

    Uses a separate "demo/fixture" model so real models and their scores are never touched.
    """
    import random
    from datetime import UTC, datetime, timedelta

    from psycopg.types.json import Jsonb

    rng = random.Random(42)
    now = datetime.now(UTC)
    created = 0
    with connect(database_url) as conn, conn.transaction():
        model = conn.execute(
            "INSERT INTO models (name, revision, backend) VALUES ('demo/fixture', 'v1', 'fixture')"
            " ON CONFLICT (name, revision) DO UPDATE SET backend = EXCLUDED.backend RETURNING id"
        ).fetchone()["id"]
        conn.execute("UPDATE models SET is_active = (id = %s)", (model,))
        for platform in platforms:
            kind = DEMO_KINDS.get(platform, "post")
            parent = _demo_parent(conn, platform, now - timedelta(days=days))
            for day in range(days):
                for n in range(rng.randint(1, per_day)):
                    text, label = rng.choice(DEMO_TEXTS)
                    metrics = (
                        {}
                        if kind == "article"
                        else {
                            "likes": rng.randint(0, 40),
                            "reposts": rng.randint(0, 10),
                            "replies": rng.randint(0, 8),
                        }
                    )
                    title = "Demo article about nuclear power" if kind == "article" else None
                    published = now - timedelta(days=day, minutes=rng.randint(0, 1439))
                    # Draw every random value before any early exit, so re-running is a no-op.
                    confidence = rng.uniform(0.55, 0.99)
                    doc = conn.execute(
                        INSERT_DEMO_DOC,
                        (platform, f"demo-{day}-{n}", kind, parent, title, text, published, Jsonb(metrics)),
                    ).fetchone()
                    if doc is None:
                        continue
                    segment = conn.execute(INSERT_DEMO_SEGMENT, (doc["id"], text)).fetchone()["id"]
                    probs = [(1 - confidence) / 2] * 3
                    probs[label] = confidence
                    conn.execute(INSERT_DEMO_PREDICTION, (segment, model, label, *probs, confidence))
                    created += 1
            conn.execute(MARK_DEMO_SOURCE, (platform,))
    return {"documents": created}


async def backfill_nyt(
    settings, start: tuple[int, int], end: tuple[int, int], *, replace_legacy: bool = False
) -> dict[str, int]:
    """Rebuild NYT history from the Archive API (real headlines, abstracts, and links), month by month.

    With `replace_legacy`, the old GPT-written summaries are deleted once every month has loaded.
    The API allows about 5 requests a minute, so months are spaced 12.5 seconds apart.
    """
    import asyncio

    import httpx

    from sentiment.db import async_pool
    from sentiment.ingest.sources.nyt import REQUEST_SPACING_S, archive_month
    from sentiment.ingest.store import save_documents

    if not settings.nyt_api_key:
        raise SystemExit("NYT_API_KEY is not set")
    key = settings.nyt_api_key.get_secret_value()
    months = []
    year, month = start
    while (year, month) <= end:
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)

    totals = {
        "months": 0,
        "articles": 0,
        "kept": 0,
        "new_documents": 0,
        "new_segments": 0,
        "legacy_deleted": 0,
    }
    pool = await async_pool(settings.database_url, max_size=2)
    try:
        async with httpx.AsyncClient(headers={"User-Agent": settings.user_agent}) as client:
            for i, (y, m) in enumerate(months):
                if i:
                    await asyncio.sleep(REQUEST_SPACING_S)
                articles, docs = await archive_month(client, key, y, m)
                async with pool.connection() as conn, conn.transaction():
                    saved = await save_documents(conn, docs)
                    if saved.new_segments:
                        await conn.execute(f"NOTIFY {NEW_SEGMENTS_CHANNEL}")
                totals["months"] += 1
                totals["articles"] += articles
                totals["kept"] += len(docs)
                totals["new_documents"] += saved.new_documents
                totals["new_segments"] += saved.new_segments
                label = f"{y}-{m:02d}"
                print(f"{label}: {articles} articles, {len(docs)} mention nuclear, {saved.new_documents} new")
        if replace_legacy:
            async with pool.connection() as conn, conn.transaction():
                cur = await conn.execute(
                    "DELETE FROM documents WHERE platform = 'nyt' AND external_id LIKE 'legacy-%%'"
                )
                totals["legacy_deleted"] = cur.rowcount
    finally:
        await pool.close()
    return totals
