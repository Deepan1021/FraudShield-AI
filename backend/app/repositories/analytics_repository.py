"""Aggregate queries. Every number shown in the dashboard and analytics views comes from here."""
from __future__ import annotations

from typing import List, Optional

from app.repositories.base import BaseRepository

LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
ACTIONS = ["APPROVE", "REQUEST_MFA", "TEMPORARILY_BLOCK", "FLAG_FOR_ANALYST_REVIEW"]


class AnalyticsRepository(BaseRepository):
    def totals(self) -> dict:
        row = self._one("""SELECT COUNT(*) AS total, COALESCE(AVG(processing_time_ms), 0) AS avg_ms,
                           COALESCE(AVG(severity_index), 0) AS avg_index FROM inference_results""")
        return {"total": int(row["total"]), "avg_processing_ms": round(float(row["avg_ms"]), 2), "avg_severity_index": round(float(row["avg_index"]), 1)}

    def risk_distribution(self) -> List[dict]:
        counts = {r["risk_level"]: r["n"] for r in self._all("SELECT risk_level, COUNT(*) AS n FROM inference_results GROUP BY risk_level")}
        return [{"risk_level": lv, "count": int(counts.get(lv, 0))} for lv in LEVELS]

    def recommendation_distribution(self) -> List[dict]:
        counts = {r["action"]: r["n"] for r in self._all("SELECT action, COUNT(*) AS n FROM recommendations GROUP BY action")}
        return [{"action": a, "count": int(counts.get(a, 0))} for a in ACTIONS]

    def trend(self, days: int = 30) -> List[dict]:
        rows = self._all(
            """SELECT date(created_at) AS day, COUNT(*) AS total,
               SUM(risk_level = 'LOW') AS low, SUM(risk_level = 'MEDIUM') AS medium,
               SUM(risk_level = 'HIGH') AS high, SUM(risk_level = 'CRITICAL') AS critical
               FROM inference_results WHERE date(created_at) >= date('now', ?) GROUP BY day ORDER BY day""", (f"-{int(days)} days",))
        return [{"day": r["day"], "total": int(r["total"]), "low": int(r["low"] or 0), "medium": int(r["medium"] or 0),
                 "high": int(r["high"] or 0), "critical": int(r["critical"] or 0)} for r in rows]

    def top_rules(self, limit: int = 10) -> List[dict]:
        return self._all(
            """SELECT rule_id, rule_name, category, COUNT(*) AS firings, COUNT(DISTINCT transaction_pk) AS transactions
               FROM rule_executions GROUP BY rule_id, rule_name, category ORDER BY firings DESC, rule_id LIMIT ?""", (limit,))

    def locations(self, limit: int = 10) -> List[dict]:
        return self._all(
            """SELECT t.location, COUNT(*) AS transactions,
               SUM(i.risk_level IN ('HIGH','CRITICAL')) AS high_risk
               FROM transactions t JOIN inference_results i ON i.transaction_pk = t.id
               GROUP BY t.location ORDER BY transactions DESC, t.location LIMIT ?""", (limit,))

    def device_anomalies(self) -> List[dict]:
        return self._all(
            """SELECT t.device_trust, COUNT(*) AS transactions, SUM(i.risk_level IN ('HIGH','CRITICAL')) AS high_risk
               FROM transactions t JOIN inference_results i ON i.transaction_pk = t.id GROUP BY t.device_trust ORDER BY transactions DESC""")

    def behavioural_anomalies(self) -> List[dict]:
        return self._all(
            """SELECT predicate, COUNT(*) AS occurrences FROM facts WHERE kind IN ('behavioural','constraint')
               AND predicate NOT IN ('KnownLocation','UsualHour') GROUP BY predicate ORDER BY occurrences DESC""")

    def indicator_frequency(self) -> List[dict]:
        return self._all(
            """SELECT predicate, COUNT(*) AS occurrences FROM facts WHERE kind = 'observed'
               AND predicate IN ('HighAmount','UntrustedDevice','UnknownDevice','NightTransaction','HighFrequency',
               'SuspiciousLogin','FailedLoginAttempts','UnusualLogin','DormantAccount','RecentlyReactivated','SuspiciousAccountActivity')
               GROUP BY predicate ORDER BY occurrences DESC""")

    def recent(self, limit: int = 8, risks: Optional[List[str]] = None) -> List[dict]:
        where, params = "", []
        if risks:
            where = f"WHERE i.risk_level IN ({','.join('?' * len(risks))})"
            params = list(risks)
        return self._all(
            f"""SELECT t.transaction_id, t.user_id, t.amount, t.currency, t.location, t.submitted_at, i.risk_level,
               i.severity_index, i.summary, r.action AS recommendation_action, r.label AS recommendation_label
               FROM inference_results i JOIN transactions t ON t.id = i.transaction_pk
               JOIN recommendations r ON r.transaction_pk = t.id {where}
               ORDER BY i.created_at DESC, i.id DESC LIMIT ?""", params + [limit])

    def synthetic_count(self) -> int:
        return int(self._scalar("SELECT COUNT(*) FROM transactions WHERE is_synthetic = 1"))
