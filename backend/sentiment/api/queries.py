"""Read-side SQL. Every aggregate is computed in Postgres over the active model's predictions."""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg

from sentiment import LABELS
from sentiment.api.platforms import Platform

RANGES: dict[str, tuple[timedelta | None, str]] = {
    "24h": (timedelta(hours=24), "hour"),
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
      AND (NOT %(us_only)s OR d.raw->>'us' = 'true')
"""


# Confidence histogram bands. A top probability is never below 1/3; 0.7 is the close-call line.
CONFIDENCE_EDGES = (1 / 3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)

# The activity grid always covers the last four weeks, whatever range the page shows.
ACTIVITY_WINDOW = timedelta(days=28)


def bucket_key(value: datetime, bucket: str) -> str:
    """Bucket start as a UTC string: a date for day and longer buckets, a full timestamp for hours."""
    value = value.astimezone(UTC)
    return value.strftime("%Y-%m-%dT%H:00:00Z") if bucket == "hour" else value.date().isoformat()


def range_bounds(range_key: str, now: datetime | None = None) -> tuple[datetime, str]:
    delta, bucket = RANGES[range_key]
    now = now or datetime.now(UTC)
    since = now - delta if delta else datetime(1970, 1, 1, tzinfo=UTC)
    return since, bucket


def _params(platform: Platform, since: datetime, us_only: bool = False) -> dict[str, Any]:
    return {
        "platform": platform.key,
        "kinds": list(platform.scored_kinds),
        "since": since,
        "us_only": us_only,
    }


def active_model(conn: psycopg.Connection) -> dict[str, Any] | None:
    return conn.execute("SELECT id, name, revision, backend FROM models WHERE is_active").fetchone()


def summary(
    conn: psycopg.Connection, platform: Platform, range_key: str, us_only: bool = False
) -> dict[str, Any]:
    since, bucket = range_bounds(range_key)
    # Bounded ranges show every bucket in the range; "all" starts at the first data point.
    params = _params(platform, since, us_only) | {
        "bucket": bucket,
        "full_range": RANGES[range_key][0] is not None,
    }

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
                    %(bucket)s,
                    CASE WHEN %(full_range)s THEN %(since)s
                         ELSE COALESCE((SELECT min(bucket) FROM scored), now()) END,
                    'UTC'
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
        SELECT width_bucket(p.confidence, %(edges)s::real[]) AS bin, count(*) AS count
        {SCORED_FROM}
        GROUP BY 1 ORDER BY 1
        """,
        params | {"edges": list(CONFIDENCE_EDGES[1:-1])},
    ).fetchall()
    counts = {row["bin"]: row["count"] for row in histogram}
    confidence_bins = [
        {"from": CONFIDENCE_EDGES[i], "to": CONFIDENCE_EDGES[i + 1], "count": counts.get(i, 0)}
        for i in range(len(CONFIDENCE_EDGES) - 1)
    ]

    engagement = _engagement(conn, platform, params) if platform.engagement else None
    activity = _activity(conn, platform, us_only)

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
            "collecting_since": collecting_since(conn, platform),
            "last_published": totals["last_published"],
            "avg_confidence": round(float(totals["avg_confidence"]), 4) if totals["avg_confidence"] else None,
        },
        "sentiment": {label: totals[label] for label in LABELS},
        "net_sentiment": round((totals["positive"] - totals["negative"]) / scored, 4) if scored else None,
        "trend": [
            {
                "bucket": bucket_key(row["bucket"], bucket),
                "negative": row["negative"],
                "neutral": row["neutral"],
                "positive": row["positive"],
                "documents": row["documents"],
            }
            for row in trend
        ],
        "confidence": confidence_bins,
        "engagement": engagement,
        "activity": activity,
    }


def collecting_since(conn: psycopg.Connection, platform: Platform) -> datetime | None:
    """The source's first document ever, so pages can mark time before collection began."""
    return conn.execute(
        "SELECT min(published_at) AS first FROM documents"
        " WHERE platform = %(platform)s AND kind = ANY(%(kinds)s)",
        {"platform": platform.key, "kinds": list(platform.scored_kinds)},
    ).fetchone()["first"]


def scored_count(conn: psycopg.Connection, platform: Platform) -> int:
    since, _ = range_bounds("all")
    row = conn.execute(f"SELECT count(*) AS n {SCORED_FROM}", _params(platform, since)).fetchone()
    return row["n"]


def _engagement(conn: psycopg.Connection, platform: Platform, params: dict[str, Any]) -> dict[str, Any]:
    keys = [key for key, _ in platform.engagement]
    averages_sql = ", ".join(f"avg(NULLIF(d.metrics->>'{key}', '')::numeric) AS {key}" for key in keys)
    # Engagement is per document, so aggregate over documents rather than segments.
    doc_filter = """
        FROM documents d
        WHERE d.platform = %(platform)s AND d.kind = ANY(%(kinds)s) AND d.published_at >= %(since)s
          AND d.metrics <> '{}'::jsonb AND (NOT %(us_only)s OR d.raw->>'us' = 'true')
    """
    row = conn.execute(f"SELECT count(*) AS documents, {averages_sql} {doc_filter}", params).fetchone()
    # Engagement by the document's sentiment. Only single-segment kinds carry engagement, so the
    # segment's label is the document's label.
    stats_sql = ", ".join(
        f"avg(NULLIF(d.metrics->>'{key}', '')::numeric) AS {key}_mean,"
        f" stddev_samp(NULLIF(d.metrics->>'{key}', '')::numeric) AS {key}_sd"
        for key in keys
    )
    by_label = conn.execute(
        f"SELECT p.label, count(*) AS n, {stats_sql} {SCORED_FROM} AND d.metrics <> '{{}}'::jsonb GROUP BY 1",
        params,
    ).fetchall()
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
        "by_sentiment": {
            LABELS[r["label"]]: {
                "n": r["n"],
                **{key: {"mean": num(r[f"{key}_mean"]), "sd": num(r[f"{key}_sd"])} for key in keys},
            }
            for r in by_label
        },
        "trend": [
            {"bucket": r["bucket"].astimezone(UTC).date().isoformat(), **{k: num(r[k]) for k in keys}}
            for r in trend
        ],
    }


def _activity(conn: psycopg.Connection, platform: Platform, us_only: bool) -> dict[str, Any]:
    """Scored texts by UTC weekday and hour over the last four weeks.

    `slots` counts how many times each weekday-hour occurred while the source was collecting, so the page
    can tell "quiet" apart from "not collecting yet".
    """
    now = datetime.now(UTC)
    since = now - ACTIVITY_WINDOW
    params = _params(platform, since, us_only)
    rows = conn.execute(
        f"""
        SELECT extract(isodow FROM d.published_at AT TIME ZONE 'UTC')::int - 1 AS dow,
               extract(hour FROM d.published_at AT TIME ZONE 'UTC')::int AS hour,
               count(*) AS n
        {SCORED_FROM}
        GROUP BY 1, 2
        """,
        params,
    ).fetchall()
    first = collecting_since(conn, platform)
    counts = [[0] * 24 for _ in range(7)]
    for row in rows:
        counts[row["dow"]][row["hour"]] = row["n"]
    slots = [[0] * 24 for _ in range(7)]
    if first is not None:
        hour = max(first, since).replace(minute=0, second=0, microsecond=0)
        while hour <= now:
            slots[hour.weekday()][hour.hour] += 1
            hour += timedelta(hours=1)
    return {"window_days": ACTIVITY_WINDOW.days, "counts": counts, "slots": slots}


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


def words(
    conn: psycopg.Connection, platform: Platform, range_key: str, sample: int = 5000, us_only: bool = False
) -> dict[str, Any]:
    since, _ = range_bounds(range_key)
    rows = conn.execute(
        f"""
        SELECT s.text, p.label {SCORED_FROM} AND s.text <> ''
        ORDER BY d.published_at DESC LIMIT %(sample)s
        """,
        _params(platform, since, us_only) | {"sample": sample},
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
        "cloud": [
            {"value": w, "count": c, "positive": by_label[2][w], "negative": by_label[0][w]}
            for w, c in overall.most_common(45)
        ],
        "distinctive": distinctive_words(by_label[2], by_label[0], overall),
    }


def distinctive_words(
    positive: Counter[str], negative: Counter[str], prior: Counter[str], *, top: int = 8, min_count: int = 3
) -> dict[str, list[dict[str, Any]]]:
    """Words most characteristic of positive versus negative texts.

    Log-odds ratio with an informative Dirichlet prior (Monroe, Colaresi and Quinn 2008), which keeps
    rare words from topping the list by chance. Returns the strongest words on each side with their z-score.
    """
    n_pos, n_neg = sum(positive.values()), sum(negative.values())
    a0 = sum(prior.values())
    if not n_pos or not n_neg or not a0:
        return {"positive": [], "negative": []}
    scored = []
    for word, a in prior.items():
        yp, yn = positive[word], negative[word]
        if yp + yn < min_count:
            continue
        delta = math.log((yp + a) / (n_pos + a0 - yp - a)) - math.log((yn + a) / (n_neg + a0 - yn - a))
        z = delta / math.sqrt(1 / (yp + a) + 1 / (yn + a))
        scored.append({"word": word, "positive": yp, "negative": yn, "z": round(z, 2)})
    scored.sort(key=lambda item: item["z"])
    return {
        "positive": [w for w in reversed(scored[-top:]) if w["z"] > 0],
        "negative": [w for w in scored[:top] if w["z"] < 0],
    }


def posts(
    conn: psycopg.Connection,
    platform: Platform,
    *,
    limit: int,
    before: tuple[datetime, int] | None,
    sentiment: str | None,
    us_only: bool = False,
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
        "us_only": us_only,
    }
    # Walk documents newest-first on the (platform, published_at) index and aggregate each one's
    # segments lazily, so the cost is proportional to the page size, not the table size.
    rows = conn.execute(
        """
        SELECT d.id, d.kind, d.url, d.title, d.author_handle, d.published_at, d.metrics, d.origin,
               COALESCE(d.body, (SELECT s.text FROM segments s WHERE s.document_id = d.id
                                 AND s.relevance = 'relevant' ORDER BY s.ordinal LIMIT 1)) AS body,
               lbl.label, agg.p_neg, agg.p_neu, agg.p_pos, agg.segments,
               parent.title AS parent_title, parent.url AS parent_url,
               (SELECT e.spans FROM segments s
                JOIN explanations e ON e.segment_id = s.id
                     AND e.model_id = (SELECT id FROM models WHERE is_active)
                WHERE s.document_id = d.id AND s.relevance = 'relevant' AND s.text = COALESCE(d.body, s.text)
                ORDER BY s.ordinal LIMIT 1) AS highlights
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
        WHERE d.platform = %(platform)s AND d.kind = ANY(%(kinds)s) AND d.text_purged_at IS NULL
          AND (NOT %(us_only)s OR d.raw->>'us' = 'true')
          -- Bluesky posts are listed only once the metrics job has checked the author's opt-outs.
          AND (d.platform <> 'bluesky' OR d.metrics_updated_at IS NOT NULL)
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
                # Words that pushed the label, as [start, end, score] offsets into `text` (posts only).
                "highlights": row["highlights"] if row["segments"] == 1 else None,
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


def strip(
    conn: psycopg.Connection, platforms: list[Platform], hours: int = 24, cap: int = 4000
) -> dict[str, Any]:
    """Every scored text of the last `hours`, as compact [epoch seconds, label, confidence %] rows.

    `collecting_since` is each source's first document ever, so the page can mark time before it.
    """
    now = datetime.now(UTC)
    since = now - timedelta(hours=hours)
    items = []
    for platform in platforms:
        params = _params(platform, since) | {"cap": cap}
        rows = conn.execute(
            f"""
            SELECT extract(epoch FROM d.published_at)::bigint AS t, p.label,
                   round(p.confidence * 100)::int AS confidence
            {SCORED_FROM}
            ORDER BY d.published_at DESC LIMIT %(cap)s
            """,
            params,
        ).fetchall()
        first = collecting_since(conn, platform)
        items.append(
            {
                "platform": platform.key,
                "collecting_since": first,
                "count": len(rows),
                "items": [[r["t"], r["label"], r["confidence"]] for r in reversed(rows)],
            }
        )
    return {"since": since, "until": now, "hours": hours, "platforms": items}


def ingest_states(conn: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = conn.execute("SELECT * FROM ingest_state").fetchall()
    return {row["source"]: row for row in rows}


def scorer_status(conn: psycopg.Connection) -> dict[str, Any]:
    model = active_model(conn)
    if model is None:
        backlog = conn.execute(
            "SELECT count(*) AS n FROM segments WHERE relevance = 'relevant' AND text <> ''"
        ).fetchone()
        return {"model": None, "backlog": backlog["n"], "last_scored_at": None}
    row = conn.execute(
        """
        SELECT
          (SELECT count(*) FROM segments s
            WHERE s.relevance = 'relevant' AND s.text <> ''
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


# ---------------------------------------------------------------------------
# Topics

# Scored segments across several platforms at once (each platform only through its scored kinds).
_SCORED_ANY_JOINS = """
    FROM documents d
    JOIN segments s ON s.document_id = d.id AND s.relevance = 'relevant'
    JOIN predictions p ON p.segment_id = s.id
         AND p.model_id = (SELECT id FROM models WHERE is_active)
"""
_SCORED_ANY_WHERE = """
    WHERE (d.platform || ':' || d.kind) = ANY(%(scored)s)
      AND d.published_at >= %(since)s AND d.published_at < %(until)s
"""
SCORED_ANY_FROM = _SCORED_ANY_JOINS + _SCORED_ANY_WHERE
# One row per (segment, topic tag); `t` is the topic id.
TOPIC_TAGS_FROM = _SCORED_ANY_JOINS + "    CROSS JOIN LATERAL unnest(s.topics) AS t\n" + _SCORED_ANY_WHERE
TOPIC_WEEKS = 12


def _scored_keys(platforms: list[Platform]) -> list[str]:
    return [f"{p.key}:{kind}" for p in platforms for kind in p.scored_kinds]


def _net(pos: int, neg: int, total: int) -> float | None:
    return round((pos - neg) / total, 4) if total else None


def topics(conn: psycopg.Connection, platforms: list[Platform], range_key: str) -> dict[str, Any]:
    """Volume and sentiment for every topic, with the previous period, 12 weekly counts, and each platform."""
    from sentiment.topics import TOPICS

    now = datetime.now(UTC)
    since, _ = range_bounds(range_key, now)
    delta = RANGES[range_key][0]
    params = {"scored": _scored_keys(platforms), "since": since, "until": now}
    per_label = """
        count(*) AS n,
        count(*) FILTER (WHERE p.label = 0) AS negative,
        count(*) FILTER (WHERE p.label = 1) AS neutral,
        count(*) FILTER (WHERE p.label = 2) AS positive
    """
    texts = conn.execute(f"SELECT count(*) AS n {SCORED_ANY_FROM}", params).fetchone()["n"]
    current = {
        r["topic"]: r
        for r in conn.execute(
            f"SELECT t AS topic, {per_label} {TOPIC_TAGS_FROM} GROUP BY 1",
            params,
        )
    }
    previous: dict[str, int] = {}
    if delta is not None:
        prev_params = params | {"since": since - delta, "until": since}
        previous = {
            r["topic"]: r["n"]
            for r in conn.execute(
                f"SELECT t AS topic, count(*) AS n {TOPIC_TAGS_FROM} GROUP BY 1",
                prev_params,
            )
        }
    by_platform: dict[str, dict[str, Any]] = {}
    for r in conn.execute(
        f"SELECT t AS topic, d.platform, {per_label} {TOPIC_TAGS_FROM} GROUP BY 1, 2",
        params,
    ):
        by_platform.setdefault(r["topic"], {})[r["platform"]] = {
            "n": r["n"],
            "net": _net(r["positive"], r["negative"], r["n"]),
        }
    week_start = date_trunc_week(now) - timedelta(weeks=TOPIC_WEEKS - 1)
    weekly: dict[str, dict[datetime, int]] = {}
    for r in conn.execute(
        f"SELECT t AS topic, date_trunc('week', d.published_at, 'UTC') AS week, count(*) AS n"
        f" {TOPIC_TAGS_FROM} GROUP BY 1, 2",
        params | {"since": week_start},
    ):
        weekly.setdefault(r["topic"], {})[r["week"]] = r["n"]
    weeks = [week_start + timedelta(weeks=i) for i in range(TOPIC_WEEKS)]
    items = []
    for topic in TOPICS:
        row = current.get(topic.id)
        n = row["n"] if row else 0
        items.append(
            {
                "id": topic.id,
                "name": topic.name,
                "keywords": list(topic.keywords),
                "count": n,
                "share": round(n / texts, 4) if texts else None,
                "sentiment": {label: (row[label] if row else 0) for label in LABELS},
                "net_sentiment": _net(row["positive"], row["negative"], n) if row else None,
                "previous_count": previous.get(topic.id) if delta is not None else None,
                "weekly": [weekly.get(topic.id, {}).get(w, 0) for w in weeks],
                "by_platform": by_platform.get(topic.id, {}),
            }
        )
    return {
        "range": range_key,
        "texts": texts,
        "weeks": [w.date().isoformat() for w in weeks],
        "platforms": [p.key for p in platforms],
        "topics": items,
    }


def date_trunc_week(value: datetime) -> datetime:
    """Start of the ISO week (Monday 00:00 UTC), matching Postgres date_trunc('week')."""
    value = value.astimezone(UTC)
    return (value - timedelta(days=value.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


# Example posts are only drawn from kinds that are shown as individual texts elsewhere on the site.
EXAMPLE_KINDS = ("post", "comment")


def topic_detail(
    conn: psycopg.Connection, platforms: list[Platform], topic_id: str, range_key: str
) -> dict[str, Any]:
    """One topic: weekly volume and net sentiment, the words that travel with it, and two example texts."""
    now = datetime.now(UTC)
    since, _ = range_bounds(range_key, now)
    week_start = date_trunc_week(now) - timedelta(weeks=TOPIC_WEEKS - 1)
    params = {"scored": _scored_keys(platforms), "since": week_start, "until": now, "topic": topic_id}
    by_week = {
        r["week"]: r
        for r in conn.execute(
            f"""
            SELECT date_trunc('week', d.published_at, 'UTC') AS week, count(*) AS n,
                   count(*) FILTER (WHERE p.label = 0) AS negative,
                   count(*) FILTER (WHERE p.label = 2) AS positive
            {SCORED_ANY_FROM} AND %(topic)s = ANY(s.topics)
            GROUP BY 1
            """,
            params,
        )
    }
    weeks = []
    for i in range(TOPIC_WEEKS):
        week = week_start + timedelta(weeks=i)
        row = by_week.get(week)
        n = row["n"] if row else 0
        weeks.append(
            {
                "week": week.date().isoformat(),
                "count": n,
                "net_sentiment": _net(row["positive"], row["negative"], n) if row else None,
            }
        )
    sample = conn.execute(
        f"""
        SELECT s.text, %(topic)s = ANY(s.topics) AS in_topic {SCORED_ANY_FROM}
        ORDER BY d.published_at DESC LIMIT 6000
        """,
        params | {"since": since},
    ).fetchall()
    inside: Counter[str] = Counter()
    outside: Counter[str] = Counter()
    for row in sample:
        (inside if row["in_topic"] else outside).update(set(tokenize(row["text"])))
    words = distinctive_words(inside, outside, inside + outside, top=6)["positive"]
    examples = []
    for label in (2, 0):
        row = conn.execute(
            f"""
            SELECT d.platform, d.url, s.text, p.label, p.confidence {SCORED_ANY_FROM}
              AND %(topic)s = ANY(s.topics) AND p.label = %(label)s AND p.confidence >= 0.8
              AND d.kind = ANY(%(kinds)s) AND d.text_purged_at IS NULL
              AND (d.platform <> 'bluesky' OR d.metrics_updated_at IS NOT NULL)
            ORDER BY d.published_at DESC LIMIT 1
            """,
            params | {"since": since, "label": label, "kinds": list(EXAMPLE_KINDS)},
        ).fetchone()
        if row:
            examples.append(
                {
                    "platform": row["platform"],
                    "url": row["url"],
                    "text": row["text"],
                    "sentiment": LABELS[row["label"]],
                    "confidence": round(float(row["confidence"]), 4),
                }
            )
    return {"id": topic_id, "range": range_key, "weeks": weeks, "words": words, "examples": examples}


# ---------------------------------------------------------------------------
# Events and spikes

BASELINE_MONTHS = 6
MIN_EVENT_TEXTS = 8  # an event month with fewer texts is "too few to call"
SPIKE_RATIO = 2.5  # volume at least this many times the source's recent monthly average
SPIKE_MIN_TEXTS = 10
SPIKE_MIN_BASELINE = 3.0  # average texts per month before a ratio means anything
SHIFT_MIN_DELTA = 0.4  # a sentiment jump also has to be this large to count


def _interval(pos: int, neg: int, n: int) -> tuple[float, float] | tuple[None, None]:
    """Net sentiment and the half-width of its 95% interval (multinomial normal approximation)."""
    if not n:
        return None, None
    a, b = pos / n, neg / n
    net = a - b
    return net, 1.96 * math.sqrt(max(0.0, a + b - net * net) / n)


def _month_range(first: str, last: str) -> list[str]:
    year, month = int(first[:4]), int(first[5:7])
    months = []
    while f"{year:04d}-{month:02d}" <= last:
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return months


def weekly_counts(
    conn: psycopg.Connection, platforms: list[Platform], weeks: int = 26
) -> dict[str, dict[str, list[int]]]:
    """{platform: {"YYYY-MM-DD" (Monday): [negative, neutral, positive]}} for the last `weeks` weeks."""
    now = datetime.now(UTC)
    start = date_trunc_week(now) - timedelta(weeks=weeks - 1)
    params = {"scored": _scored_keys(platforms), "since": start, "until": now}
    rows = conn.execute(
        f"""
        SELECT d.platform, date_trunc('week', d.published_at, 'UTC') AS week, p.label, count(*) AS n
        {SCORED_ANY_FROM}
        GROUP BY 1, 2, 3
        """,
        params,
    ).fetchall()
    keys = [(start + timedelta(weeks=i)).date().isoformat() for i in range(weeks)]
    out = {p.key: {k: [0, 0, 0] for k in keys} for p in platforms}
    for row in rows:
        out[row["platform"]][row["week"].astimezone(UTC).date().isoformat()][row["label"]] = row["n"]
    return out


def series(conn: psycopg.Connection, platforms: list[Platform], bucket: str) -> dict[str, Any]:
    """Sentiment counts per source by month (all time) or by week (last 26 weeks)."""
    counts = monthly_counts(conn, platforms) if bucket == "month" else weekly_counts(conn, platforms)
    return {
        "bucket": bucket,
        "platforms": {
            key: [{"bucket": k, "negative": c[0], "neutral": c[1], "positive": c[2]} for k, c in rows.items()]
            for key, rows in counts.items()
        },
    }


def monthly_counts(conn: psycopg.Connection, platforms: list[Platform]) -> dict[str, dict[str, list[int]]]:
    """{platform: {"YYYY-MM": [negative, neutral, positive]}} over all time, every month from first data."""
    now = datetime.now(UTC)
    params = {"scored": _scored_keys(platforms), "since": datetime(1970, 1, 1, tzinfo=UTC), "until": now}
    rows = conn.execute(
        f"""
        SELECT d.platform, to_char(date_trunc('month', d.published_at, 'UTC'), 'YYYY-MM') AS month,
               p.label, count(*) AS n
        {SCORED_ANY_FROM}
        GROUP BY 1, 2, 3
        """,
        params,
    ).fetchall()
    raw: dict[str, dict[str, list[int]]] = {}
    for row in rows:
        raw.setdefault(row["platform"], {}).setdefault(row["month"], [0, 0, 0])[row["label"]] = row["n"]
    this_month = now.strftime("%Y-%m")
    return {
        platform: {m: months.get(m, [0, 0, 0]) for m in _month_range(min(months), this_month)}
        for platform, months in raw.items()
    }


def _baseline(counts: dict[str, list[int]], months: list[str], index: int) -> list[int]:
    window = months[max(0, index - BASELINE_MONTHS) : index]
    return [sum(counts[m][i] for m in window) for i in range(3)]


def events(conn: psycopg.Connection, platforms: list[Platform], focus: Platform) -> dict[str, Any]:
    """The focus platform's monthly series, each listed event's impact on it, and spikes on every platform."""
    from sentiment.events import EVENTS

    counts = monthly_counts(conn, platforms)
    series = counts.get(focus.key, {})
    months = list(series)
    impacts = []
    for number, event in enumerate(EVENTS, start=1):
        item: dict[str, Any] = {"number": number, "date": event.day.isoformat(), "month": event.month}
        item["title"] = event.title
        if event.month not in series:
            impacts.append(item | {"n": 0, "verdict": "no_data"})
            continue
        index = months.index(event.month)
        neg, neu, pos = series[event.month]
        n = neg + neu + pos
        bneg, bneu, bpos = _baseline(series, months, index)
        base_n = bneg + bneu + bpos
        net, half = _interval(pos, neg, n)
        base_net, _ = _interval(bpos, bneg, base_n)
        if n < MIN_EVENT_TEXTS or base_n < MIN_EVENT_TEXTS:
            verdict = "too_few"
        elif net - half > base_net or net + half < base_net:
            verdict = "shift"
        else:
            verdict = "within_noise"
        impacts.append(
            item
            | {
                "n": n,
                "net_sentiment": round(net, 4) if net is not None else None,
                "interval": round(half, 4) if half is not None else None,
                "baseline_n": base_n,
                "baseline_net": round(base_net, 4) if base_net is not None else None,
                "verdict": verdict,
            }
        )
    return {
        "platform": focus.key,
        "months": [
            {"month": m, "negative": c[0], "neutral": c[1], "positive": c[2]} for m, c in series.items()
        ],
        "events": impacts,
        "spikes": spikes(counts),
    }


def spikes(counts: dict[str, dict[str, list[int]]], limit: int = 20) -> list[dict[str, Any]]:
    """Months where a source's volume or sentiment broke from its previous six months.

    Volume: at least SPIKE_RATIO times the recent monthly average. Sentiment: the month's 95% interval
    clears the pooled baseline by at least SHIFT_MIN_DELTA. Listed events in the same month are matched.
    """
    from sentiment.events import EVENTS

    by_month = {event.month: number for number, event in enumerate(EVENTS, start=1)}
    found = []
    for platform, series in counts.items():
        months = list(series)
        for index, month in enumerate(months):
            if index < BASELINE_MONTHS:
                continue  # not enough history to call anything unusual
            neg, neu, pos = series[month]
            n = neg + neu + pos
            if n < SPIKE_MIN_TEXTS:
                continue
            base = _baseline(series, months, index)
            base_n = sum(base)
            mean = base_n / BASELINE_MONTHS
            net, half = _interval(pos, neg, n)
            base_net, _ = _interval(base[2], base[0], base_n)
            ratio = n / mean if mean >= SPIKE_MIN_BASELINE else None
            kind = None
            if ratio is not None and ratio >= SPIKE_RATIO:
                kind = "volume"
            elif (
                base_net is not None
                and base_n >= 2 * MIN_EVENT_TEXTS
                and abs(net - base_net) >= SHIFT_MIN_DELTA
                and (net - half > base_net or net + half < base_net)
            ):
                kind = "sentiment"
            if kind:
                found.append(
                    {
                        "platform": platform,
                        "month": month,
                        "kind": kind,
                        "n": n,
                        "ratio": round(ratio, 2) if ratio is not None else None,
                        "net_sentiment": round(net, 4),
                        "baseline_net": round(base_net, 4) if base_net is not None else None,
                        "event": by_month.get(month),
                    }
                )
    found.sort(key=lambda s: (s["kind"] != "volume", -(s["ratio"] or 0), s["month"]))
    return found[:limit]


# ---------------------------------------------------------------------------
# Model

CLOSE_CALL = 0.7  # a prediction whose top probability is below this is a close call


def model_overview(conn: psycopg.Connection, platforms: list[Platform], sample: int = 250) -> dict[str, Any]:
    """How the active model behaves on live data: confidence, close calls, and where it hesitates."""
    now = datetime.now(UTC)
    params = {
        "scored": _scored_keys(platforms),
        "since": datetime(1970, 1, 1, tzinfo=UTC),
        "until": now,
        "close": CLOSE_CALL,
        "sample": sample,
        "edges": list(CONFIDENCE_EDGES[1:-1]),
    }
    by_label = conn.execute(
        f"""
        SELECT p.label, count(*) AS n, count(*) FILTER (WHERE p.confidence < %(close)s) AS close,
               avg(p.confidence) AS confidence
        {SCORED_ANY_FROM} GROUP BY 1
        """,
        params,
    ).fetchall()
    by_platform = conn.execute(
        f"""
        SELECT d.platform, count(*) AS n, count(*) FILTER (WHERE p.confidence < %(close)s) AS close,
               avg(p.confidence) AS confidence,
               array_agg(width_bucket(p.confidence, %(edges)s::real[])) AS bins
        {SCORED_ANY_FROM} GROUP BY 1
        """,
        params,
    ).fetchall()
    probabilities = conn.execute(
        f"""
        SELECT round(p.p_neg::numeric, 3) AS neg, round(p.p_neu::numeric, 3) AS neu,
               round(p.p_pos::numeric, 3) AS pos
        {SCORED_ANY_FROM} ORDER BY d.published_at DESC LIMIT %(sample)s
        """,
        params,
    ).fetchall()
    closest = conn.execute(
        f"""
        SELECT d.platform, d.url, s.text, p.p_neg, p.p_neu, p.p_pos {SCORED_ANY_FROM}
          AND d.kind = ANY(%(kinds)s) AND d.text_purged_at IS NULL AND p.confidence < 0.6
          AND (d.platform <> 'bluesky' OR d.metrics_updated_at IS NOT NULL)
        ORDER BY d.published_at DESC LIMIT 4
        """,
        params | {"since": now - timedelta(days=30), "kinds": list(EXAMPLE_KINDS)},
    ).fetchall()
    total = sum(r["n"] for r in by_label)
    platform_rows = {r["platform"]: r for r in by_platform}
    return {
        "model": active_model(conn),
        "close_call_below": CLOSE_CALL,
        "bin_edges": [round(e, 4) for e in CONFIDENCE_EDGES],
        "scored": total,
        "confidence": round(sum(float(r["confidence"]) * r["n"] for r in by_label) / total, 4)
        if total
        else None,
        "close_calls": sum(r["close"] for r in by_label),
        "by_label": {LABELS[r["label"]]: {"n": r["n"], "close": r["close"]} for r in by_label},
        "by_platform": [
            {
                "platform": p.key,
                "n": platform_rows[p.key]["n"],
                "close": platform_rows[p.key]["close"],
                "confidence": round(float(platform_rows[p.key]["confidence"]), 4),
                "bins": [platform_rows[p.key]["bins"].count(i) for i in range(len(CONFIDENCE_EDGES) - 1)],
            }
            for p in platforms
            if p.key in platform_rows
        ],
        "sample": [[float(r["neg"]), float(r["neu"]), float(r["pos"])] for r in probabilities],
        "closest": [
            {
                "platform": r["platform"],
                "url": r["url"],
                "text": r["text"],
                "probabilities": dict(
                    zip(LABELS, (round(float(r[k]), 4) for k in ("p_neg", "p_neu", "p_pos")), strict=True)
                ),
            }
            for r in closest
        ],
    }
