"""Structured fact representation: a ground predicate instance with provenance metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

FactKey = Tuple[str, Tuple[str, ...]]


@dataclass
class Fact:
    predicate: str
    args: Tuple[str, ...]
    kind: str  # observed | behavioural | constraint | indicator | risk | external
    source: str  # feature_extractor | behaviour_engine | constraint_engine | inference_engine | ...
    value: bool = True
    confidence: float = 1.0
    derivation_rule: str | None = None
    parents: Tuple[str, ...] = ()  # texts of the facts this fact was derived from
    seq: int = 0
    created_at: str = ""
    supported_by: list = field(default_factory=list)  # additional rules that re-derived this fact

    @property
    def key(self) -> FactKey:
        return (self.predicate, tuple(self.args))

    @property
    def entity(self) -> str:
        return self.args[0] if self.args else ""

    @property
    def text(self) -> str:
        return f"{self.predicate}({', '.join(self.args)})"

    def to_dict(self) -> dict:
        return {
            "predicate": self.predicate,
            "entity": self.entity,
            "args": list(self.args),
            "text": self.text,
            "value": self.value,
            "kind": self.kind,
            "source": self.source,
            "confidence": self.confidence,
            "derivation_rule": self.derivation_rule,
            "parents": list(self.parents),
            "supported_by": list(self.supported_by),
            "seq": self.seq,
            "created_at": self.created_at,
        }
