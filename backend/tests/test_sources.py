"""Collector parsing and polling against mocked platform APIs."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from sentiment.db import async_pool
from sentiment.ingest import store
from sentiment.ingest.base import RateLimitedError, SourceDisabledError, redact
from sentiment.ingest.sources.bluesky import BlueskyMetricsJob, parse_event
from sentiment.ingest.sources.guardian import GuardianJob, parse_result
from sentiment.ingest.sources.mastodon import MastodonJob, parse_status
from sentiment.ingest.sources.nyt import NytJob, parse_doc
from sentiment.ingest.sources.reddit import RedditComplianceJob, RedditJob
from sentiment.ingest.sources.youtube import YouTubeCommentsJob, YouTubeSearchJob, seconds_until_quota_reset
from sentiment.text import EXCLUDED, RELEVANT
from tests import factories as f


@pytest.fixture
async def pool(database_url, db):
    pool = await async_pool(database_url)
    yield pool
    await pool.close()


@pytest.fixture
async def client():
    async with httpx.AsyncClient() as client:
        yield client


# --- Bluesky -----------------------------------------------------------------


def test_bluesky_keeps_relevant_english_posts():
    doc = parse_event(f.jetstream_post("Nuclear power keeps the lights on", rkey="3xyz"))
    assert doc.external_id == "at://did:plc:testuser/app.bsky.feed.post/3xyz"
    assert doc.url == "https://bsky.app/profile/did:plc:testuser/post/3xyz"
    assert doc.segments[0].relevance.status == RELEVANT
    assert doc.published_at == datetime(2026, 9, 22, 12, 26, 40, tzinfo=UTC)


@pytest.mark.parametrize(
    "event",
    [
        f.jetstream_post("A lovely day at the beach"),
        f.jetstream_post("The nuclear option is back in the Senate"),
        f.jetstream_post("Kernkraft ist die Zukunft der nuclear Energie", langs=["de"]),
        f.jetstream_post("nuclear hot take", labels=["porn"]),
        {"kind": "identity", "did": "did:plc:x", "time_us": 1},
    ],
)
def test_bluesky_drops_everything_else(event):
    assert parse_event(event) is None


def test_bluesky_delete_becomes_deletion_key():
    assert parse_event(f.jetstream_delete(rkey="3gone")) == (
        "bluesky",
        "at://did:plc:testuser/app.bsky.feed.post/3gone",
    )


def test_bluesky_distrusts_backdated_created_at():
    event = f.jetstream_post("nuclear energy history", created_at="2019-01-01T00:00:00Z")
    doc = parse_event(event)
    assert doc.published_at == datetime.fromtimestamp(event["time_us"] / 1e6, tz=UTC)


@respx.mock
async def test_bluesky_metrics_refresh_updates_counts_and_drops_removed(settings, client, pool):
    kept = parse_event(f.jetstream_post("nuclear power rocks", rkey="3keep"))
    gone = parse_event(f.jetstream_post("nuclear power again", rkey="3gone"))
    hidden = parse_event(f.jetstream_post("nuclear power, quietly", rkey="3hide"))
    kept.published_at = gone.published_at = hidden.published_at = datetime.now(UTC)
    async with pool.connection() as conn, conn.transaction():
        await store.save_documents(conn, [kept, gone, hidden])
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.feed.getPosts").respond(
        json={
            "posts": [
                {
                    "uri": kept.external_id,
                    "likeCount": 9,
                    "repostCount": 2,
                    "replyCount": 1,
                    "quoteCount": 0,
                    "author": {"handle": "someone.bsky.social"},
                    "labels": [],
                },
                {
                    "uri": hidden.external_id,
                    "author": {"handle": "private.bsky.social", "labels": [{"val": "!no-unauthenticated"}]},
                    "labels": [],
                },
            ]
        }
    )
    result = await BlueskyMetricsJob(settings, client, pool).poll({})
    assert sorted(result.deletions) == sorted(
        [("bluesky", gone.external_id), ("bluesky", hidden.external_id)]
    )
    assert result.metric_updates[0][2]["likes"] == 9
    async with pool.connection() as conn:
        await store.commit_run(conn, "bluesky_metrics", result, 3600)
        rows = await (
            await conn.execute("SELECT external_id, author_handle, metrics FROM documents")
        ).fetchall()
    assert [(r["external_id"], r["author_handle"], r["metrics"]["likes"]) for r in rows] == [
        (kept.external_id, "someone.bsky.social", 9)
    ]


# --- Mastodon ----------------------------------------------------------------


def test_mastodon_parses_html_and_metrics():
    doc = parse_status(
        f.mastodon_status("10", "<p>New <a href='#'>#NuclearPower</a> plant approved</p>"), "example.social"
    )
    assert doc.body == "New #NuclearPower plant approved"
    assert doc.author_handle == "tester@example.social"
    assert doc.metrics == {"replies": 1, "reposts": 2, "likes": 3, "sensitive": False, "has_media": False}
    assert doc.segments[0].relevance.status == RELEVANT


def test_mastodon_skips_noindex_and_bot_accounts():
    noindex = f.mastodon_status("20", "<p>nuclear power</p>")
    noindex["account"]["noindex"] = True
    bot = f.mastodon_status("21", "<p>nuclear power</p>")
    bot["account"]["bot"] = True
    assert parse_status(noindex, "m.s") is None
    assert parse_status(bot, "m.s") is None


def test_mastodon_skips_bridged_and_private_posts():
    bridged = f.mastodon_status(
        "11", "<p>nuclear</p>", uri="https://bsky.brid.gy/convert/ap/at://did:plc:x/post/1"
    )
    assert parse_status(bridged, "mastodon.social") is None
    assert parse_status(f.mastodon_status("12", "<p>nuclear</p>", visibility="unlisted"), "m.s") is None


@respx.mock
async def test_mastodon_paginates_from_cursor_and_advances_it(settings, client, pool):
    settings.mastodon_instances = "example.social"
    settings.mastodon_hashtags = "nuclear"
    page1 = [f.mastodon_status(str(i), f"<p>nuclear energy post {i}</p>") for i in range(140, 100, -1)]
    page2 = [f.mastodon_status("141", "<p>nuclear energy post 141</p>")]
    route = respx.get("https://example.social/api/v1/timelines/tag/nuclear")
    route.side_effect = [httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
    result = await MastodonJob(settings, client, pool).poll({"example.social/nuclear": "100"})
    assert route.calls[0].request.url.params["min_id"] == "100"
    assert route.calls[1].request.url.params["min_id"] == "140"
    assert result.cursor == {"example.social/nuclear": "141"}
    assert len(result.documents) == 41


@respx.mock
async def test_mastodon_rate_limit_is_surfaced(settings, client, pool):
    settings.mastodon_instances = "example.social"
    settings.mastodon_hashtags = "nuclear"
    respx.get("https://example.social/api/v1/timelines/tag/nuclear").respond(
        429, headers={"retry-after": "120"}
    )
    with pytest.raises(RateLimitedError) as info:
        await MastodonJob(settings, client, pool).poll({})
    assert info.value.retry_after_s == 120


# --- Guardian ----------------------------------------------------------------


def test_guardian_scores_nuclear_sentences_only():
    body = (
        "The state budget passed on Monday. Lawmakers approved money for a new nuclear plant. "
        "Critics said Iran's nuclear program was a bigger worry. Parking fees also rose."
    )
    doc = parse_result(f.guardian_result("us-news/2026/sep/28/budget", body))
    assert [(s.text, s.relevance.status) for s in doc.segments] == [
        ("Lawmakers approved money for a new nuclear plant.", RELEVANT),
        ("Critics said Iran's nuclear program was a bigger worry.", EXCLUDED),
    ]
    assert doc.body == "A short standfirst."
    assert doc.metrics == {"word_count": 812}


@respx.mock
async def test_guardian_pages_and_keeps_newest_cursor(settings, client, pool):
    route = respx.get("https://content.guardianapis.com/search")
    route.side_effect = [
        httpx.Response(
            200,
            json=f.guardian_page(
                [f.guardian_result("a/1", "nuclear power.", date="2026-09-28T10:00:00Z")], pages=2
            ),
        ),
        httpx.Response(
            200,
            json=f.guardian_page(
                [f.guardian_result("a/2", "reactors.", date="2026-09-27T10:00:00Z")], page=2, pages=2
            ),
        ),
    ]
    result = await GuardianJob(settings, client, pool).poll({"latest": "2026-09-27T00:00:00+00:00"})
    first = route.calls[0].request.url.params
    assert first["from-date"] == "2026-09-26"
    assert first["section"] == "us-news"
    assert first["api-key"] == "guardian-secret"
    assert [d.external_id for d in result.documents] == ["a/1", "a/2"]
    assert result.cursor == {"latest": "2026-09-28T10:00:00+00:00"}


async def test_guardian_without_key_is_disabled(settings, client, pool):
    settings.guardian_api_key = None
    with pytest.raises(SourceDisabledError):
        await GuardianJob(settings, client, pool).poll({})


# --- NYT ---------------------------------------------------------------------


def test_nyt_uses_headline_when_abstract_lacks_keyword():
    doc = parse_doc(
        f.nyt_doc("x1", "Regulators approved it on Monday.", headline="Nuclear Plant Gets a Second Life")
    )
    assert doc.segments[0].relevance.status == RELEVANT
    assert doc.published_at == datetime(2026, 9, 28, 9, 0, tzinfo=UTC)
    assert doc.author_handle == "A Writer"


@respx.mock
async def test_nyt_stops_after_a_short_page(settings, client, pool):
    route = respx.get("https://api.nytimes.com/svc/search/v2/articlesearch.json").respond(
        json={
            "status": "OK",
            "response": {"docs": [f.nyt_doc("x2", "A nuclear reactor restarts.")], "metadata": {"hits": 1}},
        }
    )
    result = await NytJob(settings, client, pool).poll({})
    assert route.call_count == 1
    assert result.documents[0].external_id == "nyt://article/x2"


# --- YouTube -----------------------------------------------------------------


@respx.mock
async def test_youtube_search_keeps_only_relevant_videos(settings, client, pool):
    respx.get("https://www.googleapis.com/youtube/v3/search").respond(
        json={"items": [{"id": {"videoId": "v1"}}, {"id": {"videoId": "v2"}}]}
    )
    respx.get("https://www.googleapis.com/youtube/v3/videos").respond(
        json={
            "items": [
                f.youtube_video("v1", "Why nuclear energy is back"),
                f.youtube_video("v2", "Cooking pasta"),
            ]
        }
    )
    result = await YouTubeSearchJob(settings, client, pool).poll({})
    assert [d.external_id for d in result.documents] == ["v1"]
    assert result.documents[0].metrics == {"views": 1000, "likes": 50, "comments": 7}


@respx.mock
async def test_youtube_comments_only_new_and_skip_disabled(settings, client, pool):
    video = f.youtube_video("vid1", "Nuclear reactors explained", published=datetime.now(UTC).isoformat())
    muted = f.youtube_video("vid2", "Nuclear waste explained", published=datetime.now(UTC).isoformat())
    from sentiment.ingest.sources.youtube import parse_video

    async with pool.connection() as conn, conn.transaction():
        await store.save_documents(conn, [parse_video(video), parse_video(muted)])

    def threads(request):
        if request.url.params["videoId"] == "vid2":
            return httpx.Response(403, json={"error": {"errors": [{"reason": "commentsDisabled"}]}})
        return httpx.Response(
            200,
            json={
                "items": [
                    f.youtube_thread("c3", "Great explainer!", published="2026-09-29T10:00:00Z"),
                    f.youtube_thread("c2", "Seen already", published="2026-09-28T10:00:00Z"),
                ]
            },
        )

    respx.get("https://www.googleapis.com/youtube/v3/commentThreads").mock(side_effect=threads)
    respx.get("https://www.googleapis.com/youtube/v3/videos").respond(json={"items": [video, muted]})
    job = YouTubeCommentsJob(settings, client, pool)
    result = await job.poll({"seen": {"vid1": "2026-09-28T10:00:00+00:00"}})
    assert [d.external_id for d in result.documents] == ["c3"]
    assert result.documents[0].parent_external_id == "vid1"
    assert result.documents[0].segments[0].relevance.status == RELEVANT
    assert result.cursor["seen"]["vid1"] == "2026-09-29T10:00:00+00:00"
    assert result.cursor["disabled"] == ["vid2"]
    assert {u[1] for u in result.metric_updates} == {"vid1", "vid2"}


@respx.mock
async def test_youtube_quota_exhaustion_waits_until_reset(settings, client, pool):
    respx.get("https://www.googleapis.com/youtube/v3/search").respond(
        403, json={"error": {"errors": [{"reason": "quotaExceeded"}]}}
    )
    with pytest.raises(RateLimitedError):
        await YouTubeSearchJob(settings, client, pool).poll({})
    # 23:00 Pacific -> resets at 00:05 Pacific, 65 minutes later.
    assert seconds_until_quota_reset(datetime(2026, 9, 29, 6, 0, tzinfo=UTC)) == 65 * 60


# --- Reddit ------------------------------------------------------------------


@respx.mock
async def test_reddit_authenticates_and_filters_old_nsfw_and_removed(settings, client, pool):
    settings.reddit_subreddits = "nuclear"
    token = respx.post("https://www.reddit.com/api/v1/access_token").respond(
        json={"access_token": "tok", "expires_in": 3600}
    )
    listing = f.reddit_listing(
        [
            f.reddit_post("t3_new", "New nuclear plant approved", created=2000),
            f.reddit_post("t3_old", "Old nuclear news", created=900),
            f.reddit_post("t3_nsfw", "nuclear", created=2001, over_18=True),
            f.reddit_post("t3_gone", "nuclear", created=2002, selftext="[removed]"),
        ]
    )
    respx.get("https://oauth.reddit.com/search").respond(json=listing)
    feed = respx.get("https://oauth.reddit.com/r/nuclear/new").respond(json=listing)
    result = await RedditJob(settings, client, pool).poll({"search": 1000, "r/nuclear": 1000})
    assert token.call_count == 1
    assert feed.calls[0].request.headers["authorization"] == "Bearer tok"
    assert [d.external_id for d in result.documents] == ["t3_new"]
    assert result.cursor == {"search": 2002, "r/nuclear": 2002}


@respx.mock
async def test_reddit_compliance_deletes_removed_posts(settings, client, pool):
    from sentiment.ingest.sources.reddit import parse_post

    posts = [
        parse_post(f.reddit_post(name, "nuclear power", created=2000)["data"])
        for name in ("t3_a", "t3_b", "t3_c")
    ]
    async with pool.connection() as conn, conn.transaction():
        await store.save_documents(conn, posts)
    respx.post("https://www.reddit.com/api/v1/access_token").respond(json={"access_token": "tok"})
    respx.get("https://oauth.reddit.com/api/info").respond(
        json=f.reddit_listing(
            [
                f.reddit_post("t3_a", "nuclear power", created=2000, score=99),
                f.reddit_post("t3_b", "nuclear power", created=2000, removed_by_category="moderator"),
            ]
        )
    )
    result = await RedditComplianceJob(settings, client, pool).poll({})
    assert sorted(result.deletions) == [("reddit", "t3_b"), ("reddit", "t3_c")]
    assert result.metric_updates == [("reddit", "t3_a", {"score": 99, "comments": 3, "upvote_ratio": 0.9})]


# --- Shared ------------------------------------------------------------------


def test_redact_scrubs_known_secrets_and_key_params():
    message = "HTTP 401 from api.example.com/search?api-key=abc123&q=x token=zzz and literal s3cr3t"
    assert (
        redact(message, ["s3cr3t"])
        == "HTTP 401 from api.example.com/search?api-key=***&q=x token=*** and literal ***"
    )
