"""Extension points for future hybrid AI.

A FactProvider can add facts (for example MLAnomalyDetected(x) from an anomaly-detection model, an IP
reputation lookup or external threat intelligence) to the knowledge base. Providers only ever ADD
facts; the symbolic rule engine remains the single source of the risk decision.
"""
from __future__ import annotations

from typing import List, Protocol

from app.domain.models import Transaction
from app.expert_system.knowledge_base.fact import Fact


class FactProvider(Protocol):
    name: str

    def provide(self, tx: Transaction) -> List[Fact]:
        ...
