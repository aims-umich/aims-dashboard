"""Read-side SQL. Every aggregate is computed in Postgres over the active model's predictions."""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg

from sentiment import LABELS
from sentiment.api.platforms import Platform

RANGES: dict[str, tuple[timedelta | None, str]] = {
    "7d": (timedelta(days=7), "day"),
    "30d": (timedelta(days=30), "day"),
    "90d": (timedelta(days=90), "week"),
    "1y": (timedelta(days=365), "month"),
    "all": (None, "month"),
}

# Joins a document to its scored segments under the active model.
SCORED_FROM = """
    FROM documents d
    JOIN segments s ON s.document_id = d.id AND s.relevance = 'relevant'
    JOIN predictions p ON p.segment_id = s.id
         AND p.model_id = (SELECT id FROM models WHERE is_active)
    WHERE d.platform = %(platform)s AND d.kind = ANY(%(kinds)s) AND d.published_at >= %(since)s
"""


def range_bounds(range_key: str, now: datetime | None = None) -> tuple[datetime, str]:
    delta, bucket = RANGES[range_key]
    now = now or datetime.now(UTC)
    since = now - delta if delta else datetime(1970, 1, 1, tzinfo=UTC)
    return since, bucket


def _params(platform: Platform, since: datetime) -> dict[str, Any]:
    return {"platform": platform.key, "kinds": list(platform.scored_kinds), "since": since}


def active_model(conn: psycopg.Connection) -> dict[str, Any] | None:
    return conn.execute("SELECT id, name, revision, backend FROM models WHERE is_active").fetchone()


def summary(conn: psycopg.Connection, platform: Platform, range_key: str) -> dict[str, Any]:
    since, bucket = range_bounds(range_key)
    params = _params(platform, since) | {"bucket": bucket}

    totals = conn.execute(
        f"""
        SELECT count(*) AS scored,
               count(DISTINCT d.id) AS documents,
               count(*) FILTER (WHERE p.label = 0) AS negative,
               count(*) FILTER (WHERE p.label = 1) AS neutral,
               count(*) FILTER (WHERE p.label = 2) AS positive,
               avg(p.confidence) AS avg_confidence,
               min(d.published_at) AS first_published,
               max(d.published_at) AS last_published,
               count(DISTINCT d.id) FILTER (WHERE d.published_at > now() - interval '24 hours') AS last_24h
        {SCORED_FROM}
        """,
        params,
    ).fetchone()

    # Continuous buckets (including empty ones) from the first document in range to now.
    trend = conn.execute(
        f"""
        WITH scored AS (
            SELECT date_trunc(%(bucket)s, d.published_at, 'UTC') AS bucket, d.id AS document_id, p.label
            {SCORED_FROM}
        ),
        buckets AS (
            SELECT generate_series(
                date_trunc(
                    %(bucket)s, GREATEST(%(since)s, COALESCE((SELECT min(bucket) FROM scored), now())), 'UTC'
                ),
                date_trunc(%(bucket)s, now(), 'UTC'),
                ('1 ' || %(bucket)s)::interval
            ) AS bucket
        )
        SELECT b.bucket,
               count(s.label) FILTER (WHERE s.label = 0) AS negative,
               count(s.label) FILTER (WHERE s.label = 1) AS neutral,
               count(s.label) FILTER (WHERE s.label = 2) AS positive,
               count(DISTINCT s.document_id) AS documents
        FROM buckets b LEFT JOIN scored s ON s.bucket = b.bucket
        GROUP BY b.bucket ORDER BY b.bucket
        """,
        params,
    ).fetchall()

    histogram = conn.execute(
        f"""
        SELECT width_bucket(p.confidence, 0.3333, 1.0000001, 7) AS bin, count(*) AS count
        {SCORED_FROM}
        GROUP BY 1 ORDER BY 1
        """,
        params,
    ).fetchall()
    counts = {row["bin"]: row["count"] for row in histogram}
    width = (1.0 - 1 / 3) / 7
    confidence_bins = [
        {
            "from": round(1 / 3 + i * width, 3),
            "to": round(1 / 3 + (i + 1) * width, 3),
            "count": counts.get(i + 1, 0),
        }
        for i in range(7)
    ]

    engagement = _engagement(conn, platform, params) if platform.engagement else None

    scored = totals["scored"] or 0
    return {
        "platform": platform.key,
        "range": range_key,
        "bucket": bucket,
        "totals": {
            "documents": totals["documents"],
            "scored": scored,
            "last_24h": totals["last_24h"],
            "first_published": totals["first_published"],
            "last_published": totals["last_published"],
            "avg_confidence": round(float(totals["avg_confidence"]), 4) if totals["avg_confidence"] else None,
        },
        "sentiment": {label: totals[label] for label in LABELS},
        "net_sentiment": round((totals["positive"] - totals["negative"]) / scored, 4) if scored else None,
        "trend": [
            {
                "bucket": row["bucket"].astimezone(UTC).date().isoformat(),
                "negative": row["negative"],
                "neutral": row["neutral"],
                "positive": row["positive"],
                "documents": row["documents"],
            }
            for row in trend
        ],
        "confidence": confidence_bins,
        "engagement": engagement,
    }


def _engagement(conn: psycopg.Connection, platform: Platform, params: dict[str, Any]) -> dict[str, Any]:
    keys = [key for key, _ in platform.engagement]
    averages_sql = ", ".join(f"avg(NULLIF(d.metrics->>'{key}', '')::numeric) AS {key}" for key in keys)
    # Engagement is per document, so aggregate over documents rather than segments.
    doc_filter = """
        FROM documents d
        WHERE d.platform = %(platform)s AND d.kind = ANY(%(kinds)s) AND d.published_at >= %(since)s
          AND d.metrics <> '{}'::jsonb
    """
    row = conn.execute(f"SELECT count(*) AS documents, {averages_sql} {doc_filter}", params).fetchone()
    trend = conn.execute(
        f"""
        SELECT date_trunc(%(bucket)s, d.published_at, 'UTC') AS bucket, {averages_sql}
        {doc_filter}
        GROUP BY 1 ORDER BY 1
        """,
        params,
    ).fetchall()

    def num(value: Any) -> float | None:
        return round(float(value), 2) if value is not None else None

    return {
        "fields": [{"key": key, "label": label} for key, label in platform.engagement],
        "documents": row["documents"],
        "averages": {key: num(row[key]) for key in keys},
        "trend": [
            {"bucket": r["bucket"].astimezone(UTC).date().isoformat(), **{k: num(r[k]) for k in keys}}
            for r in trend
        ],
    }


_STOPWORDS = frozenset(
    "a about above after again against all also am an and any are aren as at be because been before being "
    "below between both but by can cannot could couldn did didn do does doesn doing don down during each "
    "even ever every few for from further get gets getting go going gone got had hadn has hasn have haven "
    "having he her here hers herself him himself his how however i if in into is isn it its itself just "
    "let like ll me might more most much must my myself no nor not now of off on once one only or other "
    "our ours ourselves out over own re really s said same say says see she should shouldn so some such "
    "t than that the their theirs them themselves then there these they thing things think this those "
    "through to too under until up us ve very via want was wasn way we well were weren what when where "
    "which while who whom why will with won would wouldn yes yet you your yours yourself yourselves "
    "amp http https www com nuclear rt".split()
)
_TOKEN = re.compile(r"[a-z][a-z'\-]{2,}")
_URL = re.compile(r"https?://\S+|www\.\S+")
_MENTION = re.compile(r"@\w[\w.\-]*")


def tokenize(text: str) -> list[str]:
    text = _MENTION.sub(" ", _URL.sub(" ", text.lower().replace("\u2019", "'")))
    tokens = []
    for raw in _TOKEN.findall(text):
        token = raw.strip("'-").removesuffix("'s")
        # Contractions carry no topic, and nuclear* hashtags are what every post was collected by.
        if "'" in token or token.startswith("nuclear") or token in _STOPWORDS or len(token) < 3:
            continue
        tokens.append(token)
    return tokens


def words(conn: psycopg.Connection, platform: Platform, range_key: str, sample: int = 5000) -> dict[str, Any]:
    since, _ = range_bounds(range_key)
    rows = conn.execute(
        f"""
        SELECT s.text, p.label {SCORED_FROM}
        ORDER BY d.published_at DESC LIMIT %(sample)s
        """,
        _params(platform, since) | {"sample": sample},
    ).fetchall()
    by_label: dict[int, Counter[str]] = {0: Counter(), 1: Counter(), 2: Counter()}
    overall: Counter[str] = Counter()
    for row in rows:
        # Count each word once per segment so one repetitive post cannot dominate.
        tokens = set(tokenize(row["text"]))
        by_label[row["label"]].update(tokens)
        overall.update(tokens)
    return {
        "platform": platform.key,
        "range": range_key,
        "sampled": len(rows),
        **{
            LABELS[label]: [{"word": w, "count": c} for w, c in counter.most_common(15)]
            for label, counter in by_label.items()
        },
        "cloud": [{"value": w, "count": c} for w, c in overall.most_common(45)],
    }


def posts(
    conn: psycopg.Connection,
    platform: Platform,
    *,
    limit: int,
    before: tuple[datetime, int] | None,
    sentiment: str | None,
) -> dict[str, Any]:
    """Recent scored documents, newest first, with a document-level sentiment.

    A post has one segment; an article's sentiment is the argmax of its sentences' mean probabilities.
    """
    params: dict[str, Any] = {
        "platform": platform.key,
        "kinds": list(platform.scored_kinds),
        "limit": limit + 1,
        "before_ts": before[0] if before else None,
        "before_id": before[1] if before else None,
        "label": LABELS.index(sentiment) if sentiment else None,
    }
    # Walk documents newest-first on the (platform, published_at) index and aggregate each one's
    # segments lazily, so the cost is proportional to the page size, not the table size.
    rows = conn.execute(
        """
        SELECT d.id, d.kind, d.url, d.title, d.author_handle, d.published_at, d.metrics, d.origin,
               COALESCE(d.body, (SELECT s.text FROM segments s WHERE s.document_id = d.id
                                 AND s.relevance = 'relevant' ORDER BY s.ordinal LIMIT 1)) AS body,
               lbl.label, agg.p_neg, agg.p_neu, agg.p_pos, agg.segments,
               parent.title AS parent_title, parent.url AS parent_url
        FROM documents d
        CROSS JOIN LATERAL (
            SELECT avg(p.p_neg) AS p_neg, avg(p.p_neu) AS p_neu, avg(p.p_pos) AS p_pos, count(*) AS segments
            FROM segments s
            JOIN predictions p ON p.segment_id = s.id AND p.model_id = (SELECT id FROM models WHERE is_active)
            WHERE s.document_id = d.id AND s.relevance = 'relevant'
        ) agg
        CROSS JOIN LATERAL (
            SELECT CASE WHEN agg.p_pos >= agg.p_neu AND agg.p_pos >= agg.p_neg THEN 2
                        WHEN agg.p_neu >= agg.p_neg THEN 1 ELSE 0 END AS label
        ) lbl
        LEFT JOIN documents parent ON parent.id = d.parent_id
        WHERE d.platform = %(platform)s AND d.kind = ANY(%(kinds)s)
          AND (%(before_ts)s::timestamptz IS NULL
               OR (d.published_at, d.id) < (%(before_ts)s::timestamptz, %(before_id)s::bigint))
          AND agg.segments > 0
          AND (%(label)s::smallint IS NULL OR lbl.label = %(label)s::smallint)
        ORDER BY d.published_at DESC, d.id DESC
        LIMIT %(limit)s
        """,
        params,
    ).fetchall()
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = []
    for row in rows:
        probs = (row["p_neg"], row["p_neu"], row["p_pos"])
        items.append(
            {
                "id": row["id"],
                "kind": row["kind"],
                "url": row["url"],
                "title": row["title"],
                "author": row["author_handle"],
                "text": row["body"],
                "published_at": row["published_at"],
                "sentiment": LABELS[row["label"]],
                "confidence": round(float(max(probs)), 4),
                "probabilities": dict(zip(LABELS, (round(float(p), 4) for p in probs), strict=True)),
                "segments": row["segments"],
                "metrics": row["metrics"],
                "origin": row["origin"],
                "parent": {"title": row["parent_title"], "url": row["parent_url"]}
                if row["parent_url"]
                else None,
            }
        )
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = f"{last['published_at'].isoformat()}_{last['id']}"
    return {"platform": platform.key, "items": items, "next_cursor": next_cursor}


def ingest_states(conn: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = conn.execute("SELECT * FROM ingest_state").fetchall()
    return {row["source"]: row for row in rows}


def scorer_status(conn: psycopg.Connection) -> dict[str, Any]:
    model = active_model(conn)
    if model is None:
        backlog = conn.execute("SELECT count(*) AS n FROM segments WHERE relevance = 'relevant'").fetchone()
        return {"model": None, "backlog": backlog["n"], "last_scored_at": None}
    row = conn.execute(
        """
        SELECT
          (SELECT count(*) FROM segments s
            WHERE s.relevance = 'relevant'
              AND NOT EXISTS (SELECT 1 FROM predictions p WHERE p.segment_id = s.id AND p.model_id = %(m)s))
            AS backlog,
          (SELECT max(scored_at) FROM predictions WHERE model_id = %(m)s) AS last_scored_at
        """,
        {"m": model["id"]},
    ).fetchone()
    return {
        "model": {"name": model["name"], "revision": model["revision"], "backend": model["backend"]},
        "backlog": row["backlog"],
        "last_scored_at": row["last_scored_at"],
    }
