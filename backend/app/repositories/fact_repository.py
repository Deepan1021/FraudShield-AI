from __future__ import annotations

import json
from typing import List

from app.repositories.base import BaseRepository, dumps


class FactRepository(BaseRepository):
    def add_many(self, pk: int, facts: List[dict]) -> None:
        self.conn.executemany(
            """INSERT INTO facts(transaction_pk, seq, predicate, entity, text, kind, source, derivation_rule, parents_json,
               supported_by_json, confidence, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(pk, f["seq"], f["predicate"], f["entity"], f["text"], f["kind"], f["source"], f["derivation_rule"],
              dumps(f["parents"]), dumps(f["supported_by"]), f["confidence"], f["created_at"]) for f in facts])

    def for_transaction(self, pk: int) -> List[dict]:
        rows = self._all("SELECT * FROM facts WHERE transaction_pk = ? ORDER BY seq", (pk,))
        return [{"predicate": r["predicate"], "entity": r["entity"], "text": r["text"], "kind": r["kind"],
                 "source": r["source"], "derivation_rule": r["derivation_rule"], "parents": json.loads(r["parents_json"]),
                 "supported_by": json.loads(r["supported_by_json"]), "confidence": r["confidence"], "seq": r["seq"],
                 "created_at": r["created_at"], "value": True, "args": [r["entity"]]} for r in rows]
