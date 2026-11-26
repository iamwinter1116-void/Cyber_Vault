"""PostgreSQL connection pool factory (no ORM)."""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool


def create_pool(
    dsn: str,
    *,
    min_size: int = 1,
    max_size: int = 10,
) -> ConnectionPool[psycopg.Connection[tuple[object, ...]]]:
    """Create an open psycopg connection pool for the given DSN."""
    if not dsn:
        raise ValueError("ABH_DB_DSN must be non-empty")
    return ConnectionPool(conninfo=dsn, min_size=min_size, max_size=max_size, open=True)


@contextmanager
def transaction(
    pool: ConnectionPool[psycopg.Connection[tuple[object, ...]]],
) -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    """Yield a connection wrapped in a single database transaction."""
    with pool.connection() as conn, conn.transaction():
        yield conn
