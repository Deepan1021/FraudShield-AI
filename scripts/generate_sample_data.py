"""Deterministically generates synthetic demonstration data (labelled synthetic everywhere in the product).

The risk classification of each row is NOT stored here - it is produced by the rule engine at seed time.
"""
import csv
import json
import random
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
CITIES = ["Chennai", "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Kochi"]
rng = random.Random(20260101)

USERS = {}
names = ["Asha", "Rahul", "Meera", "Karthik", "Priya", "Vikram", "Sana", "Arjun", "Divya", "Imran", "Nisha", "Rohan"]
for i, n in enumerate(names, start=1):
    home = CITIES[i % len(CITIES)]
    other = CITIES[(i + 3) % len(CITIES)]
    USERS[f"USER{i:03d}"] = {
        "display_name": f"Synthetic User {i:03d}",
        "average_amount": rng.choice([3000, 5000, 8000, 12000, 15000, 22000]),
        "usual_frequency": rng.choice([2, 3, 4, 5]),
        "known_devices": [f"DEV{i:03d}A", f"DEV{i:03d}B"],
        "known_locations": [home, other] if i % 3 == 0 else [home],
        "usual_hours": list(range(8, 22)) if i % 2 else list(range(9, 23)),
    }
USERS["USER001"].update({"average_amount": 15000, "usual_frequency": 4, "known_devices": ["DEV001"], "known_locations": ["Chennai"], "usual_hours": list(range(8, 22))})
USERS["USER002"].update({"average_amount": 3000, "usual_frequency": 2, "known_devices": ["DEV002"], "known_locations": ["Chennai"], "usual_hours": list(range(8, 22))})

FIELDS = ["transaction_id", "user_id", "amount", "transaction_time", "device_trust", "device_id", "location",
          "login_behavior", "transaction_frequency", "account_activity", "channel", "days_ago"]
rows = [
    ["TXN001", "USER001", 85000, "02:15", "UNTRUSTED", "DEV-X91", "Delhi", "SUSPICIOUS", 12, "ACTIVE", "UPI", 0],
    ["TXN002", "USER002", 2500, "14:30", "TRUSTED", "DEV002", "Chennai", "NORMAL", 2, "ACTIVE", "UPI", 0],
]
channels = ["UPI", "WALLET", "ONLINE_BANKING", "CARD"]


def hhmm(lo, hi):
    return f"{rng.randint(lo, hi):02d}:{rng.choice([0, 10, 15, 20, 30, 45, 50]):02d}"


def make(n, kind):
    uid = rng.choice(list(USERS))
    u = USERS[uid]
    home = u["known_locations"][0]
    foreign = rng.choice([c for c in CITIES if c not in u["known_locations"]])
    base = dict(transaction_id=f"TXN{n:03d}", user_id=uid, amount=round(u["average_amount"] * rng.uniform(0.3, 1.3), -1),
                transaction_time=hhmm(9, 20), device_trust=rng.choice(["TRUSTED", "TRUSTED", "KNOWN"]),
                device_id=rng.choice(u["known_devices"]), location=home, login_behavior="NORMAL",
                transaction_frequency=rng.randint(1, u["usual_frequency"] + 1), account_activity=rng.choice(["ACTIVE", "ACTIVE", "NORMAL"]),
                channel=rng.choice(channels), days_ago=rng.randint(0, 29))
    if kind == "moderate":
        pick = rng.choice(["location", "device", "amount", "login", "night_burst", "dormant"])
        if pick == "location": base["location"] = foreign
        elif pick == "device": base["device_trust"] = "UNKNOWN"
        elif pick == "amount": base["amount"] = rng.choice([52000, 60000, 72000])
        elif pick == "login": base["login_behavior"] = rng.choice(["UNUSUAL", "FAILED_ATTEMPTS"])
        elif pick == "night_burst": base.update(transaction_time=hhmm(1, 4), transaction_frequency=rng.randint(10, 14))
        else: base["account_activity"] = "DORMANT"
    elif kind == "high":
        pick = rng.choice(["amount_device", "login_location", "dormant_amount", "velocity_amount"])
        if pick == "amount_device": base.update(device_trust="UNTRUSTED", device_id=f"DEV-X{rng.randint(10, 99)}", amount=rng.choice([55000, 68000, 90000]))
        elif pick == "login_location": base.update(login_behavior="SUSPICIOUS", location=foreign)
        elif pick == "dormant_amount": base.update(account_activity="DORMANT", amount=rng.choice([60000, 75000]))
        else: base.update(transaction_frequency=rng.randint(11, 16), amount=rng.choice([58000, 64000]))
    elif kind == "critical":
        base.update(device_trust=rng.choice(["UNTRUSTED", "UNKNOWN"]), device_id=f"DEV-X{rng.randint(10, 99)}", location=foreign,
                    login_behavior=rng.choice(["SUSPICIOUS", "HIGH_RISK"]), transaction_time=hhmm(0, 4),
                    amount=rng.choice([70000, 95000, 120000]), transaction_frequency=rng.randint(10, 18),
                    account_activity=rng.choice(["ACTIVE", "RECENTLY_REACTIVATED", "DORMANT"]))
    return [base[f] for f in FIELDS]


kinds = ["normal"] * 38 + ["moderate"] * 16 + ["high"] * 11 + ["critical"] * 7
rng.shuffle(kinds)
for i, k in enumerate(kinds, start=3):
    rows.append(make(i, k))

with open(DATA / "sample_transactions.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(FIELDS)
    w.writerows(rows)
with open(DATA / "user_baselines.json", "w", encoding="utf-8") as fh:
    json.dump({"_note": "Synthetic demonstration data. Not real customer data.", "users": USERS}, fh, indent=2)
print(f"wrote {len(rows)} transactions and {len(USERS)} baselines")
