from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from app.repositories.base import BaseRepository, dumps, like_pattern

SORT_COLUMNS = {
    "submitted_at": "t.submitted_at", "amount": "t.amount", "transaction_id": "t.transaction_id",
    "user_id": "t.user_id", "risk_rank": "i.risk_rank", "severity_index": "i.severity_index",
}
LIST_SELECT = """
SELECT t.id AS pk, t.transaction_id, t.user_id, t.amount, t.currency, t.transaction_time, t.device_trust, t.device_id,
       t.location, t.login_behavior, t.transaction_frequency, t.account_activity, t.channel, t.status,
       t.is_synthetic, t.submitted_at, i.evaluation_id, i.risk_level, i.severity_index, i.summary,
       i.processing_time_ms, r.action AS recommendation_action, r.label AS recommendation_label
FROM transactions t
LEFT JOIN inference_results i ON i.transaction_pk = t.id
LEFT JOIN recommendations r ON r.transaction_pk = t.id
"""


class TransactionRepository(BaseRepository):
    def exists(self, transaction_id: str) -> bool:
        return self._one("SELECT 1 FROM transactions WHERE transaction_id = ?", (transaction_id,)) is not None

    def insert(self, snapshot: dict, submitted_at: str, is_synthetic: bool = False, status: str = "ANALYZED") -> int:
        cur = self.conn.execute(
            """INSERT INTO transactions(transaction_id, user_id, amount, currency, channel, transaction_time, device_trust,
               device_id, location, login_behavior, transaction_frequency, account_activity, merchant_category, session_id,
               input_snapshot_json, is_synthetic, status, submitted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (snapshot["transaction_id"], snapshot["user_id"], snapshot["amount"], snapshot["currency"], snapshot.get("channel"),
             snapshot["transaction_time"], snapshot["device_trust"], snapshot.get("device_id"), snapshot["location"],
             snapshot["login_behavior"], snapshot["transaction_frequency"], snapshot["account_activity"],
             snapshot.get("merchant_category"), snapshot.get("session_id"), dumps(snapshot), int(is_synthetic), status, submitted_at))
        return int(cur.lastrowid)

    def get_pk(self, transaction_id: str) -> Optional[int]:
        row = self._one("SELECT id FROM transactions WHERE transaction_id = ?", (transaction_id,))
        return row["id"] if row else None

    def get(self, transaction_id: str) -> Optional[dict]:
        return self._one(LIST_SELECT + " WHERE t.transaction_id = ?", (transaction_id,))

    def add_features(self, pk: int, features: List[dict]) -> None:
        self.conn.executemany(
            "INSERT INTO transaction_features(transaction_pk, name, category, kind, value_json, description) VALUES (?,?,?,?,?,?)",
            [(pk, f["name"], f["category"], f["kind"], dumps(f["value"]), f["description"]) for f in features])

    def get_features(self, pk: int) -> List[dict]:
        rows = self._all("SELECT name, category, kind, value_json, description FROM transaction_features WHERE transaction_pk = ? ORDER BY id", (pk,))
        return [{"name": r["name"], "category": r["category"], "kind": r["kind"], "value": json.loads(r["value_json"]),
                 "description": r["description"]} for r in rows]

    def count(self) -> int:
        return int(self._scalar("SELECT COUNT(*) FROM transactions"))

    def search(self, q: Optional[str] = None, risk: Optional[List[str]] = None, recommendation: Optional[str] = None,
               location: Optional[str] = None, device_trust: Optional[str] = None, rule: Optional[str] = None,
               status: Optional[str] = None, user_id: Optional[str] = None, date_from: Optional[str] = None,
               date_to: Optional[str] = None, sort: str = "submitted_at", order: str = "desc",
               page: int = 1, page_size: int = 20) -> Tuple[List[dict], int]:
        where: List[str] = []
        params: List[Any] = []
        if q:
            where.append("(t.transaction_id LIKE ? ESCAPE '\\' OR t.user_id LIKE ? ESCAPE '\\')")
            params += [like_pattern(q), like_pattern(q)]
        if risk:
            where.append(f"i.risk_level IN ({','.join('?' * len(risk))})")
            params += risk
        if recommendation:
            where.append("r.action = ?"); params.append(recommendation)
        if location:
            where.append("t.location LIKE ? ESCAPE '\\'"); params.append(like_pattern(location))
        if device_trust:
            where.append("t.device_trust = ?"); params.append(device_trust)
        if user_id:
            where.append("t.user_id = ?"); params.append(user_id)
        if status:
            where.append("t.status = ?"); params.append(status)
        if rule:
            where.append("EXISTS (SELECT 1 FROM rule_executions re WHERE re.transaction_pk = t.id AND re.rule_id = ?)")
            params.append(rule)
        if date_from:
            where.append("date(t.submitted_at) >= date(?)"); params.append(date_from)
        if date_to:
            where.append("date(t.submitted_at) <= date(?)"); params.append(date_to)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        column = SORT_COLUMNS.get(sort, "t.submitted_at")
        direction = "ASC" if str(order).lower() == "asc" else "DESC"
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        total = int(self._scalar("SELECT COUNT(*) FROM transactions t LEFT JOIN inference_results i ON i.transaction_pk = t.id "
                                 "LEFT JOIN recommendations r ON r.transaction_pk = t.id" + clause, params))
        rows = self._all(LIST_SELECT + clause + f" ORDER BY {column} {direction}, t.id DESC LIMIT ? OFFSET ?",
                         params + [page_size, (page - 1) * page_size])
        return rows, total
