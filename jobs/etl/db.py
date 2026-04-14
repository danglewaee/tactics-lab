from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Database:
    database_url: str

    def __enter__(self) -> "Database":
        import psycopg
        from psycopg.types.json import Jsonb

        self._jsonb = Jsonb
        self.connection = psycopg.connect(self.database_url)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()
        self.connection.close()

    def jsonb(self, value: Any) -> Any:
        return self._jsonb(value or {})

    def fetch_value(self, sql: str, params: tuple[Any, ...]) -> Any:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            if row is None:
                return None
            return row[0]

    def execute(self, sql: str, params: tuple[Any, ...]) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
