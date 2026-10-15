"""Rule matcher: finds every instantiation of a rule against working memory (with unification)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple

from app.expert_system.knowledge_base.fact import Fact
from app.expert_system.knowledge_base.working_memory import WorkingMemory
from app.expert_system.rules.model import Condition, Rule, is_variable

Bindings = Dict[str, str]


@dataclass(frozen=True)
class Match:
    rule: Rule
    bindings: Tuple[Tuple[str, str], ...]
    facts: Tuple[Fact, ...]

    @property
    def key(self) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
        """Instantiation identity used for refraction (a rule fires once per instantiation)."""
        return (self.rule.id, self.bindings)

    def binding_dict(self) -> Bindings:
        return dict(self.bindings)


def unify(cond: Condition, fact: Fact, bindings: Bindings) -> Optional[Bindings]:
    if cond.predicate != fact.predicate or len(cond.args) != len(fact.args):
        return None
    out = dict(bindings)
    for term, value in zip(cond.args, fact.args):
        if is_variable(term):
            if term in out and out[term] != value:
                return None
            out[term] = value
        elif term != value:
            return None
    return out


def substitute(cond: Condition, bindings: Bindings) -> Tuple[str, ...]:
    return tuple(bindings[t] if is_variable(t) else t for t in cond.args)


def _join(conds: List[Condition], idx: int, bindings: Bindings, chosen: List[Fact], wm: WorkingMemory) -> Iterator[Tuple[Bindings, List[Fact]]]:
    if idx == len(conds):
        yield bindings, list(chosen)
        return
    for fact in wm.by_predicate(conds[idx].predicate):
        nb = unify(conds[idx], fact, bindings)
        if nb is not None:
            chosen.append(fact)
            yield from _join(conds, idx + 1, nb, chosen, wm)
            chosen.pop()


def match_rule(rule: Rule, wm: WorkingMemory) -> List[Match]:
    matches: List[Match] = []
    if rule.min_matches is not None:
        var = rule.antecedents[0].args[0]
        for entity in wm.entities():
            satisfied = []
            for cond in rule.antecedents:
                f = wm.get((cond.predicate, (entity,)))
                if f is not None:
                    satisfied.append(f)
            if len(satisfied) >= rule.min_matches:
                matches.append(Match(rule, ((var, entity),), tuple(satisfied)))
        return matches
    for bindings, facts in _join(list(rule.antecedents), 0, {}, [], wm):
        matches.append(Match(rule, tuple(sorted(bindings.items())), tuple(facts)))
    return matches
