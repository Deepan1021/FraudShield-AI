"""Constraint engine: consistency checks over the validated input.

Constraints do not reject a transaction (validation does that). A violated constraint is
recorded and may generate a fact (e.g. SessionIntegrityConcern) for the rule engine.
"""
from __future__ import annotations

from typing import List, Optional

from app.domain.enums import DeviceTrust, LoginBehavior
from app.domain.models import BaselineProfile, ConstraintResult, Transaction

CHANNEL_LIMITS = {"UPI": 100_000.0}
DEFAULT_CHANNEL_LIMIT = 1_000_000.0
MAX_PLAUSIBLE_FREQUENCY = 100


def evaluate_constraints(tx: Transaction, baseline: Optional[BaselineProfile] = None) -> List[ConstraintResult]:
    results: List[ConstraintResult] = []

    limit = CHANNEL_LIMITS.get(tx.channel or "", DEFAULT_CHANNEL_LIMIT)
    within = tx.amount <= limit
    results.append(ConstraintResult(
        "C01", "Amount within channel limit", within, "info" if within else "warning",
        f"Amount {tx.amount:,.2f} is within the {limit:,.0f} limit for this channel." if within
        else f"Amount {tx.amount:,.2f} exceeds the typical {limit:,.0f} limit for channel {tx.channel or 'default'}."))

    plausible = tx.transaction_frequency <= MAX_PLAUSIBLE_FREQUENCY
    results.append(ConstraintResult(
        "C02", "Frequency plausible", plausible, "info" if plausible else "warning",
        "Transaction frequency is plausible." if plausible
        else f"Frequency {tx.transaction_frequency} exceeds the plausible maximum of {MAX_PLAUSIBLE_FREQUENCY}."))

    inconsistent = (tx.device_trust in (DeviceTrust.TRUSTED, DeviceTrust.KNOWN)
                    and tx.login_behavior in (LoginBehavior.SUSPICIOUS, LoginBehavior.HIGH_RISK))
    results.append(ConstraintResult(
        "C03", "Device trust consistent with login behaviour", not inconsistent,
        "warning" if inconsistent else "info",
        "A trusted/known device is paired with a high-risk login: possible session hijack or credential misuse."
        if inconsistent else "Device trust and login behaviour are consistent."))
    return results
