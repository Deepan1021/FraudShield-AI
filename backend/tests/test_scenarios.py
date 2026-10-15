"""Acceptance scenarios A-D, TXN001/TXN002 and the full pipeline contract."""
import unittest

from app.core.errors import TransactionValidationError
from app.expert_system.extensions import FactProvider
from app.expert_system.knowledge_base.fact import Fact
from app.expert_system.predicates.registry import PredicateSpec, default_registry
from app.pipeline import AnalysisPipeline, analyze_transaction
from tests.helpers import TXN001, TXN002, baseline, tx


class ScenarioTests(unittest.TestCase):
    def test_scenario_a_low(self):
        r = analyze_transaction(tx(transaction_id="TXNA"), baseline())
        self.assertEqual((r["risk_level"], r["recommendation"]["action"]), ("LOW", "APPROVE"))
        self.assertEqual(r["assessment"]["decisive_rules"], ["R50"])
        self.assertEqual(r["explanation"]["drivers"][0]["role"], "mitigating")

    def test_scenario_b_medium(self):
        r = analyze_transaction(tx(transaction_id="TXNB", location="Mumbai"), baseline())
        self.assertEqual((r["risk_level"], r["recommendation"]["action"]), ("MEDIUM", "REQUEST_MFA"))
        self.assertEqual([t["rule_id"] for t in r["triggered_rules"]], ["R21"])

    def test_scenario_b2_two_weak_signals_still_medium(self):
        r = analyze_transaction(tx(transaction_id="TXNB2", transaction_time="03:00", transaction_frequency=11), baseline())
        self.assertEqual(r["risk_level"], "MEDIUM")
        self.assertIn("R25", {t["rule_id"] for t in r["triggered_rules"]})

    def test_scenario_c_high(self):
        r = analyze_transaction(tx(transaction_id="TXNC", amount=85000, device_trust="UNTRUSTED"), baseline())
        self.assertEqual((r["risk_level"], r["recommendation"]["action"]), ("HIGH", "TEMPORARILY_BLOCK"))
        self.assertIn("R30", r["assessment"]["decisive_rules"])

    def test_scenario_d_critical_txn001(self):
        r = analyze_transaction(TXN001, baseline())
        self.assertEqual((r["risk_level"], r["recommendation"]["action"]), ("CRITICAL", "FLAG_FOR_ANALYST_REVIEW"))
        ids = {t["rule_id"] for t in r["triggered_rules"]}
        self.assertTrue({"R30", "R40", "R41"} <= ids)
        facts = {f["text"] for f in r["facts"]}
        for expected in ("HighAmount(TXN001)", "UntrustedDevice(TXN001)", "NightTransaction(TXN001)", "NewLocation(TXN001)",
                         "HighFrequency(TXN001)", "SuspiciousLogin(TXN001)", "ActiveAccount(TXN001)", "HighRisk(TXN001)", "CriticalRisk(TXN001)"):
            self.assertIn(expected, facts)
        drivers = " ".join(d["text"] for d in r["explanation"]["drivers"]).lower()
        for phrase in ("high-value", "untrusted device", "new geographic location", "night", "suspicious login", "high transaction frequency"):
            self.assertIn(phrase, drivers)

    def test_txn002_normal(self):
        r = analyze_transaction(TXN002)  # no baseline on record
        self.assertEqual((r["risk_level"], r["recommendation"]["action"]), ("LOW", "APPROVE"))
        self.assertIn("NoBehaviouralBaseline(TXN002)", {f["text"] for f in r["facts"]})
        self.assertIn("No risk conclusion", r["assessment"]["rationale"])

    def test_result_is_driven_by_inputs_not_ids(self):
        a = analyze_transaction({**TXN001, "transaction_id": "TXN777"}, baseline())
        b = analyze_transaction({**TXN001, "transaction_id": "TXN001", "device_trust": "TRUSTED", "login_behavior": "NORMAL",
                                 "location": "Chennai", "transaction_time": "11:00", "transaction_frequency": 2}, baseline())
        self.assertEqual(a["risk_level"], "CRITICAL")
        self.assertEqual(b["risk_level"], "MEDIUM")  # only the high amount remains

    def test_risk_is_monotonic_when_adding_indicators(self):
        steps = [tx(transaction_id="TXM0"), tx(transaction_id="TXM1", location="Delhi"),
                 tx(transaction_id="TXM2", location="Delhi", login_behavior="SUSPICIOUS"),
                 tx(transaction_id="TXM3", location="Delhi", login_behavior="SUSPICIOUS", transaction_time="03:00", transaction_frequency=12)]
        ranks = [["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(analyze_transaction(s, baseline())["risk_level"]) for s in steps]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(ranks[-1], 3)

    def test_pipeline_contract(self):
        r = analyze_transaction(TXN001, baseline())
        for key in ("evaluation_id", "transaction_id", "risk_level", "recommendation", "features", "facts", "triggered_rules",
                    "derived_facts", "reasoning_trace", "behavioural_analysis", "explanation", "pipeline", "metadata", "constraints",
                    "validation", "input_snapshot", "severity_index", "rules_evaluated", "initial_facts"):
            self.assertIn(key, r)
        stages = [s["key"] for s in r["pipeline"]]
        self.assertEqual(stages, ["validation", "constraints", "baseline", "behaviour", "features", "facts", "knowledge_base",
                                  "rule_matching", "forward_chaining", "conflict_resolution", "classification", "recommendation", "explanation"])
        self.assertTrue(all(s["status"] == "COMPLETED" for s in r["pipeline"]))
        m = r["metadata"]
        self.assertEqual((m["engine_version"], m["rulebase_version"], m["app_version"]), ("1.0.0", "1.0.0", "1.0.0"))
        self.assertGreater(m["processing_time_ms"], 0)
        self.assertEqual(len(r["rules_evaluated"]), 32)

    def test_evidence_categories_are_separated(self):
        ex = analyze_transaction(TXN001, baseline())["explanation"]
        self.assertTrue(all(e["kind"] == "observed" for e in ex["observed_evidence"]))
        self.assertTrue(all(e["kind"] in ("behavioural", "constraint") for e in ex["derived_evidence"]))
        self.assertTrue(ex["logical_inference"])
        self.assertEqual(ex["final_decision"]["risk_level"], "CRITICAL")
        self.assertTrue(ex["question"].startswith("Why is this transaction CRITICAL"))

    def test_why_chain_reaches_observed_facts(self):
        chain = analyze_transaction(TXN001, baseline())["explanation"]["why_chain"]
        self.assertEqual(chain["fact"], "CriticalRisk(TXN001)")

        def leaves(n):
            return [n] if not n["children"] else [x for c in n["children"] for x in leaves(c)]
        self.assertTrue(all(l["kind"] in ("observed", "behavioural", "constraint") for l in leaves(chain)))

    def test_graph_is_consistent(self):
        g = analyze_transaction(TXN001, baseline())["explanation"]["graph"]
        ids = {n["id"] for n in g["nodes"]}
        self.assertTrue(all(e["from"] in ids and e["to"] in ids for e in g["edges"]))
        layers = {n["id"]: n["layer"] for n in g["nodes"]}
        for e in g["edges"]:
            if e["from"] in layers and e["to"] in layers and e["decisive"]:
                self.assertLess(layers[e["from"]], layers[e["to"]])
        self.assertTrue(any(n["decisive"] for n in g["nodes"]))

    def test_invalid_input_raises_structured_error(self):
        with self.assertRaises(TransactionValidationError):
            analyze_transaction(tx(amount=-1))


class MLProviderStub:
    name = "ml-stub"

    def provide(self, transaction):
        return [Fact("MLAnomalyDetected", (transaction.transaction_id,), "external", "ml-stub", confidence=0.9)]


class ExtensionTests(unittest.TestCase):
    def test_external_provider_feeds_the_knowledge_base(self):
        reg = default_registry()
        reg.register(PredicateSpec("MLAnomalyDetected", "external", "ML", "Anomaly model flagged the transaction"))
        r = AnalysisPipeline(registry=reg, fact_providers=[MLProviderStub()]).analyze(tx(transaction_id="TXNML"), baseline())
        self.assertIn("MLAnomalyDetected(TXNML)", {f["text"] for f in r["facts"]})
        self.assertEqual(r["risk_level"], "LOW")  # the symbolic rule base remains the decision maker

    def test_unregistered_provider_predicate_is_refused(self):
        with self.assertRaises(ValueError):
            AnalysisPipeline(fact_providers=[MLProviderStub()]).analyze(tx(transaction_id="TXNML2"), baseline())


if __name__ == "__main__":
    unittest.main()
