"""Fact generation: converts boolean features into structured predicate facts."""
from __future__ import annotations

from typing import List

from app.domain.models import Feature, Transaction
from app.expert_system.knowledge_base.fact import Fact
from app.expert_system.predicates.registry import PredicateRegistry

# feature name -> (predicate, source)
FEATURE_TO_PREDICATE = {
    "high_amount": ("HighAmount", "feature_extractor"),
    "amount_spike": ("AmountSpike", "behaviour_engine"),
    "trusted_device": ("TrustedDevice", "feature_extractor"),
    "known_device_label": ("KnownDevice", "feature_extractor"),
    "untrusted_device": ("UntrustedDevice", "feature_extractor"),
    "unknown_device": ("UnknownDevice", "feature_extractor"),
    "new_device": ("NewDevice", "behaviour_engine"),
    "new_location": ("NewLocation", "behaviour_engine"),
    "known_location": ("KnownLocation", "behaviour_engine"),
    "night_transaction": ("NightTransaction", "feature_extractor"),
    "unusual_hour": ("UnusualHour", "behaviour_engine"),
    "usual_hour": ("UsualHour", "behaviour_engine"),
    "high_frequency": ("HighFrequency", "feature_extractor"),
    "suspicious_login": ("SuspiciousLogin", "feature_extractor"),
    "failed_login_attempts": ("FailedLoginAttempts", "feature_extractor"),
    "unusual_login": ("UnusualLogin", "feature_extractor"),
    "session_integrity_concern": ("SessionIntegrityConcern", "constraint_engine"),
    "active_account": ("ActiveAccount", "feature_extractor"),
    "dormant_account": ("DormantAccount", "feature_extractor"),
    "recently_reactivated": ("RecentlyReactivated", "feature_extractor"),
    "suspicious_account_activity": ("SuspiciousAccountActivity", "feature_extractor"),
    "no_behavioural_baseline": ("NoBehaviouralBaseline", "behaviour_engine"),
}


def generate_facts(tx: Transaction, features: List[Feature], registry: PredicateRegistry) -> List[Fact]:
    facts: List[Fact] = []
    for f in features:
        mapping = FEATURE_TO_PREDICATE.get(f.name)
        if mapping and f.kind == "boolean" and f.value is True:
            predicate, source = mapping
            facts.append(Fact(predicate=predicate, args=(tx.transaction_id,),
                              kind=registry.kind_of(predicate), source=source))
    return facts
