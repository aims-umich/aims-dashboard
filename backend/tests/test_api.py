from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from sentiment.api.app import create_app
from sentiment.api.queries import distinctive_words, spikes
from sentiment.scorer.service import explain_batch, register_model, score_batch
from sentiment.topics import topics_for
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
            "INSERT INTO segments (document_id, ordinal, text, relevance, topics)"
            " VALUES (%s, %s, %s, %s, %s)",
            (doc, i, text, relevance, topics_for(text)),
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


def test_repeated_failures_mark_a_platform_broken_even_after_a_recent_success(client, seeded):
    seeded.execute(
        "INSERT INTO ingest_state (source, interval_s, last_success_at, consecutive_failures) VALUES"
        " ('youtube', 1800, now(), 0), ('youtube_comments', 1800, now() - interval '5 minutes', 3)"
    )
    youtube = next(p for p in client.get("/api/v1/status").json()["platforms"] if p["platform"] == "youtube")
    assert youtube["state"] == "error"
    assert {j["job"]: j["state"] for j in youtube["jobs"]}["youtube_comments"] == "error"


def test_a_job_that_has_not_run_yet_does_not_hide_a_healthy_platform(client, seeded):
    seeded.execute(
        "INSERT INTO ingest_state (source, interval_s, last_success_at, consecutive_failures)"
        " VALUES ('bluesky', 30, now(), 0)"
    )  # bluesky_metrics has no row yet
    bluesky = next(p for p in client.get("/api/v1/status").json()["platforms"] if p["platform"] == "bluesky")
    assert bluesky["state"] == "ok"


def test_24h_range_uses_hourly_buckets(client):
    body = client.get("/api/v1/platforms/mastodon/summary", params={"range": "24h"}).json()
    assert body["bucket"] == "hour"
    assert body["totals"]["documents"] == 1
    assert body["trend"][-1]["bucket"] == NOW.strftime("%Y-%m-%dT%H:00:00Z")
    assert 24 <= len(body["trend"]) <= 25


def test_activity_counts_weekday_hours_and_the_hours_we_were_collecting(client):
    activity = client.get("/api/v1/platforms/mastodon/summary", params={"range": "7d"}).json()["activity"]
    assert activity["window_days"] == 28
    assert sum(map(sum, activity["counts"])) == 2  # the excluded idiom and the 400-day-old post do not count
    one_hour_ago = NOW - timedelta(hours=1)
    assert activity["counts"][one_hour_ago.weekday()][one_hour_ago.hour] >= 1
    assert sum(map(sum, activity["slots"])) == 28 * 24 or sum(map(sum, activity["slots"])) == 28 * 24 + 1


def test_engagement_by_sentiment(client):
    engagement = client.get("/api/v1/platforms/mastodon/summary", params={"range": "30d"}).json()[
        "engagement"
    ]
    assert engagement["by_sentiment"]["positive"]["n"] == 1
    assert engagement["by_sentiment"]["positive"]["likes"]["mean"] == 4
    assert engagement["by_sentiment"]["negative"]["reposts"]["mean"] == 2


def test_strip_lists_every_scored_text_of_the_last_day(client):
    body = client.get("/api/v1/strip").json()
    mastodon = next(p for p in body["platforms"] if p["platform"] == "mastodon")
    assert mastodon["count"] == 1
    [[stamp, label, confidence]] = mastodon["items"]
    assert label == 2 and confidence == 80
    assert abs(stamp - (NOW - timedelta(hours=1)).timestamp()) < 5
    assert mastodon["collecting_since"] is not None


def test_distinctive_words_favor_words_used_mostly_on_one_side():
    from collections import Counter

    positive = Counter({"clean": 30, "power": 40, "safe": 12})
    negative = Counter({"waste": 25, "power": 38, "risk": 10})
    result = distinctive_words(positive, negative, positive + negative)
    assert [w["word"] for w in result["positive"]][:2] == ["clean", "safe"]
    assert [w["word"] for w in result["negative"]][:2] == ["waste", "risk"]
    assert "power" not in [w["word"] for w in result["positive"][:2] + result["negative"][:2]]


def test_words_include_label_counts_in_the_cloud(client):
    cloud = client.get("/api/v1/platforms/mastodon/words").json()["cloud"]
    waste = next(w for w in cloud if w["value"] == "waste")
    assert (waste["positive"], waste["negative"]) == (0, 1)


def test_topics_count_share_sentiment_and_platforms(client):
    body = client.get("/api/v1/topics", params={"range": "30d"}).json()
    waste = next(t for t in body["topics"] if t["id"] == "waste")
    assert body["texts"] == 6
    assert waste["count"] == 1 and waste["sentiment"]["negative"] == 1
    assert waste["share"] == round(1 / 6, 4)
    assert waste["by_platform"] == {"mastodon": {"n": 1, "net": -1.0}}
    assert len(waste["weekly"]) == 12 and sum(waste["weekly"]) == 1
    assert body["topics"][0]["id"] == "data-centers"


def test_topic_detail_and_unknown_topic(client, db):
    add_doc(db, "mastodon", "m5", "post", NOW - timedelta(hours=3), ["fusion power is good"])
    add_doc(db, "mastodon", "m6", "post", NOW - timedelta(hours=4), ["fusion is bad"])
    clf = FakeClassifier()
    model_id = register_model(db, clf.info)
    while score_batch(db, clf, model_id, 50):
        pass
    db.execute("UPDATE documents SET metrics_updated_at = now()")
    body = client.get("/api/v1/topics/fusion", params={"range": "7d"}).json()
    assert sum(w["count"] for w in body["weeks"]) == 2
    assert [e["text"] for e in body["examples"]] == [
        "fusion power is good"
    ]  # the negative one is not sure enough
    assert client.get("/api/v1/topics/astrology").status_code == 404


def test_spikes_flag_volume_and_sentiment_breaks_and_match_events():
    quiet = [2, 3, 2]  # negative, neutral, positive
    counts = {
        "nyt": {f"2022-{m:02d}": quiet for m in range(1, 8)}
        | {"2022-08": [30, 15, 5]}  # the Zaporizhzhia month: volume spike, matches event 2
        | {"2022-09": quiet, "2022-10": quiet, "2022-11": quiet, "2022-12": [1, 3, 11]},
    }
    found = {(s["month"], s["kind"]): s for s in spikes(counts)}
    assert found[("2022-08", "volume")]["event"] == 2
    assert found[("2022-08", "volume")]["ratio"] == pytest.approx(50 / 7, abs=0.01)
    assert found[("2022-12", "sentiment")]["event"] == 3
    assert ("2022-05", "volume") not in found


def test_events_endpoint_lists_every_event_for_the_focus_platform(client):
    body = client.get("/api/v1/events", params={"platform": "mastodon"}).json()
    assert body["platform"] == "mastodon"
    assert len(body["events"]) == 9 and body["events"][0]["verdict"] == "no_data"
    assert body["months"][-1]["month"] == NOW.strftime("%Y-%m")
    assert client.get("/api/v1/events", params={"platform": "myspace"}).status_code == 404


def test_model_overview(client):
    body = client.get("/api/v1/model").json()
    assert body["model"]["name"] == "fake/model"
    assert body["scored"] == 7 and body["close_call_below"] == 0.7
    assert body["close_calls"] == body["by_label"]["neutral"]["close"] + body["by_label"]["negative"]["close"]
    assert len(body["sample"]) == 7 and all(abs(sum(p) - 1) < 0.01 for p in body["sample"])
    mastodon = next(p for p in body["by_platform"] if p["platform"] == "mastodon")
    assert sum(mastodon["bins"]) == mastodon["n"] == 3


def test_posts_carry_word_highlights_once_explained(client, seeded):
    clf = FakeClassifier()
    model_id = register_model(seeded, clf.info)
    while explain_batch(seeded, clf, model_id, 10, days=14):
        pass
    items = client.get("/api/v1/platforms/mastodon/posts").json()["items"]
    by_text = {p["text"]: p["highlights"] for p in items}
    assert by_text["nuclear power is good"] == [[17, 21, 1.0]]
    assert by_text["nuclear plants exist"] is None  # 400 days old: never explained
    assert all(p["sentences"] is None for p in items)


def test_articles_list_their_scored_sentences_with_highlights(client, seeded):
    clf = FakeClassifier()
    model_id = register_model(seeded, clf.info)
    while explain_batch(seeded, clf, model_id, 10, days=14):
        pass
    article = client.get("/api/v1/platforms/guardian/posts").json()["items"][0]
    assert article["highlights"] is None
    assert [(s["text"], s["sentiment"]) for s in article["sentences"]] == [
        ("a good reactor", "positive"),
        ("a bad reactor", "negative"),
        ("a good plant", "positive"),
    ]
    assert article["sentences"][0]["highlights"] == [[2, 6, 1.0]]


def test_series_by_month_and_week(client):
    months = client.get("/api/v1/series").json()["platforms"]["mastodon"]
    assert months[-1]["bucket"] == NOW.strftime("%Y-%m")
    assert sum(m["positive"] + m["neutral"] + m["negative"] for m in months) == 3
    weeks = client.get("/api/v1/series", params={"bucket": "week"}).json()["platforms"]["mastodon"]
    assert len(weeks) == 26 and sum(w["positive"] + w["neutral"] + w["negative"] for w in weeks) == 2
    assert client.get("/api/v1/series", params={"bucket": "day"}).status_code == 422
