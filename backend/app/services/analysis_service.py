"""TransactionAnalysisService: orchestrates validation, baseline lookup, inference and atomic persistence."""
from __future__ import annotations

import sqlite3
import time
from typing import Mapping, Optional

from app.core.errors import DuplicateTransactionError, TransactionValidationError
from app.core.logging import get_logger
from app.database.database import Database
from app.database.migrations import LATEST_SCHEMA_VERSION
from app.pipeline import AnalysisPipeline
from app.utils.timeutil import utc_now_iso

STATUS_BY_ACTION = {
    "APPROVE": "APPROVED", "REQUEST_MFA": "PENDING_VERIFICATION",
    "TEMPORARILY_BLOCK": "BLOCKED", "FLAG_FOR_ANALYST_REVIEW": "UNDER_REVIEW",
}
_log = get_logger("inference")


class AnalysisService:
    def __init__(self, db: Database, pipeline: AnalysisPipeline):
        self.db = db
        self.pipeline = pipeline

    def analyze(self, raw: Mapping, actor: str = "analyst", is_synthetic: bool = False,
                submitted_at: Optional[str] = None) -> dict:
        rb_version = self.pipeline.rulebase.version
        user_hint = raw.get("user_id") if isinstance(raw, Mapping) else None
        user_hint = user_hint.strip().upper() if isinstance(user_hint, str) else None
        baseline = self.db.read().users.get_baseline(user_hint) if user_hint else None
        try:
            result = self.pipeline.analyze(raw, baseline)
        except TransactionValidationError as exc:
            self._audit_failure("VALIDATION_REJECTED", f"Input rejected: {exc.message}", actor, raw, rb_version, exc.field)
            raise
        tid = result["transaction_id"]
        submitted_at = submitted_at or utc_now_iso()
        if self.db.read().transactions.exists(tid):
            self._audit_failure("DUPLICATE_REJECTED", f"Duplicate transaction id {tid} rejected", actor, raw, rb_version)
            raise DuplicateTransactionError(f"Transaction {tid} has already been analysed.", field="transaction_id")

        snapshot = result["input_snapshot"]
        level, rec = result["risk_level"], result["recommendation"]
        drivers = result["explanation"]["drivers"]
        summary = "; ".join(d["text"] for d in drivers[:2]) if drivers else "No risk indicators detected"
        result["metadata"]["schema_version"] = LATEST_SCHEMA_VERSION
        result["metadata"]["submitted_at"] = submitted_at
        result["decision_status"] = STATUS_BY_ACTION[rec["action"]]
        result["synthetic"] = is_synthetic
        try:
            with self.db.unit_of_work() as uow:
                t0 = time.perf_counter()
                uow.users.upsert(snapshot["user_id"], is_synthetic=is_synthetic, now=submitted_at)
                pk = uow.transactions.insert(snapshot, submitted_at, is_synthetic, result["decision_status"])
                uow.transactions.add_features(pk, result["features"])
                uow.facts.add_many(pk, result["facts"])
                result["pipeline"].append({"key": "persistence", "label": "Persist evidence and audit trail", "status": "COMPLETED",
                                           "duration_ms": round((time.perf_counter() - t0) * 1000, 3),
                                           "detail": f"{len(result['facts'])} facts, {len(result['reasoning_trace'])} rule executions"})
                inf_id = uow.inference.save_result(pk, result, summary, LATEST_SCHEMA_VERSION, submitted_at)
                uow.inference.add_executions(pk, inf_id, rb_version, result["reasoning_trace"])
                uow.inference.add_recommendation(pk, inf_id, rec, submitted_at)
                uow.audit.add("TRANSACTION_RECEIVED", f"Transaction {tid} received for analysis", actor, tid,
                              rulebase_version=rb_version, timestamp=submitted_at,
                              metadata={"evaluation_id": result["evaluation_id"], "channel": snapshot.get("channel")})
                uow.audit.add("ANALYSIS_COMPLETED", f"Transaction {tid} classified {level} by {len(result['reasoning_trace'])} rule firings",
                              actor, tid, level, (result["assessment"]["decisive_rules"] or [None])[0], rb_version, submitted_at,
                              metadata={"evaluation_id": result["evaluation_id"], "decisive_rules": result["assessment"]["decisive_rules"],
                                        "processing_time_ms": result["metadata"]["processing_time_ms"]})
                uow.audit.add("RECOMMENDATION_ISSUED", f"Recommendation for {tid}: {rec['label']}", "system", tid, level,
                              None, rb_version, submitted_at, metadata={"action": rec["action"]})
                if level in ("HIGH", "CRITICAL"):
                    uow.audit.add("HIGH_RISK_ALERT", f"{level} risk alert raised for {tid}", "system", tid, level,
                                  (result["assessment"]["decisive_rules"] or [None])[0], rb_version, submitted_at)
        except sqlite3.IntegrityError as exc:
            raise DuplicateTransactionError(f"Transaction {tid} has already been analysed.", field="transaction_id") from exc
        _log.info("evaluation=%s transaction=%s risk=%s action=%s firings=%s ms=%s", result["evaluation_id"], tid, level,
                  rec["action"], len(result["reasoning_trace"]), result["metadata"]["processing_time_ms"])
        return result

    def _audit_failure(self, event: str, description: str, actor: str, raw, rb_version: str, field: Optional[str] = None) -> None:
        tid = raw.get("transaction_id") if isinstance(raw, Mapping) else None
        try:
            with self.db.unit_of_work() as uow:
                uow.audit.add(event, description, actor, tid if isinstance(tid, str) and len(tid) <= 60 else None,
                              rulebase_version=rb_version, metadata={"field": field} if field else None)
        except Exception as exc:  # auditing must never mask the original error
            get_logger().error("Could not write audit event %s: %s", event, exc)
