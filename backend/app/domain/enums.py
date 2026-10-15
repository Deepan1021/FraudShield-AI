"""Domain enumerations. Risk levels, actions and input categories are defined only here."""
from __future__ import annotations

from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        return _RISK_ORDER.index(self)


_RISK_ORDER = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]


class RecommendationAction(str, Enum):
    APPROVE = "APPROVE"
    REQUEST_MFA = "REQUEST_MFA"
    TEMPORARILY_BLOCK = "TEMPORARILY_BLOCK"
    FLAG_FOR_ANALYST_REVIEW = "FLAG_FOR_ANALYST_REVIEW"

    @property
    def strength(self) -> int:
        return list(RecommendationAction).index(self)


class DeviceTrust(str, Enum):
    TRUSTED = "TRUSTED"
    KNOWN = "KNOWN"
    UNTRUSTED = "UNTRUSTED"
    UNKNOWN = "UNKNOWN"


class LoginBehavior(str, Enum):
    NORMAL = "NORMAL"
    UNUSUAL = "UNUSUAL"
    FAILED_ATTEMPTS = "FAILED_ATTEMPTS"
    SUSPICIOUS = "SUSPICIOUS"
    HIGH_RISK = "HIGH_RISK"


class AccountActivity(str, Enum):
    NORMAL = "NORMAL"
    ACTIVE = "ACTIVE"
    SUSPICIOUS = "SUSPICIOUS"
    DORMANT = "DORMANT"
    RECENTLY_REACTIVATED = "RECENTLY_REACTIVATED"
    UNUSUAL = "UNUSUAL"


class PaymentChannel(str, Enum):
    UPI = "UPI"
    WALLET = "WALLET"
    ONLINE_BANKING = "ONLINE_BANKING"
    CARD = "CARD"
    OTHER = "OTHER"
