"""Feature extraction: structured security features. No scoring happens here."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.domain.enums import AccountActivity, DeviceTrust, LoginBehavior
from app.domain.models import BehaviourAnalysis, ConstraintResult, Feature, Transaction


@dataclass(frozen=True)
class FeatureConfig:
    high_amount_threshold: float = 50_000.0
    amount_spike_ratio: float = 3.0
    high_frequency_absolute: int = 10
    frequency_ratio: float = 3.0
    frequency_ratio_min: int = 6
    night_start_hour: int = 0
    night_end_hour: int = 5  # inclusive

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def extract_features(tx: Transaction, behaviour: BehaviourAnalysis, constraints: List[ConstraintResult],
                     cfg: FeatureConfig = FeatureConfig()) -> List[Feature]:
    dev = lambda name: behaviour.by_dimension(name)  # noqa: E731
    amount_dev, freq_dev = dev("amount"), dev("frequency")
    device_dev, loc_dev, hour_dev = dev("device"), dev("location"), dev("hour")
    c03 = next((c for c in constraints if c.constraint_id == "C03"), None)

    def anomalous(d):
        return bool(d and d.evaluated and d.anomalous)

    def normal(d):
        return bool(d and d.evaluated and not d.anomalous)

    high_freq = tx.transaction_frequency >= cfg.high_frequency_absolute or anomalous(freq_dev)
    F = []
    add = lambda n, v, c, d, k="boolean": F.append(Feature(n, v, c, d, k))  # noqa: E731

    add("high_amount", tx.amount >= cfg.high_amount_threshold, "Transaction", f"Amount >= {cfg.high_amount_threshold:,.0f}")
    add("amount_deviation", amount_dev.ratio if amount_dev and amount_dev.evaluated else None, "Transaction", "Amount divided by the user's average amount", "numeric")
    add("amount_spike", anomalous(amount_dev), "Transaction", f"Amount >= {cfg.amount_spike_ratio:g}x the user's average")
    add("trusted_device", tx.device_trust == DeviceTrust.TRUSTED, "Device", "Device trust signature is TRUSTED")
    add("known_device_label", tx.device_trust == DeviceTrust.KNOWN, "Device", "Device trust signature is KNOWN")
    add("untrusted_device", tx.device_trust == DeviceTrust.UNTRUSTED, "Device", "Device trust signature is UNTRUSTED")
    add("unknown_device", tx.device_trust == DeviceTrust.UNKNOWN, "Device", "Device trust signature is UNKNOWN")
    add("new_device", anomalous(device_dev), "Device", "Device ID not previously used by the user")
    add("new_location", anomalous(loc_dev), "Geographic", "Location not among the user's known locations")
    add("known_location", normal(loc_dev), "Geographic", "Location among the user's known locations")
    add("hour_of_day", tx.hour, "Temporal", "Hour of day (0-23)", "numeric")
    add("night_transaction", cfg.night_start_hour <= tx.hour <= cfg.night_end_hour, "Temporal",
        f"Time between {cfg.night_start_hour:02d}:00 and {cfg.night_end_hour:02d}:59")
    add("unusual_hour", anomalous(hour_dev), "Temporal", "Hour outside the user's usual hours")
    add("usual_hour", normal(hour_dev), "Temporal", "Hour within the user's usual hours")
    add("frequency_ratio", freq_dev.ratio if freq_dev and freq_dev.evaluated else None, "Behavioural", "Frequency divided by the user's usual frequency", "numeric")
    add("high_frequency", high_freq, "Behavioural",
        f"Frequency >= {cfg.high_frequency_absolute} or >= {cfg.frequency_ratio:g}x the user's usual level")
    add("suspicious_login", tx.login_behavior in (LoginBehavior.SUSPICIOUS, LoginBehavior.HIGH_RISK), "Authentication", "Login behaviour SUSPICIOUS or HIGH_RISK")
    add("failed_login_attempts", tx.login_behavior == LoginBehavior.FAILED_ATTEMPTS, "Authentication", "Failed login attempts observed")
    add("unusual_login", tx.login_behavior == LoginBehavior.UNUSUAL, "Authentication", "Login behaviour UNUSUAL")
    add("session_integrity_concern", bool(c03 and not c03.passed), "Authentication", "Trusted device paired with high-risk login")
    add("active_account", tx.account_activity in (AccountActivity.ACTIVE, AccountActivity.NORMAL), "Account", "Account ACTIVE or NORMAL")
    add("dormant_account", tx.account_activity == AccountActivity.DORMANT, "Account", "Account was dormant")
    add("recently_reactivated", tx.account_activity == AccountActivity.RECENTLY_REACTIVATED, "Account", "Account recently reactivated")
    add("suspicious_account_activity", tx.account_activity in (AccountActivity.SUSPICIOUS, AccountActivity.UNUSUAL), "Account", "Account activity SUSPICIOUS or UNUSUAL")
    add("no_behavioural_baseline", not behaviour.baseline_available, "Behavioural", "No baseline exists for the user")
    add("behavioural_deviation_count", behaviour.anomaly_count, "Behavioural", "Number of baseline dimensions that deviate", "numeric")
    return F
