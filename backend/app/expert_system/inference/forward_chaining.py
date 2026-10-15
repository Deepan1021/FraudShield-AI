"""Forward-chaining inference engine with refraction, duplicate-derivation prevention and full tracing."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, List, Sequence, Set

from app.core.errors import InferenceError
from app.expert_system.inference.conflict_resolution import select
from app.expert_system.inference.matcher import Match, match_rule, substitute
from app.expert_system.knowledge_base.fact import Fact
from app.expert_system.knowledge_base.working_memory import WorkingMemory
from app.expert_system.predicates.registry import PredicateRegistry
from app.expert_system.rules.model import Rule


@dataclass
class RuleExecution:
    seq: int
    cycle: int
    rule_id: str
    rule_name: str
    rule_version: str
    category: str
    priority: int
    severity: str
    formula: str
    bindings: dict
    matched_facts: List[str]
    derived_fact: str
    new_fact: bool
    conflict_set_size: int
    selected_because: str
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class InferenceRun:
    working_memory: WorkingMemory
    executions: List[RuleExecution]
    cycles: int
    rules_evaluated: int
    instantiations_matched: int
    match_ms: float
    resolve_ms: float
    total_ms: float
    terminated_by: str = "FIXPOINT"

    @property
    def facts(self) -> List[Fact]:
        return list(self.working_memory)


class ForwardChainingEngine:
    def __init__(self, rules: Sequence[Rule], registry: PredicateRegistry, max_cycles: int = 1000):
        self.rules = [r for r in rules if r.active]
        self.registry = registry
        self.max_cycles = max_cycles

    def run(self, initial_facts: Iterable[Fact]) -> InferenceRun:
        t0 = time.perf_counter()
        wm = WorkingMemory(initial_facts)
        fired: Set[tuple] = set()
        executions: List[RuleExecution] = []
        match_s = resolve_s = 0.0
        total_matched = 0
        cycle = 0
        while True:
            cycle += 1
            if cycle > self.max_cycles:
                raise InferenceError(f"Inference exceeded {self.max_cycles} cycles; possible non-terminating rule base.")
            t = time.perf_counter()
            conflict: List[Match] = []
            for rule in self.rules:
                for m in match_rule(rule, wm):
                    if m.key not in fired:
                        conflict.append(m)
            match_s += time.perf_counter() - t
            if not conflict:
                cycle -= 1
                break
            t = time.perf_counter()
            chosen, reason = select(conflict)
            resolve_s += time.perf_counter() - t
            total_matched += 1
            fired.add(chosen.key)
            rule = chosen.rule
            args = substitute(rule.consequent, chosen.binding_dict())
            parents = tuple(f.text for f in chosen.facts)
            new_fact = Fact(predicate=rule.consequent.predicate, args=args,
                            kind=self.registry.kind_of(rule.consequent.predicate), source="inference_engine",
                            derivation_rule=rule.id, parents=parents)
            added = wm.add(new_fact)
            if not added:  # duplicate derivation: record additional support instead of re-adding
                existing = wm.get(new_fact.key)
                if existing is not None and rule.id != existing.derivation_rule and rule.id not in existing.supported_by:
                    existing.supported_by.append(rule.id)
            executions.append(RuleExecution(
                seq=len(executions) + 1, cycle=cycle, rule_id=rule.id, rule_name=rule.name, rule_version=rule.version,
                category=rule.category, priority=rule.priority, severity=rule.severity.value, formula=rule.formula(),
                bindings=chosen.binding_dict(), matched_facts=list(parents), derived_fact=new_fact.text,
                new_fact=added, conflict_set_size=len(conflict), selected_because=reason, tags=list(rule.tags)))
        return InferenceRun(
            working_memory=wm, executions=executions, cycles=cycle, rules_evaluated=len(self.rules),
            instantiations_matched=total_matched, match_ms=round(match_s * 1000, 3),
            resolve_ms=round(resolve_s * 1000, 3), total_ms=round((time.perf_counter() - t0) * 1000, 3))
