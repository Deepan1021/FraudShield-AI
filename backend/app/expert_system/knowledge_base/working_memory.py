"""Working memory: indexed, duplicate-free store of facts for one inference run."""
from __future__ import annotations

from typing import Dict, Iterable, Iterator, List

from app.expert_system.knowledge_base.fact import Fact, FactKey
from app.utils.timeutil import utc_now_iso


class WorkingMemory:
    def __init__(self, facts: Iterable[Fact] = ()):
        self._facts: Dict[FactKey, Fact] = {}
        self._by_predicate: Dict[str, List[Fact]] = {}
        self._seq = 0
        for f in facts:
            self.add(f)

    def add(self, fact: Fact) -> bool:
        """Insert a fact. Returns False (and changes nothing) if an identical fact exists."""
        if fact.key in self._facts:
            return False
        self._seq += 1
        fact.seq = self._seq
        if not fact.created_at:
            fact.created_at = utc_now_iso()
        self._facts[fact.key] = fact
        self._by_predicate.setdefault(fact.predicate, []).append(fact)
        return True

    def get(self, key: FactKey) -> Fact | None:
        return self._facts.get(key)

    def by_predicate(self, predicate: str) -> List[Fact]:
        return self._by_predicate.get(predicate, [])

    def entities(self) -> List[str]:
        seen: List[str] = []
        for f in self._facts.values():
            e = f.entity
            if e and e not in seen:
                seen.append(e)
        return seen

    def by_text(self) -> Dict[str, Fact]:
        return {f.text: f for f in self._facts.values()}

    def __contains__(self, key: FactKey) -> bool:
        return key in self._facts

    def __iter__(self) -> Iterator[Fact]:
        return iter(sorted(self._facts.values(), key=lambda f: f.seq))

    def __len__(self) -> int:
        return len(self._facts)
