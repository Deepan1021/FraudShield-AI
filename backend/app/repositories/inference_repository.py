from __future__ import annotations

import json
from typing import List, Optional

from app.repositories.base import BaseRepository, dumps


class InferenceRepository(BaseRepository):
    def save_result(self, pk: int, result: dict, summary: str, schema_version: int, created_at: str) -> int:
        meta = result["metadata"]
        cur = self.conn.execute(
            """INSERT INTO inference_results(evaluation_id, transaction_pk, risk_level, risk_rank, severity_index, summary,
               decisive_rules_json, validation_json, constraints_json, behaviour_json, pipeline_json, explanation_json,
               result_json, processing_time_ms, cycles, firings, engine_version, rulebase_version, app_version,
               schema_version, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (result["evaluation_id"], pk, result["risk_level"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(result["risk_level"]),
             result["severity_index"]["value"], summary, dumps(result["assessment"]["decisive_rules"]), dumps(result["validation"]),
             dumps(result["constraints"]), dumps(result["behavioural_analysis"]), dumps(result["pipeline"]),
             dumps(result["explanation"]), dumps(result), meta["processing_time_ms"], result["inference"]["cycles"],
             result["inference"]["firings"], meta["engine_version"], meta["rulebase_version"], meta["app_version"],
             schema_version, created_at))
        return int(cur.lastrowid)

    def add_executions(self, pk: int, inference_id: int, rulebase_version: str, executions: List[dict]) -> None:
        self.conn.executemany(
            """INSERT INTO rule_executions(transaction_pk, inference_id, seq, cycle, rule_id, rule_version, rulebase_version,
               rule_name, category, priority, severity, bindings_json, matched_facts_json, derived_fact, new_fact,
               conflict_set_size, selected_because) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(pk, inference_id, e["seq"], e["cycle"], e["rule_id"], e["rule_version"], rulebase_version, e["rule_name"],
              e["category"], e["priority"], e["severity"], dumps(e["bindings"]), dumps(e["matched_facts"]),
              e["derived_fact"], int(e["new_fact"]), e["conflict_set_size"], e["selected_because"]) for e in executions])

    def add_recommendation(self, pk: int, inference_id: int, rec: dict, created_at: str) -> None:
        self.conn.execute(
            """INSERT INTO recommendations(transaction_pk, inference_id, action, label, urgency, rationale, escalated_by_json, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (pk, inference_id, rec["action"], rec["label"], rec["urgency"], rec["rationale"], dumps(rec["escalated_by_rules"]), created_at))

    def get_result(self, pk: int) -> Optional[dict]:
        row = self._one("SELECT result_json FROM inference_results WHERE transaction_pk = ?", (pk,))
        return json.loads(row["result_json"]) if row else None

    def executions(self, pk: int) -> List[dict]:
        rows = self._all("SELECT * FROM rule_executions WHERE transaction_pk = ? ORDER BY seq", (pk,))
        for r in rows:
            r["bindings"] = json.loads(r.pop("bindings_json"))
            r["matched_facts"] = json.loads(r.pop("matched_facts_json"))
            r["new_fact"] = bool(r["new_fact"])
        return rows
