"""Collector jobs, grouped by the source name used in ENABLED_SOURCES."""

from __future__ import annotations

from sentiment.ingest.base import Job
from sentiment.ingest.sources.bluesky import BlueskyMetricsJob, BlueskyStreamJob
from sentiment.ingest.sources.guardian import GuardianJob
from sentiment.ingest.sources.mastodon import MastodonJob
from sentiment.ingest.sources.nyt import NytJob
from sentiment.ingest.sources.reddit import RedditComplianceJob, RedditJob
from sentiment.ingest.sources.youtube import YouTubeCommentsJob, YouTubeSearchJob

JOBS_BY_SOURCE: dict[str, list[type[Job]]] = {
    "bluesky": [BlueskyStreamJob, BlueskyMetricsJob],
    "mastodon": [MastodonJob],
    "youtube": [YouTubeSearchJob, YouTubeCommentsJob],
    "reddit": [RedditJob, RedditComplianceJob],
    "guardian": [GuardianJob],
    "nyt": [NytJob],
}

# Which platform each job's freshness counts toward on the status page.
PLATFORM_BY_JOB: dict[str, str] = {job.name: job.platform for jobs in JOBS_BY_SOURCE.values() for job in jobs}
