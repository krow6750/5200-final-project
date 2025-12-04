import os
from contextlib import contextmanager
from typing import Any, Iterable, Optional, Sequence, Tuple

import psycopg2
from psycopg2.extensions import connection as PGConnection


def get_database_url() -> str:
    """
    Pulls the connection string from env.
    Falls back to localhost Postgres with a database named cs2_esports.
    """
    return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cs2_esports")


@contextmanager
def get_conn() -> Iterable[PGConnection]:
    # Tiny wrapper so every call auto-commits/rolls back; keeps the app code uncluttered.
    conn = psycopg2.connect(get_database_url())
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(query: str, params: Optional[Sequence[Any]] = None) -> Sequence[Tuple]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchall()


def execute(query: str, params: Optional[Sequence[Any]] = None) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())


def fetch_one(query: str, params: Optional[Sequence[Any]] = None) -> Optional[Tuple]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchone()


def execute_returning(query: str, params: Optional[Sequence[Any]] = None) -> Optional[Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            row = cur.fetchone()
            return row[0] if row else None
