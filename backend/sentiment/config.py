"""Runtime configuration, read from environment variables (and an optional .env file).

Every service reads the same settings object; each one only touches the fields it needs.
Secrets are only ever read from the environment and are never logged.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ALL_SOURCES = ("bluesky", "mastodon", "youtube", "reddit", "guardian", "nyt")


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Shared
    database_url: str = "postgresql://postgres@localhost:5432/dashboard"
    environment: str = "development"
    log_level: str = "INFO"
    log_format: str = "json"
    sentry_dsn: SecretStr | None = None
    # Healthchecks.io project ping key; each source pings https://hc-ping.com/<key>/<slug>.
    healthchecks_ping_key: SecretStr | None = None
    healthchecks_slug_prefix: str = "dashboard"

    # Ingest
    enabled_sources: str = "bluesky,mastodon,youtube,guardian,nyt"
    user_agent: str = "aims-sentiment-dashboard/1.0 (+https://dashboard.aims-umich.com/about)"

    bluesky_jetstream_urls: str = (
        "wss://jetstream2.us-east.bsky.network/subscribe,"
        "wss://jetstream1.us-east.bsky.network/subscribe,"
        "wss://jetstream1.us-west.bsky.network/subscribe,"
        "wss://jetstream2.us-west.bsky.network/subscribe"
    )
    bluesky_appview_url: str = "https://public.api.bsky.app"
    bluesky_metrics_interval_s: int = 600
    bluesky_metrics_window_days: int = 7

    mastodon_instances: str = "mastodon.social"
    mastodon_hashtags: str = (
        "nuclear,nuclearpower,nuclearenergy,nuclearfusion,fission,fusionenergy,smr,uranium,"
        "radioactivewaste,nuclearwaste,atomkraft,chernobyl,fukushima"
    )
    # Optional per-instance tokens ("mastodon.social=TOKEN,fosstodon.org=TOKEN").
    # Only needed on instances that disable unauthenticated hashtag timelines.
    mastodon_access_tokens: SecretStr | None = None
    mastodon_interval_s: int = 120

    youtube_api_key: SecretStr | None = None
    youtube_query: str = '"nuclear energy"|"nuclear power"|"nuclear reactor"|"nuclear plant"|"nuclear fusion"'
    youtube_search_interval_s: int = 1800
    youtube_comments_interval_s: int = 1800
    youtube_track_days: int = 14
    youtube_max_tracked_videos: int = 40
    youtube_region_code: str = "US"

    reddit_client_id: SecretStr | None = None
    reddit_client_secret: SecretStr | None = None
    reddit_user_agent: str = "linux:edu.umich.aims.dashboard:v1.0 (by /u/aims-umich)"
    reddit_query: str = '"nuclear energy" OR "nuclear power" OR "nuclear plant" OR "nuclear reactor" OR SMR'
    reddit_subreddits: str = "nuclear,NuclearPower,energy,fusion,climate"
    reddit_interval_s: int = 120
    reddit_compliance_interval_s: int = 86400

    guardian_api_key: SecretStr | None = None
    guardian_section: str = "us-news"
    guardian_query: str = (
        '"nuclear power" OR "nuclear energy" OR "nuclear plant" OR "nuclear reactor" OR '
        '"nuclear waste" OR "nuclear fusion" OR "small modular reactor" OR "nuclear industry" OR '
        '"nuclear safety" OR "nuclear regulatory"'
    )
    guardian_interval_s: int = 1800

    nyt_api_key: SecretStr | None = None
    nyt_query: str = "nuclear energy OR nuclear power OR nuclear plant OR nuclear reactor"
    nyt_interval_s: int = 3600

    # Scorer
    scorer_backend: str = "local_hf"
    scorer_model: str = "kumo24/bert-sentiment-nuclear"
    scorer_revision: str = "883de0dd5f6a1a4a4a5f9e5af9b54863ca44cd57"
    # Segments claimed (and committed) per transaction, and texts per model forward pass.
    scorer_batch_size: int = 16
    scorer_micro_batch: int = 1
    scorer_threads: int = 1
    scorer_max_length: int = 512
    scorer_poll_interval_s: float = 30.0
    # Only used by the Modal backend (Gemma on a serverless GPU, see the deployment plan).
    modal_endpoint_url: str | None = None
    modal_token: SecretStr | None = None
    modal_timeout_s: float = 120.0

    # API
    api_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    api_cache_ttl_s: float = 30.0
    api_rate_limit_per_min: int = 600

    @property
    def sources(self) -> list[str]:
        names = split_csv(self.enabled_sources.lower())
        unknown = sorted(set(names) - set(ALL_SOURCES))
        if unknown:
            raise ValueError(f"Unknown sources in ENABLED_SOURCES: {', '.join(unknown)}")
        return names

    @property
    def cors_origins(self) -> list[str]:
        return split_csv(self.api_cors_origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()
