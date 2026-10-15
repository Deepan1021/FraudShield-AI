"""Risk classification: resolves the derived risk conclusions into one final level.

Security-first resolution policy (documented, deterministic):
  * Risk conclusions (LowRisk..CriticalRisk) can only come from production rules.
  * The final level is the highest-ranked derived conclusion that is not mitigating evidence.
  * LowRisk is mitigating evidence: it is overridden by ANY MediumRisk/HighRisk/CriticalRisk conclusion.
  * With no risk conclusion at all, the default is LOW ("no risk indicators fired").
  * Decisive rules = rules that derived (or re-derived) the winning conclusion; the first is the
    rule that fired first (conflict-resolution order).
"""
from __future__ import annotations

from typing import List

from app.domain.enums import RiskLevel
from app.expert_system.inference.forward_chaining import InferenceRun
from app.expert_system.predicates.registry import RISK_PREDICATES, PredicateRegistry

POLICY = [
    "Risk conclusions are derived only by production rules.",
    "The highest derived conclusion wins (CRITICAL > HIGH > MEDIUM > LOW).",
    "LowRisk is mitigating evidence and is always overridden by any higher conclusion.",
    "If no conclusion is derived the default is LOW.",
]


def classify(run: InferenceRun, entity: str, registry: PredicateRegistry) -> dict:
    candidates = []
    for pred, level in RISK_PREDICATES.items():
        fact = run.working_memory.get((pred, (entity,)))
        if fact:
            candidates.append({"level": level.value, "fact": fact.text, "derived_by": [fact.derivation_rule, *fact.supported_by],
                               "mitigating": level == RiskLevel.LOW})
    candidates.sort(key=lambda c: RiskLevel(c["level"]).rank, reverse=True)
    if candidates:
        winner = candidates[0]
        level = RiskLevel(winner["level"])
        overridden = [c["level"] for c in candidates[1:]]
        decisive_fact = winner["fact"]
        decisive_rules = [r for r in winner["derived_by"] if r]
        rationale = f"{winner['fact']} is the highest derived risk conclusion."
        if overridden:
            rationale += " Lower conclusions overridden: " + ", ".join(overridden) + "."
    else:
        level, overridden, decisive_fact, decisive_rules = RiskLevel.LOW, [], None, []
        rationale = "No risk conclusion was derived; the default classification is LOW."

    weights = []
    for fact in run.working_memory:
        spec = registry.get(fact.predicate)
        if spec.weight and fact.kind in ("observed", "behavioural", "constraint"):
            weights.append({"fact": fact.text, "predicate": fact.predicate, "weight": spec.weight})
    index = min(100, sum(w["weight"] for w in weights))
    return {
        "risk_level": level.value,
        "decisive_fact": decisive_fact,
        "decisive_rules": decisive_rules,
        "candidates": candidates,
        "overridden_levels": overridden,
        "rationale": rationale,
        "policy": POLICY,
        "severity_index": {
            "name": "Rule-based Risk Severity Index",
            "value": index,
            "max": 100,
            "note": "Transparent sum of fixed indicator weights. It is not a probability and does not determine the decision; the rule engine does.",
            "breakdown": weights,
        },
    }
