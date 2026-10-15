"""Read-side service for transactions, facts, rule traces and explanations."""
from __future__ import annotations

from typing import List, Optional

from app.core.errors import NotFoundError
from app.database.database import Database


class TransactionService:
    def __init__(self, db: Database):
        self.db = db

    def _row(self, uow, transaction_id: str) -> dict:
        row = uow.transactions.get(transaction_id.strip().upper())
        if not row:
            raise NotFoundError(f"Transaction {transaction_id} was not found.", field="transaction_id")
        return row

    def list(self, **filters) -> dict:
        items, total = self.db.read().transactions.search(**filters)
        page, size = max(1, filters.get("page", 1)), max(1, min(100, filters.get("page_size", 20)))
        return {"items": items, "total": total, "page": page, "page_size": size, "pages": max(1, -(-total // size))}

    def detail(self, transaction_id: str) -> dict:
        uow = self.db.read()
        row = self._row(uow, transaction_id)
        result = uow.inference.get_result(row["pk"])
        return {"transaction": row, "result": result, "audit": uow.audit.for_transaction(row["transaction_id"])}

    def result(self, transaction_id: str) -> dict:
        uow = self.db.read()
        row = self._row(uow, transaction_id)
        return uow.inference.get_result(row["pk"])

    def facts(self, transaction_id: str) -> List[dict]:
        uow = self.db.read()
        return uow.facts.for_transaction(self._row(uow, transaction_id)["pk"])

    def rules(self, transaction_id: str) -> dict:
        result = self.result(transaction_id)
        return {"evaluated": result["rules_evaluated"], "triggered": result["triggered_rules"]}

    def trace(self, transaction_id: str) -> dict:
        uow = self.db.read()
        row = self._row(uow, transaction_id)
        result = uow.inference.get_result(row["pk"])
        return {"transaction_id": row["transaction_id"], "executions": uow.inference.executions(row["pk"]),
                "graph": result["explanation"]["graph"], "inference": result["inference"], "pipeline": result["pipeline"]}

    def explanation(self, transaction_id: str) -> dict:
        result = self.result(transaction_id)
        return {"transaction_id": result["transaction_id"], "risk_level": result["risk_level"],
                "recommendation": result["recommendation"], "explanation": result["explanation"]}
