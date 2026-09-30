from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from sentiment.api.app import create_app
from sentiment.scorer.service import register_model, score_batch
from tests.fake import FakeClassifier

NOW = datetime.now(UTC)


def add_doc(db, platform, external_id, kind, published_at, texts, *, metrics=None, parent=None, title=None):
    doc = db.execute(
        """
        INSERT INTO documents
            (platform, external_id, kind, parent_id, url, title, body, published_at, metrics)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """,
        (
            platform,
            external_id,
            kind,
            parent,
            f"https://x/{external_id}",
            title,
            " ".join(texts),
            published_at,
            Jsonb(metrics or {}),
        ),
    ).fetchone()["id"]
    for i, (text, relevance) in enumerate(
        texts.items() if isinstance(texts, dict) else ((t, "relevant") for t in texts)
    ):
        db.execute(
            "INSERT INTO segments (document_id, ordinal, text, relevance) VALUES (%s, %s, %s, %s)",
            (doc, i, text, relevance),
        )
    return doc


@pytest.fixture
def seeded(db):
    add_doc(
        db,
        "mastodon",
        "m1",
        "post",
        NOW - timedelta(hours=1),
        ["nuclear power is good"],
        metrics={"likes": 4, "reposts": 0, "replies": 2},
    )
    add_doc(
        db,
        "mastodon",
        "m2",
        "post",
        NOW - timedelta(days=3),
        ["nuclear waste is bad"],
        metrics={"likes": 0, "reposts": 2, "replies": 0},
    )
    add_doc(
        db,
        "mastodon",
        "m3",
        "post",
        NOW - timedelta(days=400),
        ["nuclear plants exist"],
        metrics={"likes": 1, "reposts": 1, "replies": 1},
    )
    add_doc(db, "mastodon", "m4", "post", NOW - timedelta(hours=2), {"the nuclear option": "excluded"})
    add_doc(
        db,
        "guardian",
        "g1",
        "article",
        NOW - timedelta(days=1),
        ["a good reactor", "a bad reactor", "a good plant"],
        title="Reactor story",
    )
    video = add_doc(db, "youtube", "v1", "video", NOW - timedelta(days=2), [], title="Nuclear explained")
    add_doc(
        db,
        "youtube",
        "c1",
        "comment",
        NOW - timedelta(days=1),
        ["good video"],
        parent=video,
        metrics={"likes": 3, "replies": 0},
    )
    clf = FakeClassifier()
    model_id = register_model(db, clf.info)
    while score_batch(db, clf, model_id, 50):
        pass
    db.execute(
        "INSERT INTO ingest_state (source, interval_s, last_success_at, consecutive_failures)"
        " VALUES ('mastodon', 120, now(), 0), ('guardian', 1800, now() - interval '3 hours', 0),"
        " ('nyt', 3600, NULL, 2)"
    )
    return db


@pytest.fixture
def client(settings, seeded):
    with TestClient(create_app(settings)) as client:
        yield client


def test_summary_counts_trend_and_engagement(client):
    body = client.get("/api/v1/platforms/mastodon/summary", params={"range": "30d"}).json()
    assert body["totals"]["documents"] == 2
    assert body["totals"]["last_24h"] == 1
    assert body["sentiment"] == {"negative": 1, "neutral": 0, "positive": 1}
    assert body["net_sentiment"] == 0
    assert body["bucket"] == "day"
    assert sum(b["positive"] + b["negative"] + b["neutral"] for b in body["trend"]) == 2
    assert body["trend"][-1]["bucket"] == NOW.date().isoformat()
    assert body["engagement"]["averages"] == {"likes": 2.0, "reposts": 1.0, "replies": 1.0}
    assert sum(b["count"] for b in body["confidence"]) == 2


def test_summary_all_range_includes_history_in_monthly_buckets(client):
    body = client.get("/api/v1/platforms/mastodon/summary").json()
    assert body["range"] == "all" and body["bucket"] == "month"
    assert body["totals"]["documents"] == 3
    assert len(body["trend"]) >= 13


def test_article_sentiment_is_mean_of_sentences(client):
    body = client.get("/api/v1/platforms/guardian/summary", params={"range": "7d"}).json()
    assert body["sentiment"] == {"negative": 1, "neutral": 0, "positive": 2}
    assert body["engagement"] is None
    posts = client.get("/api/v1/platforms/guardian/posts").json()["items"]
    assert posts[0]["sentiment"] == "positive" and posts[0]["segments"] == 3


def test_posts_paginate_filter_and_link_parents(client):
    first = client.get("/api/v1/platforms/mastodon/posts", params={"limit": 2}).json()
    assert [p["text"] for p in first["items"]] == ["nuclear power is good", "nuclear waste is bad"]
    rest = client.get(
        "/api/v1/platforms/mastodon/posts", params={"limit": 2, "before": first["next_cursor"]}
    ).json()
    assert [p["text"] for p in rest["items"]] == ["nuclear plants exist"] and rest["next_cursor"] is None
    negative = client.get("/api/v1/platforms/mastodon/posts", params={"sentiment": "negative"}).json()[
        "items"
    ]
    assert [p["sentiment"] for p in negative] == ["negative"]
    comment = client.get("/api/v1/platforms/youtube/posts").json()["items"][0]
    assert comment["parent"] == {"title": "Nuclear explained", "url": "https://x/v1"}
    assert client.get("/api/v1/platforms/mastodon/posts", params={"before": "garbage"}).status_code == 400


def test_words_count_once_per_segment_and_drop_stopwords(client):
    body = client.get("/api/v1/platforms/mastodon/words").json()
    assert body["sampled"] == 3
    assert {w["word"] for w in body["positive"]} == {"power", "good"}
    assert "nuclear" not in {w["value"] for w in body["cloud"]}


def test_status_reports_fresh_stale_error_and_pending(client):
    body = client.get("/api/v1/status").json()
    states = {p["platform"]: p["state"] for p in body["platforms"]}
    assert states == {
        "bluesky": "pending",
        "mastodon": "ok",
        "youtube": "pending",
        "guardian": "stale",
        "nyt": "error",
    }
    assert body["scorer"]["backlog"] == 0 and body["scorer"]["ok"] is True
    assert body["scorer"]["model"]["name"] == "fake/model"


def test_platform_index_and_disabled_platforms(client):
    body = client.get("/api/v1/platforms").json()
    assert [p["platform"] for p in body["platforms"]] == ["bluesky", "mastodon", "youtube", "guardian", "nyt"]
    mastodon = next(p for p in body["platforms"] if p["platform"] == "mastodon")
    assert mastodon["totals"]["scored"] == 2 and mastodon["scored_all_time"] == 3
    assert client.get("/api/v1/platforms/reddit/summary").status_code == 404
    assert client.get("/api/v1/platforms/threads/summary").status_code == 404
    assert client.get("/api/v1/platforms/mastodon/summary", params={"range": "5y"}).status_code == 422


def test_api_connections_are_read_only(client, settings):
    import psycopg

    assert client.get("/healthz").json() == {"ok": True}
    # Same session options as the app's pool: writes are rejected by Postgres itself.
    options = "-c default_transaction_read_only=on"
    with (
        psycopg.connect(settings.database_url, options=options) as conn,
        pytest.raises(psycopg.errors.ReadOnlySqlTransaction),
    ):
        conn.execute("DELETE FROM documents")


def test_rate_limit_and_cache_headers(settings, seeded):
    settings.api_rate_limit_per_min = 3
    with TestClient(create_app(settings)) as client:
        codes = [client.get("/api/v1/status").status_code for _ in range(4)]
        assert codes == [200, 200, 200, 429]
    settings.api_rate_limit_per_min = 300
    settings.api_cache_ttl_s = 30
    with TestClient(create_app(settings)) as client:
        cache_control = client.get("/api/v1/status").headers["cache-control"]
        assert cache_control == "public, max-age=30, s-maxage=30, stale-while-revalidate=60"
