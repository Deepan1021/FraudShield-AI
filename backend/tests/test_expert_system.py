import copy
import json
import re
import unittest
from pathlib import Path

from app.core.errors import InferenceError, RuleBaseError
from app.domain.enums import RecommendationAction, RiskLevel
from app.expert_system.classification.classifier import classify
from app.expert_system.classification.recommendation import recommend
from app.expert_system.inference.conflict_resolution import select, sort_key
from app.expert_system.inference.forward_chaining import ForwardChainingEngine
from app.expert_system.inference.matcher import match_rule, unify
from app.expert_system.knowledge_base.fact import Fact
from app.expert_system.knowledge_base.working_memory import WorkingMemory
from app.expert_system.predicates.registry import PredicateRegistry, PredicateSpec, default_registry
from app.expert_system.rules.model import Condition
from app.expert_system.rules.rulebase import DEFAULT_RULEBASE_PATH, default_rulebase, load_rulebase, parse_rulebase

REG = default_registry()
RB = default_rulebase()


def F(pred, ent="T1", kind="observed"):
    return Fact(pred, (ent,), kind, "test")


def run(*preds, ent="T1"):
    return ForwardChainingEngine(RB.rules, REG).run([F(p, ent) for p in preds])


def data():
    return json.loads(Path(DEFAULT_RULEBASE_PATH).read_text(encoding="utf-8"))


class WorkingMemoryTests(unittest.TestCase):
    def test_duplicates_are_rejected(self):
        wm = WorkingMemory()
        self.assertTrue(wm.add(F("HighAmount")))
        self.assertFalse(wm.add(F("HighAmount")))
        self.assertEqual(len(wm), 1)
        self.assertEqual([f.text for f in wm.by_predicate("HighAmount")], ["HighAmount(T1)"])

    def test_fact_representation(self):
        f = Fact("HighAmount", ("TXN001",), "observed", "feature_extractor")
        self.assertEqual((f.text, f.entity, f.key), ("HighAmount(TXN001)", "TXN001", ("HighAmount", ("TXN001",))))
        self.assertEqual(f.to_dict()["source"], "feature_extractor")


class RuleBaseTests(unittest.TestCase):
    def test_default_rulebase_loads(self):
        self.assertEqual(RB.version, "1.0.0")
        self.assertGreaterEqual(len(RB.active_rules), 30)
        r30 = RB.get("R30")
        self.assertEqual(r30.formula(), "HighAmount(x) ∧ UnverifiedDevice(x) → HighRisk(x)")
        for field in ("id", "name", "description", "priority", "severity", "category", "tags", "source", "version", "explanation", "consequent"):
            self.assertTrue(hasattr(r30, field))

    def test_rule_categories_cover_spec(self):
        cats = {r.category for r in RB.rules}
        for c in ("Device Risk", "Geographic Risk", "Authentication Risk", "Composite Risk", "Behavioural Risk", "Transaction Risk"):
            self.assertIn(c, cats)

    def test_every_predicate_used_is_registered_and_risk_rules_exist_for_each_level(self):
        for r in RB.rules:
            for c in (*r.antecedents, r.consequent):
                self.assertTrue(REG.has(c.predicate), (r.id, c.predicate))
        self.assertEqual({r.severity for r in RB.rules if r.consequent.predicate.endswith("Risk")} >= {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}, True)

    def test_atom_parser_is_safe(self):
        self.assertEqual(str(Condition.parse("HighAmount(x)")), "HighAmount(x)")
        for bad in ("__import__('os').system('x')", "HighAmount(x); drop", "highAmount(x)", "HighAmount()", "A(x,)(y)", "A(x y)"):
            with self.assertRaises(RuleBaseError, msg=bad):
                Condition.parse(bad)

    def test_invalid_rulebases_are_rejected_with_clear_errors(self):
        def mutate(fn):
            d = copy.deepcopy(data()); fn(d)
            with self.assertRaises(RuleBaseError) as ctx:
                parse_rulebase(d, REG)
            return ctx.exception.message
        self.assertIn("Unknown predicate", mutate(lambda d: d["rules"][0].update({"if": ["Bogus(x)"]})))
        self.assertIn("duplicate rule id", mutate(lambda d: d["rules"][1].update({"id": "R01"})))
        self.assertIn("missing fields", mutate(lambda d: d["rules"][0].pop("priority")))
        self.assertIn("not bound", mutate(lambda d: d["rules"][0].update({"then": "UnverifiedDevice(y)"})))
        self.assertIn("min_matches", mutate(lambda d: next(r for r in d["rules"] if r["id"] == "R37").update({"min_matches": 99})))
        self.assertIn("indicator or risk", mutate(lambda d: d["rules"][0].update({"then": "HighAmount(x)"})))
        self.assertIn("priority", mutate(lambda d: d["rules"][0].update({"priority": -3})))
        self.assertIn("cyclic", mutate(lambda d: d["rules"].append({**d["rules"][0], "id": "R99", "if": ["UnverifiedDevice(x)"], "then": "AuthenticationAnomaly(x)"})
                                       or d["rules"].append({**d["rules"][0], "id": "R98", "if": ["AuthenticationAnomaly(x)"], "then": "UnverifiedDevice(x)"})))

    def test_empty_rulebase_never_loads_silently(self):
        with self.assertRaises(RuleBaseError):
            parse_rulebase({"rulebase_version": "9", "rules": []}, REG)
        d = data()
        for r in d["rules"]:
            r["status"] = "INACTIVE"
        with self.assertRaises(RuleBaseError):
            parse_rulebase(d, REG)

    def test_missing_or_corrupt_file(self):
        with self.assertRaises(RuleBaseError):
            load_rulebase("/nonexistent/rules.json")
        import tempfile
        p = Path(tempfile.mkdtemp()) / "bad.json"; p.write_text("{not json")
        with self.assertRaises(RuleBaseError):
            load_rulebase(p)

    def test_source_never_uses_eval_or_exec(self):
        root = Path(__file__).resolve().parents[1] / "app"
        pattern = re.compile(r"\b(eval|exec)\s*\(")
        offenders = [str(p) for p in root.rglob("*.py") if pattern.search(p.read_text(encoding="utf-8"))]
        self.assertEqual(offenders, [])

    def test_no_hardcoded_transaction_results(self):
        root = Path(__file__).resolve().parents[1] / "app"
        offenders = [str(p) for p in root.rglob("*.py") if re.search(r"==\s*[\"']TXN\d+[\"']", p.read_text(encoding="utf-8"))]
        self.assertEqual(offenders, [])

    def test_inactive_rule_is_not_used(self):
        d = data()
        for r in d["rules"]:
            if r["id"] == "R30":
                r["status"] = "INACTIVE"
        rb = parse_rulebase(d, REG)
        res = ForwardChainingEngine(rb.rules, REG).run([F("HighAmount"), F("UntrustedDevice")])
        self.assertNotIn("R30", {e.rule_id for e in res.executions})


class MatcherTests(unittest.TestCase):
    def test_unification(self):
        c = Condition.parse("HighAmount(x)")
        self.assertEqual(unify(c, F("HighAmount", "A"), {}), {"x": "A"})
        self.assertIsNone(unify(c, F("HighAmount", "A"), {"x": "B"}))
        self.assertIsNone(unify(c, F("NewLocation", "A"), {}))
        self.assertEqual(unify(Condition.parse("HighAmount(TXN1)"), F("HighAmount", "TXN1"), {}), {})
        self.assertIsNone(unify(Condition.parse("HighAmount(TXN1)"), F("HighAmount", "TXN2"), {}))

    def test_conjunction_requires_all_antecedents(self):
        wm = WorkingMemory([F("HighAmount"), F("UnverifiedDevice", kind="indicator")])
        self.assertEqual(len(match_rule(RB.get("R30"), wm)), 1)
        self.assertEqual(len(match_rule(RB.get("R30"), WorkingMemory([F("HighAmount")]))), 0)

    def test_matching_is_per_entity(self):
        wm = WorkingMemory([F("HighAmount", "A"), F("UnverifiedDevice", "B", "indicator")])
        self.assertEqual(match_rule(RB.get("R30"), wm), [])
        wm.add(F("UnverifiedDevice", "A", "indicator"))
        m = match_rule(RB.get("R30"), wm)
        self.assertEqual([x.binding_dict() for x in m], [{"x": "A"}])

    def test_m_of_n_rule(self):
        r37 = RB.get("R37")
        two = WorkingMemory([F("UnverifiedDevice", kind="indicator"), F("NewLocation")])
        three = WorkingMemory([F("UnverifiedDevice", kind="indicator"), F("NewLocation"), F("HighFrequency")])
        self.assertEqual(match_rule(r37, two), [])
        self.assertEqual(len(match_rule(r37, three)), 1)
        self.assertEqual(len(match_rule(r37, three)[0].facts), 3)

    def test_multi_arity_join(self):
        from app.expert_system.rules.model import Rule
        rule = Rule("RX", "x", "t", "d", "e", (Condition.parse("Linked(a, b)"), Condition.parse("Linked(b, c)")),
                    Condition.parse("Linked2(a, c)"), 1, RiskLevel.LOW)
        wm = WorkingMemory([Fact("Linked", ("1", "2"), "observed", "t"), Fact("Linked", ("2", "3"), "observed", "t"),
                            Fact("Linked", ("5", "6"), "observed", "t")])
        ms = match_rule(rule, wm)
        self.assertEqual([m.binding_dict() for m in ms], [{"a": "1", "b": "2", "c": "3"}])


class ForwardChainingTests(unittest.TestCase):
    def test_single_chain_derivation(self):
        r = run("UntrustedDevice", "HighAmount")
        texts = {f.text for f in r.working_memory}
        self.assertTrue({"UnverifiedDevice(T1)", "ElevatedValue(T1)", "HighRisk(T1)", "MediumRisk(T1)"} <= texts)
        self.assertNotIn("CriticalRisk(T1)", texts)

    def test_chain_depth_and_provenance(self):
        r = run("UntrustedDevice", "HighAmount", "NightTransaction", "NewLocation")
        crit = r.working_memory.get(("CriticalRisk", ("T1",)))
        self.assertIsNotNone(crit)
        self.assertEqual(crit.derivation_rule, "R40")
        self.assertIn("HighRisk(T1)", crit.parents)
        self.assertEqual(r.working_memory.get(("HighRisk", ("T1",))).derivation_rule, "R30")

    def test_terminates_at_fixpoint_and_no_refiring(self):
        r = run("UntrustedDevice", "HighAmount", "NightTransaction", "NewLocation", "HighFrequency", "SuspiciousLogin")
        keys = [(e.rule_id, tuple(sorted(e.bindings.items()))) for e in r.executions]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(r.terminated_by, "FIXPOINT")
        again = ForwardChainingEngine(RB.rules, REG).run([f for f in r.working_memory if f.kind not in ("indicator", "risk")])
        self.assertEqual({f.text for f in again.working_memory}, {f.text for f in r.working_memory})

    def test_no_duplicate_facts_and_support_is_recorded(self):
        r = run("UntrustedDevice", "HighAmount", "NewLocation")
        texts = [f.text for f in r.working_memory]
        self.assertEqual(len(texts), len(set(texts)))
        medium = r.working_memory.get(("MediumRisk", ("T1",)))
        self.assertTrue(medium.supported_by)
        redundant = [e for e in r.executions if not e.new_fact]
        self.assertTrue(redundant)

    def test_deterministic_order(self):
        facts = ["UntrustedDevice", "HighAmount", "NightTransaction", "NewLocation", "SuspiciousLogin"]
        a = [e.rule_id for e in run(*facts).executions]
        b = [e.rule_id for e in run(*reversed(facts)).executions]
        self.assertEqual(a, b)

    def test_no_rules_fire_without_matching_facts(self):
        r = run("TrustedDevice", "ActiveAccount")
        self.assertEqual(r.executions, [])
        self.assertEqual(r.cycles, 0)

    def test_independent_entities(self):
        r = ForwardChainingEngine(RB.rules, REG).run([F("HighAmount", "A"), F("UntrustedDevice", "A"), F("HighAmount", "B")])
        self.assertIsNotNone(r.working_memory.get(("HighRisk", ("A",))))
        self.assertIsNone(r.working_memory.get(("HighRisk", ("B",))))

    def test_cycle_guard(self):
        with self.assertRaises(InferenceError):
            ForwardChainingEngine(RB.rules, REG, max_cycles=1).run([F("UntrustedDevice"), F("HighAmount")])

    def test_trace_records_conflict_information(self):
        r = run("UntrustedDevice", "HighAmount")
        e = r.executions[0]
        self.assertGreaterEqual(e.conflict_set_size, 2)
        self.assertTrue(e.selected_because)
        self.assertTrue(e.formula)
        self.assertEqual([x.seq for x in r.executions], list(range(1, len(r.executions) + 1)))


class ConflictResolutionTests(unittest.TestCase):
    def matches(self, *preds):
        wm = WorkingMemory([F(p) for p in preds])
        out = []
        for rule in RB.active_rules:
            out += match_rule(rule, wm)
        return out

    def test_priority_then_specificity_then_severity_then_id(self):
        ms = self.matches("UntrustedDevice", "HighAmount")
        chosen, why = select(ms)
        self.assertEqual(chosen.rule.priority, 90)
        self.assertIn("rule id", why)
        wm = WorkingMemory([F("UnverifiedDevice", kind="indicator"), F("ElevatedValue", kind="indicator"), F("HighAmount")])
        ms = [m for r in RB.active_rules if r.id in ("R30", "R20", "R24") for m in match_rule(r, wm)]
        chosen, _ = select(ms)
        self.assertEqual(chosen.rule.id, "R30")  # priority 70 beats the MEDIUM rules (50)

    def test_specificity_breaks_priority_ties(self):
        from app.expert_system.rules.model import Rule
        a = Rule("A1", "a", "t", "d", "e", (Condition.parse("HighAmount(x)"),), Condition.parse("MediumRisk(x)"), 50, RiskLevel.MEDIUM)
        b = Rule("A2", "b", "t", "d", "e", (Condition.parse("HighAmount(x)"), Condition.parse("NewLocation(x)")), Condition.parse("HighRisk(x)"), 50, RiskLevel.HIGH)
        wm = WorkingMemory([F("HighAmount"), F("NewLocation")])
        ms = match_rule(a, wm) + match_rule(b, wm)
        chosen, why = select(ms)
        self.assertEqual(chosen.rule.id, "A2")
        self.assertIn("specific", why)

    def test_sort_key_is_total_and_stable(self):
        ms = self.matches("UntrustedDevice", "HighAmount", "NewLocation")
        self.assertEqual([sort_key(m) for m in sorted(ms, key=sort_key)], sorted(sort_key(m) for m in ms))


class ClassifierAndRecommendationTests(unittest.TestCase):
    def test_default_low_when_no_conclusion(self):
        a = classify(run("ActiveAccount"), "T1", REG)
        self.assertEqual((a["risk_level"], a["decisive_fact"], a["decisive_rules"]), ("LOW", None, []))

    def test_mitigating_lowrisk_is_overridden_by_higher_risk(self):
        r = run("TrustedDevice", "KnownLocation", "ActiveAccount")
        self.assertEqual(classify(r, "T1", REG)["risk_level"], "LOW")
        self.assertEqual(classify(r, "T1", REG)["decisive_fact"], "LowRisk(T1)")
        r = run("TrustedDevice", "KnownLocation", "ActiveAccount", "HighAmount")
        a = classify(r, "T1", REG)
        self.assertEqual(a["risk_level"], "MEDIUM")
        self.assertIn("LOW", a["overridden_levels"])

    def test_each_level_reachable(self):
        self.assertEqual(classify(run("NewLocation"), "T1", REG)["risk_level"], "MEDIUM")
        self.assertEqual(classify(run("UntrustedDevice", "HighAmount"), "T1", REG)["risk_level"], "HIGH")
        self.assertEqual(classify(run("UntrustedDevice", "HighAmount", "NightTransaction", "NewLocation"), "T1", REG)["risk_level"], "CRITICAL")

    def test_neither_night_nor_frequency_alone_is_risky(self):
        self.assertEqual(classify(run("NightTransaction"), "T1", REG)["risk_level"], "LOW")
        self.assertEqual(classify(run("HighFrequency"), "T1", REG)["risk_level"], "LOW")
        self.assertEqual(classify(run("NightTransaction", "HighFrequency"), "T1", REG)["risk_level"], "MEDIUM")

    def test_accumulation_rules(self):
        self.assertEqual(classify(run("DormantAccount", "HighFrequency", "NewLocation"), "T1", REG)["risk_level"], "HIGH")
        five = run("UntrustedDevice", "HighFrequency", "NewLocation", "NightTransaction", "UnusualLogin")
        self.assertEqual(classify(five, "T1", REG)["risk_level"], "CRITICAL")

    def test_account_takeover_pattern(self):
        a = classify(run("DormantAccount", "SuspiciousLogin", "UnknownDevice"), "T1", REG)
        self.assertEqual(a["risk_level"], "CRITICAL")
        self.assertIn("R42", a["decisive_rules"])

    def test_severity_index_is_transparent(self):
        a = classify(run("HighAmount", "UntrustedDevice"), "T1", REG)
        self.assertEqual(a["severity_index"]["value"], 30)
        self.assertIn("not a probability", a["severity_index"]["note"])
        self.assertEqual(sum(b["weight"] for b in a["severity_index"]["breakdown"]), 30)

    def test_recommendation_policy_is_separate_and_total(self):
        expected = {"LOW": "APPROVE", "MEDIUM": "REQUEST_MFA", "HIGH": "TEMPORARILY_BLOCK", "CRITICAL": "FLAG_FOR_ANALYST_REVIEW"}
        for lvl, action in expected.items():
            self.assertEqual(recommend(RiskLevel(lvl), [])["action"], action)

    def test_rule_tag_escalates_recommendation(self):
        r = run("TrustedDevice", "SuspiciousLogin", "SessionIntegrityConcern", "HighAmount")
        a = classify(r, "T1", REG)
        rec = recommend(RiskLevel(a["risk_level"]), [e.to_dict() for e in r.executions])
        self.assertEqual(a["risk_level"], "HIGH")
        self.assertEqual(rec["action"], RecommendationAction.FLAG_FOR_ANALYST_REVIEW.value)
        self.assertEqual(rec["escalated_by_rules"], ["R36"])

    def test_registry_extension_and_kinds(self):
        reg = PredicateRegistry()
        reg.register(PredicateSpec("MLAnomalyDetected", "external", "ML", "ML signal"))
        self.assertTrue(reg.has("MLAnomalyDetected"))
        with self.assertRaises(RuleBaseError):
            reg.get("Nope")


if __name__ == "__main__":
    unittest.main()
