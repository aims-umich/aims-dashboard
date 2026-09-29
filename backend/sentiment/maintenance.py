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
        (platform, external_id, kind, parent_id, url, title, author_handle, body, lang, published_at, metrics)
    VALUES (%s, %s, %s, %s, 'https://example.com/demo', %s, 'demo-author', %s, 'en', %s, %s)
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
