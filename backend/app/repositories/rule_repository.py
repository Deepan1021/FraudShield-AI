from __future__ import annotations

import json
from typing import List

from app.repositories.base import BaseRepository, dumps


class RuleRepository(BaseRepository):
    def sync(self, rulebase_version: str, rules: List[dict]) -> int:
        """Persist the rules of a rule base version (idempotent). Returns the number of rows inserted."""
        inserted = 0
        for r in rules:
            cur = self.conn.execute(
                """INSERT OR IGNORE INTO rules(rule_id, rulebase_version, name, category, priority, severity, status, version,
                   description, definition_json) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (r["id"], rulebase_version, r["name"], r["category"], r["priority"], r["severity"], r["status"], r["version"],
                 r["description"], dumps(r)))
            inserted += cur.rowcount
        return inserted

    def list(self, rulebase_version: str) -> List[dict]:
        rows = self._all("SELECT definition_json FROM rules WHERE rulebase_version = ? ORDER BY rule_id", (rulebase_version,))
        return [json.loads(r["definition_json"]) for r in rows]

    def versions(self) -> List[str]:
        return [r["rulebase_version"] for r in self._all("SELECT DISTINCT rulebase_version FROM rules ORDER BY rulebase_version")]
