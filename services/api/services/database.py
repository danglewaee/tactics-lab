from __future__ import annotations

from collections.abc import Sequence
from typing import Any

class DatabaseUnavailableError(RuntimeError):
    pass


def query_all(sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ModuleNotFoundError as exc:
        raise DatabaseUnavailableError("psycopg is not installed.") from exc

    from app.config import get_settings

    settings = get_settings()
    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())
    except Exception as exc:
        raise DatabaseUnavailableError("Database query failed.") from exc


def query_one(sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ModuleNotFoundError as exc:
        raise DatabaseUnavailableError("psycopg is not installed.") from exc

    from app.config import get_settings

    settings = get_settings()
    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
                return dict(row) if row is not None else None
    except Exception as exc:
        raise DatabaseUnavailableError("Database query failed.") from exc
