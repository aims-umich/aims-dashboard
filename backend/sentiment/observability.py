"""Structured logging, Sentry, and Healthchecks.io heartbeats."""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

import httpx

from sentiment.config import Settings

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup(settings: Settings, service: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(settings.log_level.upper())
    # httpx logs every request URL at INFO, and some URLs carry API keys as query parameters.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn.get_secret_value(),
            environment=settings.environment,
            server_name=service,
            traces_sample_rate=0.0,
            send_default_pii=False,
        )


class Heartbeat:
    """Pings a Healthchecks.io check by slug; a no-op when no ping key is configured."""

    def __init__(self, settings: Settings, name: str) -> None:
        key = settings.healthchecks_ping_key
        self._url = (
            f"https://hc-ping.com/{key.get_secret_value()}/{settings.healthchecks_slug_prefix}-{name}"
            if key
            else None
        )
        self._log = logging.getLogger(f"heartbeat.{name}")

    async def ping(self, *, failed: bool = False, message: str = "") -> None:
        if not self._url:
            return
        url = self._url + ("/fail" if failed else "")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(url, params={"create": 1}, content=message[:10_000].encode())
        except httpx.HTTPError as exc:
            self._log.warning("heartbeat failed", extra={"error": type(exc).__name__})

    def ping_sync(self, *, failed: bool = False, message: str = "") -> None:
        if not self._url:
            return
        url = self._url + ("/fail" if failed else "")
        try:
            httpx.post(url, params={"create": 1}, content=message[:10_000].encode(), timeout=10)
        except httpx.HTTPError as exc:
            self._log.warning("heartbeat failed", extra={"error": type(exc).__name__})
