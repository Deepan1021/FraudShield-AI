"""Predicate vocabulary of the expert system.

Each predicate has a kind that decides where it appears in explanations:
  observed    - taken directly from the transaction input
  behavioural - derived by comparing the transaction with the user's baseline
  constraint  - derived by the constraint engine
  indicator   - derived by production rules (normalised evidence)
  risk        - derived by production rules (risk conclusions)
  external    - supplied by an optional FactProvider (e.g. a future ML signal)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from app.core.errors import RuleBaseError
from app.domain.enums import RiskLevel


@dataclass(frozen=True)
class PredicateSpec:
    name: str
    kind: str
    category: str
    description: str
    driver_text: str = ""
    weight: int = 0  # contribution to the Rule-based Risk Severity Index (observed/behavioural only)
    arity: int = 1

    def to_dict(self) -> dict:
        return {
            "name": self.name, "kind": self.kind, "category": self.category,
            "description": self.description, "driver_text": self.driver_text,
            "weight": self.weight, "arity": self.arity,
        }


def _p(name, kind, category, description, driver="", weight=0):
    return PredicateSpec(name, kind, category, description, driver or description, weight)


_DEFAULT_SPECS = [
    # Transaction
    _p("HighAmount", "observed", "Transaction Risk", "Payment amount meets or exceeds the high-value threshold.", "High-value transaction", 15),
    _p("AmountSpike", "behavioural", "Transaction Risk", "Amount is a large multiple of the user's average amount.", "Amount far above the user's normal spending", 10),
    # Device
    _p("TrustedDevice", "observed", "Device Risk", "Device trust signature is TRUSTED.", "Trusted device"),
    _p("KnownDevice", "observed", "Device Risk", "Device trust signature is KNOWN.", "Known device"),
    _p("UntrustedDevice", "observed", "Device Risk", "Device trust signature is UNTRUSTED.", "Untrusted device", 15),
    _p("UnknownDevice", "observed", "Device Risk", "Device trust signature is UNKNOWN.", "Unknown device", 15),
    _p("NewDevice", "behavioural", "Device Risk", "Device ID has never been seen for this user.", "Device not previously used by this user", 10),
    # Geographic
    _p("NewLocation", "behavioural", "Geographic Risk", "Location is not among the user's known locations.", "New geographic location", 12),
    _p("KnownLocation", "behavioural", "Geographic Risk", "Location is among the user's known locations.", "Familiar location"),
    # Temporal
    _p("NightTransaction", "observed", "Temporal Risk", "Transaction time falls in the night window (00:00-05:59).", "Night-time transaction", 6),
    _p("UnusualHour", "behavioural", "Temporal Risk", "Hour of day is outside the user's usual hours.", "Unusual hour for this user", 6),
    _p("UsualHour", "behavioural", "Temporal Risk", "Hour of day is within the user's usual hours.", "Usual hour"),
    # Behavioural
    _p("HighFrequency", "observed", "Behavioural Risk", "Transaction velocity is high (absolute or relative to baseline).", "High transaction frequency", 8),
    _p("NoBehaviouralBaseline", "behavioural", "Behavioural Risk", "No behavioural baseline exists for this user; baseline comparisons were skipped.", "No behavioural baseline available"),
    # Authentication
    _p("SuspiciousLogin", "observed", "Authentication Risk", "Login behaviour is SUSPICIOUS or HIGH_RISK.", "Suspicious login behaviour", 18),
    _p("FailedLoginAttempts", "observed", "Authentication Risk", "Login behaviour shows failed attempts.", "Failed login attempts", 12),
    _p("UnusualLogin", "observed", "Authentication Risk", "Login behaviour is UNUSUAL.", "Unusual login behaviour", 6),
    _p("SessionIntegrityConcern", "constraint", "Authentication Risk", "A trusted/known device is paired with a high-risk login (possible session hijack).", "Trusted device combined with high-risk login", 12),
    # Account
    _p("ActiveAccount", "observed", "Account Risk", "Account activity is ACTIVE or NORMAL.", "Active account"),
    _p("DormantAccount", "observed", "Account Risk", "Account was dormant.", "Dormant account in use", 10),
    _p("RecentlyReactivated", "observed", "Account Risk", "Account was recently reactivated.", "Recently reactivated account", 8),
    _p("SuspiciousAccountActivity", "observed", "Account Risk", "Account activity is SUSPICIOUS or UNUSUAL.", "Suspicious account activity", 12),
    # Derived indicators
    _p("UnverifiedDevice", "indicator", "Device Risk", "Device cannot be verified (untrusted, unknown or new)."),
    _p("ElevatedValue", "indicator", "Transaction Risk", "Transaction value is elevated (high amount or amount spike)."),
    _p("AuthenticationAnomaly", "indicator", "Authentication Risk", "Authentication behaviour is anomalous."),
    _p("AccountAnomaly", "indicator", "Account Risk", "Account lifecycle behaviour is anomalous."),
    _p("OffHoursActivity", "indicator", "Temporal Risk", "Activity occurs outside normal hours."),
    # Risk conclusions
    _p("LowRisk", "risk", "Risk Conclusion", "Risk conclusion: LOW."),
    _p("MediumRisk", "risk", "Risk Conclusion", "Risk conclusion: MEDIUM."),
    _p("HighRisk", "risk", "Risk Conclusion", "Risk conclusion: HIGH."),
    _p("CriticalRisk", "risk", "Risk Conclusion", "Risk conclusion: CRITICAL."),
]

RISK_PREDICATES: Dict[str, RiskLevel] = {
    "LowRisk": RiskLevel.LOW,
    "MediumRisk": RiskLevel.MEDIUM,
    "HighRisk": RiskLevel.HIGH,
    "CriticalRisk": RiskLevel.CRITICAL,
}


class PredicateRegistry:
    def __init__(self, specs: List[PredicateSpec] | None = None):
        self._specs: Dict[str, PredicateSpec] = {}
        for s in specs if specs is not None else _DEFAULT_SPECS:
            self.register(s)

    def register(self, spec: PredicateSpec) -> None:
        self._specs[spec.name] = spec

    def get(self, name: str) -> PredicateSpec:
        try:
            return self._specs[name]
        except KeyError:
            raise RuleBaseError(f"Unknown predicate '{name}'") from None

    def has(self, name: str) -> bool:
        return name in self._specs

    def all(self) -> List[PredicateSpec]:
        return list(self._specs.values())

    def kind_of(self, name: str) -> str:
        return self.get(name).kind


def default_registry() -> PredicateRegistry:
    return PredicateRegistry()
