"""Explainable AI: builds the explanation, proof tree and trace graph purely from real inference data."""
from __future__ import annotations

from typing import Dict, List, Set

from app.expert_system.inference.forward_chaining import InferenceRun
from app.expert_system.predicates.registry import PredicateRegistry
from app.expert_system.rules.rulebase import RuleBase


def _proof(text: str, by_text: Dict[str, object], depth: int = 0) -> dict:
    fact = by_text[text]
    node = {"fact": text, "kind": fact.kind, "rule": fact.derivation_rule, "source": fact.source, "children": []}
    if fact.parents and depth < 25:
        node["children"] = [_proof(p, by_text, depth + 1) for p in fact.parents if p in by_text]
    return node


def _supports(run: InferenceRun) -> Dict[str, Set[str]]:
    """Every fact -> union of the facts that supported it across ALL rule firings that derived it."""
    support: Dict[str, Set[str]] = {}
    for e in run.executions:
        support.setdefault(e.derived_fact, set()).update(e.matched_facts)
    return support


def _ancestry(text: str, support: Dict[str, Set[str]], acc: Set[str]) -> Set[str]:
    if text in acc:
        return acc
    acc.add(text)
    for p in support.get(text, ()):
        _ancestry(p, support, acc)
    return acc


def build_graph(run: InferenceRun, decisive: Set[str]) -> dict:
    by_text = run.working_memory.by_text()
    support = _supports(run)
    depth: Dict[str, int] = {}

    def d(text: str) -> int:
        if text in depth:
            return depth[text]
        depth[text] = 1 + max(d(p) for p in support[text]) if support.get(text) else 0
        return depth[text]

    nodes = []
    for f in run.working_memory:
        nodes.append({"id": f.text, "type": "fact", "label": f.predicate, "kind": f.kind,
                      "layer": 2 * d(f.text), "decisive": f.text in decisive})
    edges = []
    for e in run.executions:
        rid = f"{e.rule_id}@{e.seq}"
        layer = 2 * max((d(p) for p in e.matched_facts if p in by_text), default=0) + 1
        is_decisive = e.derived_fact in decisive
        nodes.append({"id": rid, "type": "rule", "label": e.rule_id, "name": e.rule_name, "kind": "rule",
                      "layer": layer, "decisive": is_decisive})
        for p in e.matched_facts:
            edges.append({"from": p, "to": rid, "decisive": is_decisive})
        edges.append({"from": rid, "to": e.derived_fact, "decisive": is_decisive})
    return {"nodes": nodes, "edges": edges, "max_layer": max((n["layer"] for n in nodes), default=0)}


def build_explanation(tx: dict, behaviour: dict, constraints: List[dict], run: InferenceRun, assessment: dict,
                      recommendation: dict, rulebase: RuleBase, registry: PredicateRegistry) -> dict:
    by_text = run.working_memory.by_text()
    level = assessment["risk_level"]
    decisive_text = assessment["decisive_fact"]
    support = _supports(run)
    decisive = _ancestry(decisive_text, support, set()) if decisive_text else set()
    mitigating = level == "LOW" and decisive_text is not None

    leaves = [by_text[t] for t in decisive if not support.get(t) and by_text[t].kind in ("observed", "behavioural", "constraint")]
    leaves.sort(key=lambda f: (-registry.get(f.predicate).weight, f.predicate))
    drivers = [{"fact": f.text, "predicate": f.predicate, "text": registry.get(f.predicate).driver_text,
                "role": "mitigating" if mitigating else "risk_driver", "kind": f.kind,
                "category": registry.get(f.predicate).category} for f in leaves]

    observed = [{"fact": f.text, "text": registry.get(f.predicate).driver_text, "kind": f.kind}
                for f in run.working_memory if f.kind == "observed"]
    derived_evidence = [{"fact": f.text, "text": registry.get(f.predicate).driver_text, "kind": f.kind, "source": f.source}
                        for f in run.working_memory if f.kind in ("behavioural", "constraint")]
    inference = []
    for e in run.executions:
        rule = rulebase.get(e.rule_id)
        inference.append({"step": e.seq, "cycle": e.cycle, "rule_id": e.rule_id, "rule_name": e.rule_name,
                          "statement": f"{' ∧ '.join(e.matched_facts)} → {e.derived_fact}",
                          "formula": e.formula, "new_fact": e.new_fact, "selected_because": e.selected_because,
                          "explanation": rule.explanation if rule else ""})

    decisive_rules = assessment["decisive_rules"]
    decisive_rule_names = [f"{r} ({rulebase.get(r).name})" for r in decisive_rules if rulebase.get(r)]
    why_chain = _proof(decisive_text, by_text) if decisive_text else None

    if decisive_text and not mitigating:
        reasons = "; ".join(d["text"].lower() for d in drivers[:6])
        narrative = (f"Transaction {tx['transaction_id']} is classified {level}. It was derived by {len(run.executions)} rule firings "
                     f"over {run.cycles} inference cycles. Main drivers: {reasons}. "
                     f"The classification {decisive_text} was concluded by {', '.join(decisive_rule_names)}. "
                     f"Recommended action: {recommendation['label']}.")
    elif mitigating:
        narrative = (f"Transaction {tx['transaction_id']} is classified LOW. Mitigating evidence supports approval: "
                     f"{'; '.join(d['text'].lower() for d in drivers)}. Recommended action: {recommendation['label']}.")
    else:
        narrative = (f"Transaction {tx['transaction_id']} is classified LOW. No risk rule produced a conclusion, "
                     f"so no risk indicators were detected. Recommended action: {recommendation['label']}.")

    anomalies = [d for d in behaviour["deviations"] if d["anomalous"]]
    return {
        "question": f"Why is this transaction {level}?",
        "narrative": narrative,
        "risk_level": level,
        "drivers": drivers,
        "observed_evidence": observed,
        "derived_evidence": derived_evidence,
        "behavioural_deviations": anomalies,
        "violated_constraints": [c for c in constraints if not c["passed"]],
        "logical_inference": inference,
        "final_decision": {
            "risk_level": level, "decisive_fact": decisive_text, "decisive_rules": decisive_rules,
            "resolution": assessment["rationale"], "recommendation": recommendation["label"],
            "recommendation_rationale": recommendation["rationale"],
        },
        "why_chain": why_chain,
        "graph": build_graph(run, decisive),
    }
