import unittest

from app.domain.models import BehaviourAnalysis
from app.expert_system.predicates.registry import default_registry
from app.preprocessing.behavior import analyze_behaviour
from app.preprocessing.constraints import evaluate_constraints
from app.preprocessing.fact_generator import generate_facts
from app.preprocessing.features import FeatureConfig, extract_features
from app.preprocessing.validation import validate_transaction
from tests.helpers import baseline, tx


def prepare(raw, with_baseline=True):
    t, _ = validate_transaction(raw)
    b = baseline() if with_baseline else None
    cons = evaluate_constraints(t, b)
    beh = analyze_behaviour(t, b)
    feats = extract_features(t, beh, cons)
    return t, cons, beh, feats


def feature(feats, name):
    return next(f for f in feats if f.name == name).value


class ConstraintTests(unittest.TestCase):
    def test_all_pass_for_normal_transaction(self):
        t, _ = validate_transaction(tx())
        self.assertTrue(all(c.passed for c in evaluate_constraints(t, baseline())))

    def test_upi_limit_and_session_hijack_constraint(self):
        t, _ = validate_transaction(tx(amount=150000, channel="UPI", login_behavior="HIGH_RISK"))
        res = {c.constraint_id: c for c in evaluate_constraints(t, baseline())}
        self.assertFalse(res["C01"].passed)
        self.assertFalse(res["C03"].passed)
        self.assertTrue(res["C02"].passed)

    def test_untrusted_device_with_bad_login_is_consistent(self):
        t, _ = validate_transaction(tx(device_trust="UNTRUSTED", login_behavior="SUSPICIOUS"))
        self.assertTrue(next(c for c in evaluate_constraints(t, baseline()) if c.constraint_id == "C03").passed)


class BehaviourTests(unittest.TestCase):
    def test_baseline_deviations(self):
        t, _ = validate_transaction(tx(amount=90000, location="Delhi", device_id="DEV-X", transaction_time="03:00", transaction_frequency=15))
        beh = analyze_behaviour(t, baseline())
        self.assertTrue(beh.baseline_available)
        self.assertEqual({d.dimension for d in beh.deviations if d.anomalous}, {"amount", "frequency", "device", "location", "hour"})
        self.assertEqual(beh.by_dimension("amount").ratio, 6.0)

    def test_no_deviation_for_normal(self):
        t, _ = validate_transaction(tx())
        self.assertEqual(analyze_behaviour(t, baseline()).anomaly_count, 0)

    def test_missing_baseline_skips_comparisons(self):
        t, _ = validate_transaction(tx())
        beh = analyze_behaviour(t, None)
        self.assertFalse(beh.baseline_available)
        self.assertTrue(all(not d.evaluated and not d.anomalous for d in beh.deviations))

    def test_missing_device_id_is_not_evaluated(self):
        raw = tx(); raw.pop("device_id")
        t, _ = validate_transaction(raw)
        self.assertFalse(analyze_behaviour(t, baseline()).by_dimension("device").evaluated)


class FeatureAndFactTests(unittest.TestCase):
    def test_features_for_critical_profile(self):
        _, _, _, f = prepare(tx(amount=85000, device_trust="UNTRUSTED", location="Delhi", transaction_time="02:15",
                                login_behavior="SUSPICIOUS", transaction_frequency=12))
        for name in ("high_amount", "amount_spike", "untrusted_device", "new_location", "night_transaction",
                     "unusual_hour", "high_frequency", "suspicious_login"):
            self.assertTrue(feature(f, name), name)
        self.assertFalse(feature(f, "trusted_device"))
        self.assertEqual(feature(f, "hour_of_day"), 2)

    def test_thresholds_are_configurable_and_boundaries(self):
        t, _ = validate_transaction(tx(amount=50000))
        beh = analyze_behaviour(t, None)
        self.assertTrue(feature(extract_features(t, beh, [], FeatureConfig()), "high_amount"))
        self.assertFalse(feature(extract_features(t, beh, [], FeatureConfig(high_amount_threshold=60000)), "high_amount"))
        t2, _ = validate_transaction(tx(amount=49999.99))
        self.assertFalse(feature(extract_features(t2, analyze_behaviour(t2, None), []), "high_amount"))

    def test_night_window_boundaries(self):
        for hhmm, expected in (("00:00", True), ("05:59", True), ("06:00", False), ("23:59", False)):
            t, _ = validate_transaction(tx(transaction_time=hhmm))
            self.assertEqual(feature(extract_features(t, analyze_behaviour(t, None), []), "night_transaction"), expected, hhmm)

    def test_high_frequency_absolute_and_relative(self):
        t, _ = validate_transaction(tx(transaction_frequency=10))
        self.assertTrue(feature(extract_features(t, analyze_behaviour(t, None), []), "high_frequency"))
        t, _ = validate_transaction(tx(transaction_frequency=12))  # 3x of usual 4 and >= 6
        self.assertTrue(feature(extract_features(t, analyze_behaviour(t, baseline()), []), "high_frequency"))
        t, _ = validate_transaction(tx(transaction_frequency=9))
        self.assertFalse(feature(extract_features(t, analyze_behaviour(t, None), []), "high_frequency"))

    def test_facts_are_structured_and_scoped_to_entity(self):
        t, _, _, feats = prepare(tx(amount=85000, device_trust="UNKNOWN", account_activity="DORMANT"))
        facts = generate_facts(t, feats, default_registry())
        texts = {f.text for f in facts}
        self.assertIn("HighAmount(TXN900)", texts)
        self.assertIn("UnknownDevice(TXN900)", texts)
        self.assertIn("DormantAccount(TXN900)", texts)
        self.assertNotIn("ActiveAccount(TXN900)", texts)
        f = next(x for x in facts if x.predicate == "HighAmount")
        self.assertEqual((f.entity, f.kind, f.source, f.value), ("TXN900", "observed", "feature_extractor", True))

    def test_baseline_absence_generates_fact(self):
        t, _, _, feats = prepare(tx(), with_baseline=False)
        self.assertIn("NoBehaviouralBaseline(TXN900)", {f.text for f in generate_facts(t, feats, default_registry())})


if __name__ == "__main__":
    unittest.main()
