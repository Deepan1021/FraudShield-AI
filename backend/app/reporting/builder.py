"""Builds a format-neutral report document from a stored analysis result.

Section types: text (str) | kv (list of [key, value]) | list (list of str) | table ({columns, rows}).
The JSON, CSV and PDF exporters and the web report viewer all consume this one structure.
"""
from __future__ import annotations

import json
import uuid
from typing import List

from app.utils.timeutil import utc_now_iso


def _s(v) -> str:
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, (list, tuple)):
        return ", ".join(_s(x) for x in v) or "-"
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def build_report(result: dict, transaction_row: dict, audit: List[dict], report_id: str | None = None) -> dict:
    ex, meta, rec = result["explanation"], result["metadata"], result["recommendation"]
    sec = []
    add = lambda key, title, typ, data: sec.append({"key": key, "title": title, "type": typ, "data": data})  # noqa: E731

    add("executive_summary", "Executive Summary", "text", ex["narrative"])
    add("risk_headline", "Decision", "kv", [["Risk level", result["risk_level"]], ["Recommendation", rec["label"]],
                                            ["Urgency", rec["urgency"]],
                                            ["Rule-based Risk Severity Index", f"{result['severity_index']['value']} / 100 (not a probability)"]])
    add("transaction_information", "Transaction Information", "kv", [
        ["Transaction ID", result["transaction_id"]], ["User ID", result["user_id"]], ["Evaluation ID", result["evaluation_id"]],
        ["Submitted at", meta.get("submitted_at", meta["timestamp"])], ["Decision status", result.get("decision_status")],
        ["Data origin", "Synthetic demonstration data" if result.get("synthetic") else "Analyst submission"]])
    add("input_parameters", "Input Parameters", "kv", [[k.replace("_", " ").capitalize(), v] for k, v in result["input_snapshot"].items()])
    v = result["validation"]
    add("validation", "Validation", "kv", [["Passed", v["passed"]], ["Normalisations", [f"{n['field']}: {n['from']} -> {n['to']}" for n in v["normalisations"]] or "none"]])
    add("constraints", "Constraints", "table", {"columns": ["ID", "Constraint", "Result", "Message"],
        "rows": [[c["id"], c["name"], "PASS" if c["passed"] else "VIOLATED", c["message"]] for c in result["constraints"]]})
    b = result["behavioural_analysis"]
    add("behavioural_analysis", "Behavioural Analysis", "table", {"columns": ["Dimension", "Observed", "Baseline", "Ratio", "Anomalous", "Note"],
        "rows": [[d["label"], _s(d["observed"]), _s(d["baseline"]), _s(d["ratio"]), "Yes" if d["anomalous"] else ("No" if d["evaluated"] else "Not evaluated"), d["message"]] for d in b["deviations"]]})
    add("features", "Extracted Features", "table", {"columns": ["Feature", "Category", "Value", "Description"],
        "rows": [[f["name"], f["category"], _s(f["value"]), f["description"]] for f in result["features"]]})
    add("facts", "Logical Facts", "table", {"columns": ["Fact", "Kind", "Source", "Derived by", "Parents"],
        "rows": [[f["text"], f["kind"], f["source"], _s(f["derivation_rule"]), _s(f["parents"])] for f in result["facts"]]})
    trig_ids = {t["rule_id"] for t in result["triggered_rules"]}
    add("rules_evaluated", "Rules Evaluated", "kv", [["Rules evaluated", len(result["rules_evaluated"])], ["Rules triggered", len(trig_ids)],
                                                      ["Rules not triggered", [r for r in result["rules_evaluated"] if r not in trig_ids]],
                                                      ["Rule base", f"{meta['rulebase_name']} v{meta['rulebase_version']}"]])
    add("rules_triggered", "Rules Triggered", "table", {"columns": ["Rule", "Name", "Category", "Priority", "Fired", "Logic"],
        "rows": [[t["rule_id"], t["rule_name"], t["category"], t["priority"], t["times_fired"], t["formula"]] for t in result["triggered_rules"]]})
    add("trace", "Forward-Chaining Trace", "table", {"columns": ["Step", "Cycle", "Rule", "Inference", "New fact", "Selected because"],
        "rows": [[e["seq"], e["cycle"], e["rule_id"], f"{' AND '.join(e['matched_facts'])} -> {e['derived_fact']}",
                  "Yes" if e["new_fact"] else "No (additional support)", e["selected_because"]] for e in result["reasoning_trace"]]})
    a = result["assessment"]
    add("risk_classification", "Risk Classification", "kv", [["Final risk level", a["risk_level"]], ["Decisive fact", a["decisive_fact"]],
                                                           ["Decisive rules", a["decisive_rules"]], ["Resolution", a["rationale"]],
                                                           ["Candidate conclusions", [c["fact"] for c in a["candidates"]]]])
    add("recommendation", "Recommendation", "kv", [["Action", rec["action"]], ["Label", rec["label"]], ["Rationale", rec["rationale"]],
                                                    ["Escalated by rules", rec["escalated_by_rules"] or "none"]])
    add("explanation_drivers", "Explanation: Risk Drivers", "list", [f"{d['text']} ({d['fact']})" for d in ex["drivers"]] or ["No risk drivers"])
    add("explanation_observed", "Explanation: Observed Evidence", "list", [f"{e['text']} ({e['fact']})" for e in ex["observed_evidence"]] or ["none"])
    add("explanation_derived", "Explanation: Derived Evidence", "list", [f"{e['text']} ({e['fact']})" for e in ex["derived_evidence"]] or ["none"])
    add("explanation_inference", "Explanation: Logical Inference", "list", [f"Step {s['step']} [{s['rule_id']}]: {s['statement']}" for s in ex["logical_inference"]] or ["none"])
    add("audit_metadata", "Audit Metadata", "kv", [
        ["Evaluation ID", result["evaluation_id"]], ["Timestamp", meta["timestamp"]], ["Processing time (ms)", meta["processing_time_ms"]],
        ["Engine version", meta["engine_version"]], ["Rule base version", meta["rulebase_version"]], ["Application version", meta["app_version"]],
        ["Schema version", meta.get("schema_version")], ["Inference cycles", result["inference"]["cycles"]],
        ["Audit events recorded", len(audit)]])
    return {
        "report_id": report_id or "RPT-" + uuid.uuid4().hex[:10].upper(),
        "title": f"FraudShield AI Transaction Risk Report - {result['transaction_id']}",
        "generated_at": utc_now_iso(),
        "transaction_id": result["transaction_id"],
        "risk_level": result["risk_level"],
        "sections": sec,
    }
