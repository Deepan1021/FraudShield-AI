from __future__ import annotations

import json
from typing import Any, List, Optional, Tuple

from app.core.version import APP_VERSION, ENGINE_VERSION
from app.repositories.base import BaseRepository, dumps, like_pattern
from app.utils.timeutil import utc_now_iso


class AuditRepository(BaseRepository):
    def add(self, event_type: str, description: str, actor: str = "system", transaction_id: Optional[str] = None,
            risk_level: Optional[str] = None, rule_id: Optional[str] = None, rulebase_version: str = "",
            timestamp: Optional[str] = None, metadata: Optional[dict] = None) -> None:
        self.conn.execute(
            """INSERT INTO audit_logs(timestamp, event_type, actor, transaction_id, risk_level, rule_id, description,
               metadata_json, engine_version, rulebase_version, app_version) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (timestamp or utc_now_iso(), event_type, actor, transaction_id, risk_level, rule_id, description,
             dumps(metadata) if metadata else None, ENGINE_VERSION, rulebase_version, APP_VERSION))

    def search(self, q: Optional[str] = None, event_type: Optional[str] = None, risk: Optional[str] = None,
               transaction_id: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None,
               page: int = 1, page_size: int = 50) -> Tuple[List[dict], int]:
        where: List[str] = []
        params: List[Any] = []
        if q:
            where.append("(description LIKE ? ESCAPE '\\' OR transaction_id LIKE ? ESCAPE '\\' OR actor LIKE ? ESCAPE '\\')")
            params += [like_pattern(q)] * 3
        if event_type:
            where.append("event_type = ?"); params.append(event_type)
        if risk:
            where.append("risk_level = ?"); params.append(risk)
        if transaction_id:
            where.append("transaction_id = ?"); params.append(transaction_id)
        if date_from:
            where.append("date(timestamp) >= date(?)"); params.append(date_from)
        if date_to:
            where.append("date(timestamp) <= date(?)"); params.append(date_to)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        page, page_size = max(1, page), max(1, min(200, page_size))
        total = int(self._scalar("SELECT COUNT(*) FROM audit_logs" + clause, params))
        rows = self._all("SELECT * FROM audit_logs" + clause + " ORDER BY timestamp DESC, id DESC LIMIT ? OFFSET ?",
                         params + [page_size, (page - 1) * page_size])
        for r in rows:
            r["metadata"] = json.loads(r.pop("metadata_json")) if r.get("metadata_json") else None
        return rows, total

    def event_types(self) -> List[str]:
        return [r["event_type"] for r in self._all("SELECT DISTINCT event_type FROM audit_logs ORDER BY event_type")]

    def for_transaction(self, transaction_id: str) -> List[dict]:
        rows, _ = self.search(transaction_id=transaction_id, page_size=200)
        return rows
