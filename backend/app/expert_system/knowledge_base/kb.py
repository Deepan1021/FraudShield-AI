"""Knowledge base: the predicate vocabulary plus the versioned rule base."""
from __future__ import annotations

from typing import Iterable

from app.expert_system.knowledge_base.fact import Fact
from app.expert_system.knowledge_base.working_memory import WorkingMemory
from app.expert_system.predicates.registry import PredicateRegistry
from app.expert_system.rules.rulebase import RuleBase


class KnowledgeBase:
    def __init__(self, rulebase: RuleBase, registry: PredicateRegistry):
        self.rulebase = rulebase
        self.registry = registry

    def new_working_memory(self, facts: Iterable[Fact] = ()) -> WorkingMemory:
        return WorkingMemory(facts)

    def describe(self) -> dict:
        used_in: dict = {}
        derived_by: dict = {}
        for r in self.rulebase.active_rules:
            for c in r.antecedents:
                used_in.setdefault(c.predicate, []).append(r.id)
            derived_by.setdefault(r.consequent.predicate, []).append(r.id)
        predicates = []
        for spec in self.registry.all():
            d = spec.to_dict()
            d["used_in_rules"] = sorted(set(used_in.get(spec.name, [])))
            d["derived_by_rules"] = sorted(set(derived_by.get(spec.name, [])))
            predicates.append(d)
        kinds: dict = {}
        for p in predicates:
            kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
        return {
            "rulebase": {"name": self.rulebase.name, "version": self.rulebase.version,
                         "rule_count": len(self.rulebase.rules), "active_rule_count": len(self.rulebase.active_rules)},
            "predicates": predicates,
            "predicate_kinds": kinds,
            "rule_dependencies": self.rulebase.dependencies(),
            "status": "LOADED",
        }
