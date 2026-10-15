import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.core.errors import ConfigurationError, DatabaseError
from app.database.database import Database, sqlite_path_from_url
from app.database.migrations import LATEST_SCHEMA_VERSION
from app.pipeline import analyze_transaction
from tests.helpers import TXN001, TXN002, baseline


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.db = Database(self.dir / "t.db")
        self.db.initialize()

    def tearDown(self):
        self.db.close_all()

    def save(self, raw, synthetic=False, at="2026-10-01T10:00:00Z"):
        result = analyze_transaction(raw, baseline() if raw["user_id"] == "USER001" else None)
        with self.db.unit_of_work() as uow:
            uow.users.upsert(result["user_id"])
            pk = uow.transactions.insert(result["input_snapshot"], at, synthetic)
            uow.transactions.add_features(pk, result["features"])
            uow.facts.add_many(pk, result["facts"])
            inf = uow.inference.save_result(pk, result, "summary", LATEST_SCHEMA_VERSION, at)
            uow.inference.add_executions(pk, inf, "1.0.0", result["reasoning_trace"])
            uow.inference.add_recommendation(pk, inf, result["recommendation"], at)
        return pk, result

    def test_schema_and_version(self):
        self.assertEqual(self.db.schema_version(), LATEST_SCHEMA_VERSION)
        self.assertEqual(self.db.verify_schema(), [])
        self.assertEqual(self.db.initialize(), LATEST_SCHEMA_VERSION)  # idempotent
        conn = self.db.connection()
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        idx = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        for name in ("idx_tx_user", "idx_inf_risk", "idx_exec_rule", "idx_audit_ts", "idx_facts_tx"):
            self.assertIn(name, idx)

    def test_newer_schema_is_refused(self):
        self.db.connection().execute("INSERT INTO schema_version VALUES (99, 'future', 'x')")
        with self.assertRaises(DatabaseError):
            Database(self.dir / "t.db").initialize()

    def test_foreign_keys_and_unique_ids(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db.unit_of_work() as uow:
                uow.transactions.insert({**analyze_transaction(TXN002)["input_snapshot"]}, "2026-10-01T10:00:00Z")  # user missing
        self.save(TXN002)
        with self.assertRaises(sqlite3.IntegrityError):
            self.save(TXN002)

    def test_failed_unit_of_work_rolls_back_everything(self):
        result = analyze_transaction(TXN001, baseline())
        with self.assertRaises(RuntimeError):
            with self.db.unit_of_work() as uow:
                uow.users.upsert("USER001")
                pk = uow.transactions.insert(result["input_snapshot"], "2026-10-01T10:00:00Z")
                uow.facts.add_many(pk, result["facts"])
                raise RuntimeError("simulated failure")
        self.assertEqual(self.db.read().transactions.count(), 0)
        self.assertEqual(self.db.read().users.count(), 0)
        self.assertEqual(self.db.connection().execute("SELECT COUNT(*) FROM facts").fetchone()[0], 0)

    def test_roundtrip_and_cascade(self):
        pk, result = self.save(TXN001)
        r = self.db.read()
        self.assertEqual(r.inference.get_result(pk)["risk_level"], "CRITICAL")
        self.assertEqual(len(r.facts.for_transaction(pk)), len(result["facts"]))
        self.assertEqual(len(r.inference.executions(pk)), len(result["reasoning_trace"]))
        self.assertTrue(any(f["name"] == "high_amount" and f["value"] is True for f in r.transactions.get_features(pk)))
        with self.db.unit_of_work() as uow:
            uow.conn.execute("DELETE FROM transactions WHERE id = ?", (pk,))
        self.assertEqual(self.db.connection().execute("SELECT COUNT(*) FROM rule_executions").fetchone()[0], 0)

    def test_search_filters_sorting_and_paging(self):
        self.save(TXN001, at="2026-10-01T02:15:00Z")
        self.save(TXN002, at="2026-10-05T14:30:00Z")
        r = self.db.read().transactions
        rows, total = r.search(risk=["CRITICAL"])
        self.assertEqual((total, rows[0]["transaction_id"]), (1, "TXN001"))
        self.assertEqual(r.search(q="txn00")[1], 2)
        self.assertEqual(r.search(location="delhi")[1], 1)
        self.assertEqual(r.search(device_trust="TRUSTED")[1], 1)
        self.assertEqual(r.search(rule="R40")[1], 1)
        self.assertEqual(r.search(recommendation="APPROVE")[1], 1)
        self.assertEqual(r.search(date_from="2026-10-03")[1], 1)
        self.assertEqual(r.search(date_to="2026-10-03")[1], 1)
        self.assertEqual([x["transaction_id"] for x in r.search(sort="amount", order="asc")[0]], ["TXN002", "TXN001"])
        rows, total = r.search(page=2, page_size=1)
        self.assertEqual((len(rows), total), (1, 2))

    def test_search_is_injection_safe(self):
        self.save(TXN002)
        r = self.db.read().transactions
        for evil in ("'; DROP TABLE transactions;--", "%", "_", "\\", "' OR '1'='1"):
            rows, total = r.search(q=evil, location=evil)
            self.assertEqual(total, 0, evil)
        rows, _ = r.search(sort="amount; DROP TABLE users", order="asc; --")
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.db.read().transactions.count(), 1)

    def test_rules_sync_is_idempotent(self):
        from app.expert_system.rules.rulebase import default_rulebase
        rb = default_rulebase()
        with self.db.unit_of_work() as uow:
            self.assertEqual(uow.rules.sync(rb.version, [r.to_dict() for r in rb.rules]), 32)
            self.assertEqual(uow.rules.sync(rb.version, [r.to_dict() for r in rb.rules]), 0)
        self.assertEqual(len(self.db.read().rules.list(rb.version)), 32)

    def test_audit_and_analytics_repositories(self):
        self.save(TXN001); self.save(TXN002)
        with self.db.unit_of_work() as uow:
            uow.audit.add("TEST_EVENT", "hello", "tester", "TXN001", "CRITICAL", "R40", "1.0.0", metadata={"a": 1})
        rows, total = self.db.read().audit.search(event_type="TEST_EVENT")
        self.assertEqual((total, rows[0]["metadata"], rows[0]["app_version"], rows[0]["engine_version"]), (1, {"a": 1}, "1.0.0", "1.0.0"))
        a = self.db.read().analytics
        self.assertEqual({d["risk_level"]: d["count"] for d in a.risk_distribution()}, {"LOW": 1, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 1})
        self.assertEqual(a.totals()["total"], 2)
        self.assertEqual(a.top_rules(3)[0]["rule_id"] in {"R01", "R04", "R05", "R06", "R12", "R13"}, True)
        self.assertEqual(sum(1 for x in a.recommendation_distribution() if x["count"]), 2)

    def test_url_parsing(self):
        self.assertEqual(sqlite_path_from_url("sqlite:///database/x.db", Path("/root")), Path("/root/database/x.db"))
        with self.assertRaises(ConfigurationError):
            sqlite_path_from_url("postgresql://u:p@h/db", Path("/root"))

    def test_unwritable_location_gives_actionable_error(self):
        blocker = self.dir / "file.txt"; blocker.write_text("x")
        with self.assertRaises(DatabaseError) as ctx:
            Database(blocker / "sub" / "x.db").connection()
        self.assertIn("Cannot open database", ctx.exception.message)


if __name__ == "__main__":
    unittest.main()
