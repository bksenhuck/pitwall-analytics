"""
Database query helpers.

Thin wrappers around get_db_connection that eliminate the repetitive
cursor / execute / fetch boilerplate for single-query reads.

Use db_fetchone / db_fetchall for simple, self-contained queries.
For blocks that run multiple queries in the same connection (e.g. loops,
nested queries) keep using get_db_connection directly.
"""
from typing import Any, List, Optional

from backend.db.session import get_db_connection


def db_fetchone(
    season: int,
    query: str,
    params: tuple = (),
) -> Optional[dict]:
    """Execute *query* and return the first row as a plain dict, or None."""
    with get_db_connection(season) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def db_fetchall(
    season: int,
    query: str,
    params: tuple = (),
) -> List[dict]:
    """Execute *query* and return all rows as a list of plain dicts."""
    with get_db_connection(season) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
