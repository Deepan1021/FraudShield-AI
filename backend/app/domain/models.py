"""Domain models: plain dataclasses with no framework dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from typing import List, Optional

from app.domain.enums import AccountActivity, DeviceTrust, LoginBehavior


@dataclass
class Transaction:
    transaction_id: str
    user_id: str
    amount: float
    transaction_time: time
    device_trust: DeviceTrust
    location: str
    login_behavior: LoginBehavior
    transaction_frequency: int
    account_activity: AccountActivity
    currency: str = "INR"
    channel: Optional[str] = None
    device_id: Optional[str] = None
    merchant_category: Optional[str] = None
    session_id: Optional[str] = None

    @property
    def hour(self) -> int:
        return self.transaction_time.hour

    def snapshot(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "user_id": self.user_id,
            "amount": self.amount,
            "currency": self.currency,
            "transaction_time": self.transaction_time.strftime("%H:%M"),
            "device_trust": self.device_trust.value,
            "location": self.location,
            "login_behavior": self.login_behavior.value,
            "transaction_frequency": self.transaction_frequency,
            "account_activity": self.account_activity.value,
            "channel": self.channel,
            "device_id": self.device_id,
            "merchant_category": self.merchant_category,
            "session_id": self.session_id,
        }


@dataclass
class BaselineProfile:
    user_id: str
    average_amount: float = 0.0
    usual_frequency: float = 0.0
    known_devices: List[str] = field(default_factory=list)
    known_locations: List[str] = field(default_factory=list)
    usual_hours: List[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, user_id: str, d: dict) -> "BaselineProfile":
        return cls(
            user_id=user_id,
            average_amount=float(d.get("average_amount", 0) or 0),
            usual_frequency=float(d.get("usual_frequency", 0) or 0),
            known_devices=[str(x).upper() for x in d.get("known_devices", [])],
            known_locations=[str(x) for x in d.get("known_locations", [])],
            usual_hours=[int(h) for h in d.get("usual_hours", [])],
        )

    def to_dict(self) -> dict:
        return {
            "average_amount": self.average_amount,
            "usual_frequency": self.usual_frequency,
            "known_devices": list(self.known_devices),
            "known_locations": list(self.known_locations),
            "usual_hours": list(self.usual_hours),
        }


@dataclass
class FieldError:
    field: str
    code: str
    message: str

    def to_dict(self) -> dict:
        return {"field": self.field, "code": self.code, "message": self.message}


@dataclass
class ConstraintResult:
    constraint_id: str
    name: str
    passed: bool
    severity: str  # info | warning
    message: str

    def to_dict(self) -> dict:
        return {
            "id": self.constraint_id, "name": self.name, "passed": self.passed,
            "severity": self.severity, "message": self.message,
        }


@dataclass
class Deviation:
    dimension: str
    label: str
    evaluated: bool
    anomalous: bool
    observed: object = None
    baseline: object = None
    ratio: Optional[float] = None
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension, "label": self.label, "evaluated": self.evaluated,
            "anomalous": self.anomalous, "observed": self.observed, "baseline": self.baseline,
            "ratio": self.ratio, "message": self.message,
        }


@dataclass
class BehaviourAnalysis:
    baseline_available: bool
    deviations: List[Deviation]

    @property
    def anomaly_count(self) -> int:
        return sum(1 for d in self.deviations if d.anomalous)

    def by_dimension(self, name: str) -> Optional[Deviation]:
        return next((d for d in self.deviations if d.dimension == name), None)

    def to_dict(self) -> dict:
        return {
            "baseline_available": self.baseline_available,
            "anomaly_count": self.anomaly_count,
            "deviations": [d.to_dict() for d in self.deviations],
        }


@dataclass
class Feature:
    name: str
    value: object
    category: str
    description: str
    kind: str = "boolean"  # boolean | numeric

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "category": self.category,
                "description": self.description, "kind": self.kind}
