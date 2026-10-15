"""Recommendation engine (separate from the classifier)."""
from __future__ import annotations

from typing import List

from app.domain.enums import RecommendationAction, RiskLevel

POLICY = {
    RiskLevel.LOW: RecommendationAction.APPROVE,
    RiskLevel.MEDIUM: RecommendationAction.REQUEST_MFA,
    RiskLevel.HIGH: RecommendationAction.TEMPORARILY_BLOCK,
    RiskLevel.CRITICAL: RecommendationAction.FLAG_FOR_ANALYST_REVIEW,
}
LABELS = {
    RecommendationAction.APPROVE: "Approve transaction",
    RecommendationAction.REQUEST_MFA: "Request additional identity verification (MFA)",
    RecommendationAction.TEMPORARILY_BLOCK: "Temporarily block transaction",
    RecommendationAction.FLAG_FOR_ANALYST_REVIEW: "Flag for cyber analyst review",
}
URGENCY = {RiskLevel.LOW: "ROUTINE", RiskLevel.MEDIUM: "STEP_UP", RiskLevel.HIGH: "IMMEDIATE", RiskLevel.CRITICAL: "URGENT"}
# A fired rule carrying this tag escalates the action to analyst review (only ever upgrades).
ESCALATION_TAG = "analyst_escalation"


def recommend(level: RiskLevel, executions: List[dict]) -> dict:
    action = POLICY[level]
    escalated_by = sorted({e["rule_id"] for e in executions if ESCALATION_TAG in e.get("tags", [])})
    rationale = f"Policy: {level.value} risk maps to {LABELS[action].lower()}."
    if escalated_by and action.strength < RecommendationAction.FLAG_FOR_ANALYST_REVIEW.strength:
        action = RecommendationAction.FLAG_FOR_ANALYST_REVIEW
        rationale = f"Escalated to analyst review by rule(s) {', '.join(escalated_by)} (tag '{ESCALATION_TAG}')."
    else:
        escalated_by = []
    return {"action": action.value, "label": LABELS[action], "urgency": URGENCY[level],
            "rationale": rationale, "escalated_by_rules": escalated_by}
