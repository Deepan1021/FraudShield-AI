"""Rule base loading and validation. Rules are parsed from JSON by a safe structural parser."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from app.core.errors import RuleBaseError
from app.domain.enums import RiskLevel
from app.expert_system.predicates.registry import PredicateRegistry, default_registry
from app.expert_system.rules.model import Condition, Rule, is_variable

DEFAULT_RULEBASE_PATH = Path(__file__).with_name("rulebase_v1.json")
_REQUIRED = ("id", "name", "category", "priority", "severity", "if", "then", "description", "explanation")


@dataclass
class RuleBase:
    name: str
    version: str
    rules: List[Rule]

    @property
    def active_rules(self) -> List[Rule]:
        return [r for r in self.rules if r.active]

    def get(self, rule_id: str) -> Optional[Rule]:
        return next((r for r in self.rules if r.id == rule_id), None)

    def dependencies(self) -> List[dict]:
        """Rule-level dependency edges: rule A feeds rule B when A's consequent is an antecedent of B."""
        edges = []
        for a in self.active_rules:
            for b in self.active_rules:
                if a.id != b.id and any(c.predicate == a.consequent.predicate for c in b.antecedents):
                    edges.append({"from": a.id, "to": b.id, "via": a.consequent.predicate})
        return edges


def _detect_cycle(rules: List[Rule]) -> Optional[List[str]]:
    graph: Dict[str, set] = {}
    for r in rules:
        for c in r.antecedents:
            graph.setdefault(c.predicate, set()).add(r.consequent.predicate)
    state: Dict[str, int] = {}

    def visit(node: str, path: List[str]) -> Optional[List[str]]:
        state[node] = 1
        for nxt in graph.get(node, ()):
            if state.get(nxt) == 1:
                return path + [node, nxt]
            if state.get(nxt) is None:
                found = visit(nxt, path + [node])
                if found:
                    return found
        state[node] = 2
        return None

    for n in list(graph):
        if state.get(n) is None:
            found = visit(n, [])
            if found:
                return found
    return None


def parse_rulebase(data: dict, registry: PredicateRegistry) -> RuleBase:
    if not isinstance(data, dict) or "rules" not in data or "rulebase_version" not in data:
        raise RuleBaseError("Rule base must be an object with 'rulebase_version' and 'rules'.")
    errors: List[str] = []
    rules: List[Rule] = []
    seen = set()
    for idx, raw in enumerate(data["rules"]):
        label = raw.get("id", f"#{idx}") if isinstance(raw, dict) else f"#{idx}"
        try:
            missing = [k for k in _REQUIRED if k not in raw]
            if missing:
                raise RuleBaseError(f"missing fields {missing}")
            if raw["id"] in seen:
                raise RuleBaseError("duplicate rule id")
            seen.add(raw["id"])
            antecedents = tuple(Condition.parse(t) for t in raw["if"])
            consequent = Condition.parse(raw["then"])
            if not antecedents:
                raise RuleBaseError("a rule needs at least one antecedent")
            for c in (*antecedents, consequent):
                spec = registry.get(c.predicate)
                if len(c.args) != spec.arity:
                    raise RuleBaseError(f"{c.predicate} expects {spec.arity} argument(s)")
            bound = {v for a in antecedents for v in a.variables}
            if any(is_variable(t) and t not in bound for t in consequent.args):
                raise RuleBaseError("consequent uses a variable not bound by the antecedents")
            if registry.kind_of(consequent.predicate) not in ("indicator", "risk", "external"):
                raise RuleBaseError("rules may only derive indicator or risk predicates")
            mm = raw.get("min_matches")
            if mm is not None:
                if not (isinstance(mm, int) and 1 <= mm <= len(antecedents)):
                    raise RuleBaseError("min_matches must be between 1 and the number of antecedents")
                if len({a.args for a in antecedents}) != 1 or any(len(a.args) != 1 or not is_variable(a.args[0]) for a in antecedents):
                    raise RuleBaseError("m-of-n rules require unary antecedents over one shared variable")
            priority = raw["priority"]
            if not (isinstance(priority, int) and 0 <= priority <= 1000):
                raise RuleBaseError("priority must be an integer 0-1000")
            status = raw.get("status", "ACTIVE")
            if status not in ("ACTIVE", "INACTIVE"):
                raise RuleBaseError("status must be ACTIVE or INACTIVE")
            rules.append(Rule(
                id=str(raw["id"]), name=str(raw["name"]), category=str(raw["category"]),
                description=str(raw["description"]), explanation=str(raw["explanation"]),
                antecedents=antecedents, consequent=consequent, priority=priority,
                severity=RiskLevel(raw["severity"]), min_matches=mm, tags=tuple(raw.get("tags", [])),
                source=str(raw.get("source", "FraudShield rule base")),
                version=str(raw.get("version", data["rulebase_version"])), status=status))
        except (RuleBaseError, ValueError, TypeError, AttributeError) as exc:
            errors.append(f"{label}: {exc}")
    if errors:
        raise RuleBaseError("Rule base validation failed: " + "; ".join(errors), details=errors)
    if not rules or not any(r.active for r in rules):
        raise RuleBaseError("Rule base contains no active rules; refusing to continue with an empty rule set.")
    cycle = _detect_cycle([r for r in rules if r.active])
    if cycle:
        raise RuleBaseError("Rule base contains a cyclic derivation: " + " -> ".join(cycle))
    return RuleBase(name=str(data.get("name", "FraudShield Rule Base")), version=str(data["rulebase_version"]), rules=rules)


def load_rulebase(path: Path | str | None = None, registry: PredicateRegistry | None = None) -> RuleBase:
    p = Path(path) if path else DEFAULT_RULEBASE_PATH
    registry = registry or default_registry()
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise RuleBaseError(f"Rule base file not found: {p}") from None
    except (OSError, json.JSONDecodeError) as exc:
        raise RuleBaseError(f"Rule base file {p} could not be read: {exc}") from exc
    return parse_rulebase(data, registry)


@lru_cache(maxsize=1)
def default_rulebase() -> RuleBase:
    return load_rulebase()
