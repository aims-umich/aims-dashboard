"""Database connections and migrations.

Runtime code talks to Postgres through psycopg 3 with plain SQL.
SQLAlchemy is only used by Alembic to run migrations.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool, ConnectionPool

BACKEND_DIR = Path(__file__).resolve().parent.parent
# Shipped inside the package so migrations work the same from a checkout and from an installed wheel.
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

# Channel the ingest service notifies after inserting scorable segments.
NEW_SEGMENTS_CHANNEL = "new_segments"


def sqlalchemy_url(database_url: str) -> str:
    """Point SQLAlchemy at the psycopg 3 driver."""
    for prefix in ("postgresql://", "postgres://"):
        if database_url.startswith(prefix):
            return "postgresql+psycopg://" + database_url[len(prefix) :]
    return database_url


def connect(database_url: str, *, autocommit: bool = False) -> psycopg.Connection:
    return psycopg.connect(database_url, autocommit=autocommit, row_factory=dict_row)


def sync_pool(database_url: str, *, min_size: int = 1, max_size: int = 4) -> ConnectionPool:
    return ConnectionPool(
        database_url,
        min_size=min_size,
        max_size=max_size,
        kwargs={"row_factory": dict_row},
        open=True,
    )


async def async_pool(database_url: str, *, min_size: int = 1, max_size: int = 4) -> AsyncConnectionPool:
    pool = AsyncConnectionPool(
        database_url,
        min_size=min_size,
        max_size=max_size,
        kwargs={"row_factory": dict_row},
        open=False,
    )
    await pool.open(wait=True)
    return pool


def migrate(database_url: str, revision: str = "head") -> None:
    from alembic import command
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["database_url"] = database_url
    command.upgrade(config, revision)
