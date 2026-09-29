"""Synthetic API payloads with the same shape as each platform's real responses (no real users)."""

from __future__ import annotations

from typing import Any


def jetstream_post(
    text: str,
    *,
    did: str = "did:plc:testuser",
    rkey: str = "3abc",
    time_us: int = 1_790_000_000_000_000,
    created_at: str = "2026-09-22T12:26:40.000Z",
    langs: list[str] | None = None,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "$type": "app.bsky.feed.post",
        "createdAt": created_at,
        "langs": ["en"] if langs is None else langs,
        "text": text,
    }
    if labels:
        record["labels"] = {
            "$type": "com.atproto.label.defs#selfLabels",
            "values": [{"val": v} for v in labels],
        }
    return {
        "did": did,
        "time_us": time_us,
        "kind": "commit",
        "commit": {
            "rev": "3rev",
            "operation": "create",
            "collection": "app.bsky.feed.post",
            "rkey": rkey,
            "record": record,
            "cid": "bafytest",
        },
    }


def jetstream_delete(did: str = "did:plc:testuser", rkey: str = "3abc") -> dict[str, Any]:
    return {
        "did": did,
        "time_us": 1_790_000_001_000_000,
        "kind": "commit",
        "commit": {"rev": "3rev2", "operation": "delete", "collection": "app.bsky.feed.post", "rkey": rkey},
    }


def mastodon_status(
    status_id: str,
    content: str,
    *,
    language: str | None = "en",
    uri: str | None = None,
    visibility: str = "public",
    created_at: str = "2026-09-29T16:15:58.614Z",
) -> dict[str, Any]:
    return {
        "id": status_id,
        "created_at": created_at,
        "sensitive": False,
        "spoiler_text": "",
        "visibility": visibility,
        "language": language,
        "uri": uri or f"https://example.social/users/tester/statuses/{status_id}",
        "url": f"https://example.social/@tester/{status_id}",
        "replies_count": 1,
        "reblogs_count": 2,
        "favourites_count": 3,
        "content": content,
        "reblog": None,
        "account": {
            "id": "1",
            "username": "tester",
            "acct": "tester",
            "url": "https://example.social/@tester",
        },
        "media_attachments": [],
        "tags": [{"name": "nuclear"}],
    }


def guardian_result(article_id: str, body: str, *, date: str = "2026-09-28T10:00:00Z") -> dict[str, Any]:
    return {
        "id": article_id,
        "type": "article",
        "sectionId": "us-news",
        "sectionName": "US news",
        "webPublicationDate": date,
        "webTitle": f"Title for {article_id}",
        "webUrl": f"https://www.theguardian.com/{article_id}",
        "apiUrl": f"https://content.guardianapis.com/{article_id}",
        "fields": {
            "trailText": "<p>A short standfirst.</p>",
            "byline": "A Reporter",
            "wordcount": "812",
            "bodyText": body,
        },
    }


def guardian_page(results: list[dict[str, Any]], *, page: int = 1, pages: int = 1) -> dict[str, Any]:
    return {
        "response": {
            "status": "ok",
            "total": len(results),
            "startIndex": 1,
            "pageSize": 50,
            "currentPage": page,
            "pages": pages,
            "orderBy": "newest",
            "results": results,
        }
    }


def nyt_doc(
    doc_id: str, abstract: str, *, headline: str = "Headline", pub_date: str = "2026-09-28T09:00:00+0000"
):
    return {
        "_id": f"nyt://article/{doc_id}",
        "web_url": f"https://www.nytimes.com/2026/09/28/climate/{doc_id}.html",
        "abstract": abstract,
        "snippet": abstract,
        "lead_paragraph": "",
        "pub_date": pub_date,
        "headline": {"main": headline},
        "byline": {"original": "By A Writer"},
        "section_name": "Climate",
        "type_of_material": "News",
        "word_count": 950,
    }


def youtube_video(video_id: str, title: str, *, published: str = "2026-09-28T08:00:00Z") -> dict[str, Any]:
    return {
        "kind": "youtube#video",
        "id": video_id,
        "snippet": {
            "publishedAt": published,
            "channelId": "UCtest",
            "title": title,
            "description": "Subscribe for more.",
            "channelTitle": "Test Channel",
            "defaultAudioLanguage": "en",
        },
        "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "7"},
    }


def youtube_thread(comment_id: str, text: str, *, published: str, video_id: str = "vid1") -> dict[str, Any]:
    return {
        "kind": "youtube#commentThread",
        "id": comment_id,
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {
                "kind": "youtube#comment",
                "id": comment_id,
                "snippet": {
                    "textDisplay": text,
                    "textOriginal": text,
                    "authorDisplayName": "@viewer",
                    "likeCount": 4,
                    "publishedAt": published,
                },
            },
            "totalReplyCount": 2,
        },
    }


def reddit_post(name: str, title: str, *, created: float, selftext: str = "", **extra: Any) -> dict[str, Any]:
    return {
        "kind": "t3",
        "data": {
            "name": name,
            "id": name.removeprefix("t3_"),
            "title": title,
            "selftext": selftext,
            "created_utc": created,
            "permalink": f"/r/nuclear/comments/{name.removeprefix('t3_')}/post/",
            "author": "redditor",
            "subreddit": "nuclear",
            "score": 12,
            "num_comments": 3,
            "upvote_ratio": 0.9,
            "over_18": False,
            **extra,
        },
    }


def reddit_listing(posts: list[dict[str, Any]]) -> dict[str, Any]:
    return {"kind": "Listing", "data": {"children": posts, "after": None}}
