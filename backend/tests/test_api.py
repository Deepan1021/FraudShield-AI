"""HTTP API tests. They need fastapi + httpx (pip install -r backend/requirements.txt).
They are skipped automatically when those packages are not installed."""
import unittest

try:
    from fastapi.testclient import TestClient
    HAVE_WEB = True
except Exception:  # pragma: no cover - environment without web dependencies
    HAVE_WEB = False

from tests.helpers import TXN001, TXN002, TempContainer, tx


@unittest.skipUnless(HAVE_WEB, "fastapi/httpx not installed (offline environment)")
class ApiTests(TempContainer, unittest.TestCase):
    def setUp(self):
        from app.main import create_app
        self.setup_container()
        self.app = create_app(self.container)
        self.ctx = TestClient(self.app)
        self.client = self.ctx.__enter__()

    def tearDown(self):
        self.ctx.__exit__(None, None, None)
        self.container.db.close_all()
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        d = r.json()["data"]
        self.assertEqual((d["api"], d["database"], d["rule_engine"], d["knowledge_base"]), ("ONLINE", "CONNECTED", "READY", "LOADED"))

    def test_analyze_and_read_back(self):
        r = self.client.post("/api/transactions/analyze", json={**TXN001, "transaction_id": "TXN100"})
        self.assertEqual(r.status_code, 201, r.text)
        data = r.json()["data"]
        self.assertEqual((data["risk_level"], data["recommendation"]["action"]), ("CRITICAL", "FLAG_FOR_ANALYST_REVIEW"))
        for path in ("", "/facts", "/rules", "/trace", "/explanation", "/report"):
            self.assertEqual(self.client.get(f"/api/transactions/TXN100{path}").status_code, 200, path)
        lst = self.client.get("/api/transactions?risk=CRITICAL&page_size=5").json()["data"]
        self.assertEqual(lst["total"], 1)
        self.assertEqual(self.client.get("/api/dashboard/summary").json()["data"]["critical"], 1)
        self.assertEqual(self.client.get("/api/analytics").json()["data"]["total_evaluations"], 1)

    def test_validation_errors_are_structured(self):
        r = self.client.post("/api/transactions/analyze", json={**TXN002, "amount": 0})
        self.assertEqual(r.status_code, 422)
        body = r.json()
        self.assertFalse(body["success"])
        self.assertEqual((body["error"]["code"], body["error"]["field"], body["error"]["message"]),
                         ("VALIDATION_ERROR", "amount", "Transaction amount must be greater than zero."))
        r = self.client.post("/api/transactions/analyze", json={**TXN002, "amount": "abc"})
        self.assertEqual((r.status_code, r.json()["error"]["field"]), (422, "amount"))
        r = self.client.post("/api/transactions/analyze", json={**TXN002, "cvv": "123"})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "UNKNOWN_FIELD"))
        r = self.client.post("/api/transactions/analyze", content=b"{not json", headers={"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 422)

    def test_duplicate_and_not_found(self):
        self.assertEqual(self.client.post("/api/transactions/analyze", json=TXN002).status_code, 201)
        r = self.client.post("/api/transactions/analyze", json=TXN002)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "DUPLICATE_TRANSACTION"))
        r = self.client.get("/api/transactions/TXN404")
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (404, "NOT_FOUND"))
        self.assertEqual(self.client.get("/api/nope").status_code, 404)
        self.assertEqual(self.client.get("/api/transactions/..%2F..%2Fetc").status_code, 404)

    def test_query_validation_and_injection(self):
        self.assertEqual(self.client.get("/api/transactions?risk=BOGUS").status_code, 422)
        self.assertEqual(self.client.get("/api/transactions?page_size=1000").status_code, 422)
        self.assertEqual(self.client.get("/api/transactions?sort=amount;drop").status_code, 422)
        self.assertEqual(self.client.get("/api/transactions", params={"q": "' OR 1=1 --"}).json()["data"]["total"], 0)

    def test_oversized_request_rejected(self):
        r = self.client.post("/api/transactions/analyze", content=b"x" * 2_000_000, headers={"Content-Type": "application/json"})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (413, "REQUEST_TOO_LARGE"))

    def test_rules_knowledge_base_and_audit(self):
        rules = self.client.get("/api/rules").json()["data"]
        self.assertEqual((rules["version"], len(rules["rules"])), ("1.0.0", 32))
        kb = self.client.get("/api/knowledge-base").json()["data"]
        self.assertEqual(kb["status"], "LOADED")
        self.assertTrue(kb["rule_dependencies"])
        self.client.post("/api/transactions/analyze", json=TXN002)
        logs = self.client.get("/api/audit-logs?transaction_id=txn002").json()["data"]
        self.assertGreaterEqual(logs["total"], 3)

    def test_reports_flow(self):
        self.client.post("/api/transactions/analyze", json=TXN001)
        r = self.client.post("/api/reports", json={"transaction_id": "TXN001", "format": "pdf"})
        self.assertEqual(r.status_code, 201, r.text)
        rid = r.json()["data"]["report_id"]
        dl = self.client.get(f"/api/reports/{rid}/download")
        self.assertEqual((dl.status_code, dl.headers["content-type"]), (200, "application/pdf"))
        self.assertTrue(dl.content.startswith(b"%PDF"))
        self.assertEqual(self.client.get(f"/api/reports/{rid}").status_code, 200)
        self.assertEqual(len(self.client.get("/api/reports").json()["data"]), 1)
        self.assertEqual(self.client.post("/api/reports", json={"transaction_id": "TXN001", "format": "exe"}).status_code, 422)
        self.assertEqual(self.client.post("/api/reports", json={"transaction_id": "TXN999", "format": "json"}).status_code, 404)

    def test_system_endpoints(self):
        self.assertEqual(self.client.post("/api/system/seed-demo").status_code, 201)
        self.assertEqual(self.client.get("/api/dashboard/summary").json()["data"]["total_transactions"] >= 70, True)
        self.assertEqual(self.client.post("/api/system/backup").status_code, 201)
        self.assertIn("config", self.client.get("/api/system/info").json()["data"])

    def test_security_headers_and_cors(self):
        r = self.client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(r.headers["x-content-type-options"], "nosniff")
        self.assertEqual(r.headers["access-control-allow-origin"], "http://localhost:5173")
        r = self.client.get("/api/health", headers={"Origin": "http://evil.example"})
        self.assertNotIn("access-control-allow-origin", r.headers)

    def test_no_stack_traces_in_errors(self):
        original = self.container.analytics.dashboard
        self.container.analytics.dashboard = lambda: (_ for _ in ()).throw(RuntimeError("secret internals"))
        try:
            r = self.ctx.__class__(self.app, raise_server_exceptions=False).get("/api/dashboard/summary")
        finally:
            self.container.analytics.dashboard = original
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("secret internals", r.text)
        self.assertEqual(r.json()["error"]["code"], "INTERNAL_ERROR")


if __name__ == "__main__":
    unittest.main()
