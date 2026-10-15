"""Behavioural baseline engine: compares a transaction with the user's baseline."""
from __future__ import annotations

from typing import Optional

from app.domain.models import BaselineProfile, BehaviourAnalysis, Deviation, Transaction


def analyze_behaviour(tx: Transaction, baseline: Optional[BaselineProfile], amount_spike_ratio: float = 3.0,
                      frequency_ratio: float = 3.0, frequency_ratio_min: int = 6) -> BehaviourAnalysis:
    if baseline is None:
        skipped = [Deviation(d, label, False, False, message="No baseline available for this user.")
                   for d, label in (("amount", "Amount vs. average"), ("frequency", "Frequency vs. usual"),
                                    ("device", "Device"), ("location", "Location"), ("hour", "Hour of day"))]
        return BehaviourAnalysis(False, skipped)

    deviations = []

    # Amount
    if baseline.average_amount > 0:
        ratio = round(tx.amount / baseline.average_amount, 2)
        anomalous = ratio >= amount_spike_ratio
        deviations.append(Deviation("amount", "Amount vs. average", True, anomalous, tx.amount, baseline.average_amount, ratio,
                                    f"Amount is {ratio}x the user's average ({baseline.average_amount:,.0f})."))
    else:
        deviations.append(Deviation("amount", "Amount vs. average", False, False, tx.amount, None, None, "Baseline has no average amount."))

    # Frequency
    if baseline.usual_frequency > 0:
        ratio = round(tx.transaction_frequency / baseline.usual_frequency, 2)
        anomalous = ratio >= frequency_ratio and tx.transaction_frequency >= frequency_ratio_min
        deviations.append(Deviation("frequency", "Frequency vs. usual", True, anomalous, tx.transaction_frequency,
                                    baseline.usual_frequency, ratio,
                                    f"Frequency is {ratio}x the user's usual level ({baseline.usual_frequency:g})."))
    else:
        deviations.append(Deviation("frequency", "Frequency vs. usual", False, False, tx.transaction_frequency, None, None, "Baseline has no usual frequency."))

    # Device
    if tx.device_id and baseline.known_devices:
        new = tx.device_id.upper() not in {d.upper() for d in baseline.known_devices}
        deviations.append(Deviation("device", "Device", True, new, tx.device_id, baseline.known_devices, None,
                                    "Device ID has not been seen for this user." if new else "Device ID is among the user's known devices."))
    else:
        deviations.append(Deviation("device", "Device", False, False, tx.device_id, baseline.known_devices or None, None,
                                    "No device ID supplied or no known devices on record."))

    # Location
    if baseline.known_locations:
        new = tx.location.lower() not in {l.lower() for l in baseline.known_locations}
        deviations.append(Deviation("location", "Location", True, new, tx.location, baseline.known_locations, None,
                                    f"{tx.location} is not a known location for this user." if new else f"{tx.location} is a known location."))
    else:
        deviations.append(Deviation("location", "Location", False, False, tx.location, None, None, "No known locations on record."))

    # Hour
    if baseline.usual_hours:
        unusual = tx.hour not in baseline.usual_hours
        deviations.append(Deviation("hour", "Hour of day", True, unusual, tx.hour, baseline.usual_hours, None,
                                    f"Hour {tx.hour:02d}:00 is outside the user's usual hours." if unusual else f"Hour {tx.hour:02d}:00 is within the user's usual hours."))
    else:
        deviations.append(Deviation("hour", "Hour of day", False, False, tx.hour, None, None, "No usual hours on record."))

    return BehaviourAnalysis(True, deviations)
