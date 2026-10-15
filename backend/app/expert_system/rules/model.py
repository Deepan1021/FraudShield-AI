"""Structured rule representation. Rules are data, never executable code."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Tuple

from app.core.errors import RuleBaseError
from app.domain.enums import RiskLevel

_ATOM_RE = re.compile(r"^([A-Z][A-Za-z0-9]*)\(([A-Za-z0-9_,\s]*)\)$")
_TERM_RE = re.compile(r"^[A-Za-z0-9_]+$")


def is_variable(term: str) -> bool:
    return bool(term) and term[0].islower()


@dataclass(frozen=True)
class Condition:
    predicate: str
    args: Tuple[str, ...]

    @classmethod
    def parse(cls, text: str) -> "Condition":
        m = _ATOM_RE.match(text.strip())
        if not m:
            raise RuleBaseError(f"Invalid atom syntax: {text!r}")
        args = tuple(a.strip() for a in m.group(2).split(",") if a.strip())
        if not args or any(not _TERM_RE.match(a) for a in args):
            raise RuleBaseError(f"Invalid arguments in atom: {text!r}")
        return cls(m.group(1), args)

    @property
    def variables(self) -> Tuple[str, ...]:
        return tuple(a for a in self.args if is_variable(a))

    def __str__(self) -> str:
        return f"{self.predicate}({', '.join(self.args)})"


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    category: str
    description: str
    explanation: str
    antecedents: Tuple[Condition, ...]
    consequent: Condition
    priority: int
    severity: RiskLevel
    min_matches: Optional[int] = None  # m-of-n rule: at least this many antecedents must hold
    tags: Tuple[str, ...] = ()
    source: str = "FraudShield rule base"
    version: str = "1.0.0"
    status: str = "ACTIVE"

    @property
    def active(self) -> bool:
        return self.status == "ACTIVE"

    @property
    def specificity(self) -> int:
        return len(self.antecedents) if self.min_matches is None else self.min_matches

    def formula(self) -> str:
        lhs = " ∧ ".join(str(a) for a in self.antecedents)
        if self.min_matches is not None:
            lhs = f"AtLeast({self.min_matches} of [{lhs}])"
        return f"{lhs} → {self.consequent}"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "category": self.category, "description": self.description,
            "explanation": self.explanation, "antecedents": [str(a) for a in self.antecedents],
            "consequent": str(self.consequent), "formula": self.formula(), "priority": self.priority,
            "severity": self.severity.value, "min_matches": self.min_matches, "tags": list(self.tags),
            "source": self.source, "version": self.version, "status": self.status,
        }
