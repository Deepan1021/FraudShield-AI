"""Deterministic conflict-resolution strategy.

When several rule instantiations are applicable in the same cycle, exactly one is selected by:
  1. higher rule priority            (evidence normalisation precedes assessment; escalations precede basic conclusions)
  2. higher specificity              (more matched conditions = more specific / composite rule precedence)
  3. higher rule severity            (security-critical conclusions first)
  4. lower rule id                   (stable lexical tie-break)
  5. bindings                        (stable final tie-break)
Final risk resolution (which of several derived risk conclusions wins) is a separate, security-first
policy implemented in classification/classifier.py.
"""
from __future__ import annotations

from typing import List, Tuple

from app.expert_system.inference.matcher import Match

STRATEGY_DESCRIPTION = [
    "1. Highest rule priority fires first.",
    "2. Ties: the more specific rule (more matched conditions) fires first.",
    "3. Ties: the rule with higher severity fires first.",
    "4. Ties: the lower rule id fires first (deterministic).",
]


def sort_key(m: Match):
    r = m.rule
    return (-r.priority, -len(m.facts), -r.severity.rank, r.id, m.bindings)


def select(conflict_set: List[Match]) -> Tuple[Match, str]:
    ordered = sorted(conflict_set, key=sort_key)
    chosen = ordered[0]
    if len(ordered) == 1:
        return chosen, "only applicable rule instantiation"
    runner = ordered[1]
    a, b = chosen.rule, runner.rule
    if a.priority != b.priority:
        reason = f"highest priority ({a.priority} > {b.priority})"
    elif len(chosen.facts) != len(runner.facts):
        reason = f"most specific ({len(chosen.facts)} matched conditions > {len(runner.facts)})"
    elif a.severity != b.severity:
        reason = f"higher severity ({a.severity.value} > {b.severity.value})"
    else:
        reason = f"lowest rule id ({a.id} before {b.id})"
    return chosen, reason
