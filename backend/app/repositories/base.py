from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable, List, Optional


class BaseRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _one(self, sql: str, params: Iterable[Any] = ()) -> Optional[dict]:
        row = self.conn.execute(sql, tuple(params)).fetchone()
        return dict(row) if row else None

    def _all(self, sql: str, params: Iterable[Any] = ()) -> List[dict]:
        return [dict(r) for r in self.conn.execute(sql, tuple(params)).fetchall()]

    def _scalar(self, sql: str, params: Iterable[Any] = ()):
        row = self.conn.execute(sql, tuple(params)).fetchone()
        return row[0] if row else None


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)


def like_pattern(term: str) -> str:
    """Escape LIKE wildcards in user input (use with ESCAPE '\\')."""
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
