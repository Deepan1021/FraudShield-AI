import csv
import io
import json
import unittest
from pathlib import Path

from app.core.errors import (DuplicateTransactionError, NotFoundError, ReportError, RuleBaseError,
                             TransactionValidationError)
from app.utils.files import ensure_within, sanitize_filename, unique_path
from tests.helpers import TXN001, TXN002, TempContainer, tx


class ServiceTests(TempContainer, unittest.TestCase):
    def setUp(self):
        self.setup_container()

    def tearDown(self):
        self.teardown_container()

    def test_analysis_persists_everything_atomically(self):
        r = self.container.analysis.analyze(TXN001)
        self.assertEqual(r["risk_level"], "CRITICAL")
        d = self.container.transactions.detail("txn001")
        self.assertEqual(d["result"]["evaluation_id"], r["evaluation_id"])
        self.assertEqual(d["transaction"]["status"], "UNDER_REVIEW")
        self.assertEqual(d["transaction"]["recommendation_action"], "FLAG_FOR_ANALYST_REVIEW")
        events = [a["event_type"] for a in d["audit"]]
        for e in ("TRANSACTION_RECEIVED", "ANALYSIS_COMPLETED", "RECOMMENDATION_ISSUED", "HIGH_RISK_ALERT"):
            self.assertIn(e, events)
        self.assertEqual(d["result"]["metadata"]["schema_version"], 1)
        self.assertEqual(d["result"]["pipeline"][-1]["key"], "persistence")
        facts = self.container.transactions.facts("TXN001")
        self.assertEqual(len(facts), len(r["facts"]))
        trace = self.container.transactions.trace("TXN001")
        self.assertEqual(len(trace["executions"]), len(r["reasoning_trace"]))
        self.assertEqual(self.container.transactions.explanation("TXN001")["risk_level"], "CRITICAL")
        self.assertEqual(self.container.transactions.rules("TXN001")["triggered"][0]["rule_id"][0], "R")

    def test_duplicate_is_rejected_without_side_effects(self):
        self.container.analysis.analyze(TXN002)
        with self.assertRaises(DuplicateTransactionError):
            self.container.analysis.analyze(TXN002)
        self.assertEqual(self.db.read().transactions.count(), 1)
        rows, _ = self.db.read().audit.search(event_type="DUPLICATE_REJECTED")
        self.assertEqual(len(rows), 1)

    def test_validation_failure_is_audited_and_stores_nothing(self):
        with self.assertRaises(TransactionValidationError):
            self.container.analysis.analyze(tx(amount=0))
        self.assertEqual(self.db.read().transactions.count(), 0)
        rows, _ = self.db.read().audit.search(event_type="VALIDATION_REJECTED")
        self.assertEqual(len(rows), 1)
        with self.assertRaises(TransactionValidationError):
            self.container.analysis.analyze("not a dict")  # type: ignore[arg-type]

    def test_malformed_input_never_crashes_service(self):
        for bad in ({}, {"amount": "x" * 10000}, {**tx(), "transaction_id": None}, {**tx(), "cvv": "123"}):
            with self.assertRaises(TransactionValidationError):
                self.container.analysis.analyze(bad)
        self.container.analysis.analyze(tx(transaction_id="TXNOK1"))

    def test_baseline_is_used_when_user_has_one(self):
        with self.db.unit_of_work() as uow:
            uow.users.upsert("USER001", baseline={"average_amount": 15000, "usual_frequency": 4, "known_devices": ["DEV001"],
                                                    "known_locations": ["Chennai"], "usual_hours": list(range(8, 22))})
        r = self.container.analysis.analyze(TXN001)
        self.assertTrue(r["behavioural_analysis"]["baseline_available"])
        self.assertIn("NewLocation(TXN001)", {f["text"] for f in r["facts"]})
        r2 = self.container.analysis.analyze({**TXN002, "transaction_id": "TXN3", "user_id": "NEWUSER"})
        self.assertFalse(r2["behavioural_analysis"]["baseline_available"])

    def test_not_found(self):
        with self.assertRaises(NotFoundError):
            self.container.transactions.detail("TXN404")
        with self.assertRaises(NotFoundError):
            self.container.reports.generate("TXN404", "json")

    def test_seed_demo_is_idempotent_and_classified_by_engine(self):
        first = self.container.system.seed_demo()
        self.assertEqual(first["failed"], 0)
        self.assertGreaterEqual(first["created"], 70)
        second = self.container.system.seed_demo()
        self.assertEqual((second["created"], second["skipped"]), (0, first["created"]))
        dash = self.container.analytics.dashboard()
        self.assertEqual(dash["total_transactions"], first["created"])
        self.assertEqual(sum(dash["risk_counts"].values()), first["created"])
        for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            self.assertGreater(dash["risk_counts"][level], 0, level)
        self.assertTrue(dash["trend"]["sufficient"])
        self.assertEqual(dash["synthetic_transactions"], first["created"])
        self.assertEqual(self.container.transactions.detail("TXN001")["result"]["risk_level"], "CRITICAL")
        self.assertEqual(self.container.transactions.detail("TXN002")["result"]["risk_level"], "LOW")

    def test_dashboard_and_analytics_empty_state_is_honest(self):
        dash = self.container.analytics.dashboard()
        self.assertEqual((dash["total_transactions"], dash["high_risk_percentage"], dash["recent_analyses"]), (0, 0.0, []))
        self.assertFalse(dash["trend"]["sufficient"])
        an = self.container.analytics.analytics()
        self.assertEqual(an["total_evaluations"], 0)
        self.assertEqual([d["count"] for d in an["risk_distribution"]], [0, 0, 0, 0])

    def test_analytics_reflect_real_data(self):
        self.container.analysis.analyze(TXN001); self.container.analysis.analyze(TXN002)
        an = self.container.analytics.analytics()
        self.assertEqual((an["total_evaluations"], an["critical_count"], an["high_risk_percentage"]), (2, 1, 50.0))
        self.assertEqual({l["location"] for l in an["locations"]}, {"Delhi", "Chennai"})
        self.assertTrue(an["top_rules"])
        self.assertIn("UntrustedDevice", {i["predicate"] for i in an["indicator_frequency"]})

    def test_reports_all_formats_and_audit(self):
        self.container.analysis.analyze(TXN001)
        out = {}
        for fmt in ("json", "csv", "pdf"):
            out[fmt] = self.container.reports.generate("TXN001", fmt)
            path, media, name = self.container.reports.file_for(out[fmt]["report_id"])
            self.assertTrue(path.is_file() and path.stat().st_size == out[fmt]["size_bytes"])
        doc = json.loads(Path(self.container.reports.file_for(out["json"]["report_id"])[0]).read_text(encoding="utf-8"))
        titles = [s["title"] for s in doc["sections"]]
        for t in ("Executive Summary", "Transaction Information", "Input Parameters", "Validation", "Constraints", "Behavioural Analysis",
                  "Extracted Features", "Logical Facts", "Rules Evaluated", "Rules Triggered", "Forward-Chaining Trace",
                  "Risk Classification", "Recommendation", "Audit Metadata"):
            self.assertIn(t, titles)
        rows = list(csv.reader(io.StringIO(Path(self.container.reports.file_for(out["csv"]["report_id"])[0]).read_text(encoding="utf-8-sig"))))
        self.assertTrue(any(r and r[0] == "## Forward-Chaining Trace" for r in rows))
        self.assertTrue(Path(self.container.reports.file_for(out["pdf"]["report_id"])[0]).read_bytes().startswith(b"%PDF"))
        self.assertEqual(len(self.container.reports.list()), 3)
        self.assertEqual(self.container.reports.get_document(out["json"]["report_id"])["transaction_id"], "TXN001")
        rows, total = self.db.read().audit.search(event_type="REPORT_GENERATED")
        self.assertEqual(total, 3)
        with self.assertRaises(ReportError):
            self.container.reports.generate("TXN001", "docx")

    def test_report_files_never_overwrite_and_stay_in_directory(self):
        self.container.analysis.analyze(TXN002)
        a = self.container.reports.generate("TXN002", "json")
        b = self.container.reports.generate("TXN002", "json")
        self.assertNotEqual(a["filename"], b["filename"])
        d = self.container.settings.reports_dir
        self.assertEqual(len(list(d.glob("*.json"))), 2)
        with self.db.unit_of_work() as uow:
            uow.conn.execute("UPDATE reports SET file_path = ? WHERE report_id = ?", (str(d.parent / "evil.txt"), a["report_id"]))
        with self.assertRaises(NotFoundError):
            self.container.reports.file_for(a["report_id"])

    def test_failed_export_does_not_damage_analysis(self):
        self.container.analysis.analyze(TXN002)
        import app.services.report_service as rs
        original = rs.EXPORTERS["pdf"]
        rs.EXPORTERS["pdf"] = (lambda doc: (_ for _ in ()).throw(ReportError("boom")), "application/pdf")
        try:
            with self.assertRaises(ReportError):
                self.container.reports.generate("TXN002", "pdf")
        finally:
            rs.EXPORTERS["pdf"] = original
        self.assertEqual(self.container.transactions.detail("TXN002")["result"]["risk_level"], "LOW")
        failed = [r for r in self.container.reports.list() if r["status"] == "FAILED"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(self.db.read().audit.search(event_type="REPORT_FAILED")[1], 1)

    def test_csv_export_neutralises_formula_injection(self):
        from app.reporting.csv_export import export_csv
        doc = {"title": "t", "report_id": "R", "generated_at": "now",
               "sections": [{"title": "s", "type": "kv", "data": [["k", "=HYPERLINK(\"http://evil\")"]]}]}
        self.assertIn("'=HYPERLINK", export_csv(doc).decode("utf-8-sig"))

    def test_backup_never_overwrites(self):
        self.container.analysis.analyze(TXN002)
        a = self.container.system.backup(); b = self.container.system.backup()
        self.assertNotEqual(a["filename"], b["filename"])
        import sqlite3
        conn = sqlite3.connect(str(self.container.settings.backups_dir / a["filename"]))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 1)
        conn.close()

    def test_health_and_startup(self):
        h = self.container.system.health()
        self.assertEqual((h["status"], h["api"], h["database"], h["rule_engine"], h["knowledge_base"]), ("ok", "ONLINE", "CONNECTED", "READY", "LOADED"))
        self.assertEqual(h["active_rules"], 32)
        self.assertTrue(all(c["status"] == "PASS" for c in self.container.startup_report))
        self.assertEqual(self.container.system.versions()["schema"], 1)

    def test_startup_fails_loudly_when_rules_missing(self):
        from app.core.errors import StartupError
        from app.expert_system.rules.rulebase import parse_rulebase
        from app.expert_system.predicates.registry import default_registry
        with self.assertRaises(RuleBaseError):
            parse_rulebase({"rulebase_version": "1", "rules": []}, default_registry())


class FileHelperTests(unittest.TestCase):
    def test_sanitize_and_containment(self):
        self.assertEqual(sanitize_filename("../../etc/passwd"), "passwd")
        self.assertEqual(sanitize_filename("a b<c>.pdf"), "a_b_c_.pdf")
        self.assertEqual(sanitize_filename("..."), "file")
        import tempfile
        d = Path(tempfile.mkdtemp())
        with self.assertRaises(ValueError):
            ensure_within(d, d / ".." / "x")
        p = unique_path(d, "x.txt"); p.write_text("1")
        self.assertEqual(unique_path(d, "x.txt").name, "x-1.txt")


if __name__ == "__main__":
    unittest.main()
