"""What the dashboard knows about each platform: display name, scored document kinds, engagement fields."""

from __future__ import annotations

from dataclasses import dataclass

from sentiment.config import Settings


@dataclass(frozen=True, slots=True)
class Platform:
    key: str
    name: str
    # Document kinds whose text is scored (a YouTube video is context; its comments are scored).
    scored_kinds: tuple[str, ...]
    # Numeric keys in documents.metrics worth averaging, with display labels.
    engagement: tuple[tuple[str, str], ...]
    source_jobs: tuple[str, ...]
    unit: str  # What one scored item is called on the page.


PLATFORMS: dict[str, Platform] = {
    p.key: p
    for p in (
        Platform(
            "bluesky",
            "Bluesky",
            ("post",),
            (("likes", "Likes"), ("reposts", "Reposts"), ("replies", "Replies")),
            ("bluesky", "bluesky_metrics"),
            "posts",
        ),
        Platform(
            "mastodon",
            "Mastodon",
            ("post",),
            (("likes", "Favourites"), ("reposts", "Boosts"), ("replies", "Replies")),
            ("mastodon",),
            "posts",
        ),
        Platform(
            "reddit",
            "Reddit",
            ("post",),
            (("score", "Score"), ("comments", "Comments")),
            ("reddit", "reddit_compliance"),
            "posts",
        ),
        Platform(
            "youtube",
            "YouTube",
            ("comment",),
            (("likes", "Likes"), ("replies", "Replies")),
            ("youtube", "youtube_comments"),
            "comments",
        ),
        Platform("guardian", "The Guardian", ("article",), (), ("guardian",), "sentences"),
        Platform("nyt", "New York Times", ("article",), (), ("nyt",), "articles"),
    )
}


def enabled_platforms(settings: Settings) -> list[Platform]:
    enabled = set(settings.sources)
    return [p for key, p in PLATFORMS.items() if key in enabled]
