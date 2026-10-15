"""Dashboard and analytics aggregation. Every figure is computed from the database."""
from __future__ import annotations

from app.database.database import Database


class AnalyticsService:
    def __init__(self, db: Database):
        self.db = db

    def dashboard(self) -> dict:
        a = self.db.read().analytics
        totals = a.totals()
        dist = {d["risk_level"]: d["count"] for d in a.risk_distribution()}
        rec = {d["action"]: d["count"] for d in a.recommendation_distribution()}
        total = totals["total"]
        trend = a.trend(14)
        return {
            "total_transactions": total,
            "risk_counts": dist,
            "low": dist["LOW"], "medium": dist["MEDIUM"], "high": dist["HIGH"], "critical": dist["CRITICAL"],
            "blocked_or_flagged": rec["TEMPORARILY_BLOCK"] + rec["FLAG_FOR_ANALYST_REVIEW"],
            "high_risk_percentage": round(100.0 * (dist["HIGH"] + dist["CRITICAL"]) / total, 1) if total else 0.0,
            "avg_processing_ms": totals["avg_processing_ms"],
            "risk_distribution": a.risk_distribution(),
            "recent_alerts": a.recent(6, ["HIGH", "CRITICAL"]),
            "recent_analyses": a.recent(8),
            "trend": {"days": trend, "sufficient": len(trend) >= 2},
            "top_rules": a.top_rules(5),
            "synthetic_transactions": a.synthetic_count(),
        }

    def analytics(self) -> dict:
        a = self.db.read().analytics
        totals = a.totals()
        dist = a.risk_distribution()
        counts = {d["risk_level"]: d["count"] for d in dist}
        total = totals["total"]
        trend = a.trend(30)
        return {
            "total_evaluations": total,
            "avg_processing_ms": totals["avg_processing_ms"],
            "avg_severity_index": totals["avg_severity_index"],
            "high_risk_percentage": round(100.0 * (counts["HIGH"] + counts["CRITICAL"]) / total, 1) if total else 0.0,
            "critical_count": counts["CRITICAL"],
            "risk_distribution": dist,
            "recommendation_distribution": a.recommendation_distribution(),
            "trend": {"days": trend, "sufficient": len(trend) >= 2},
            "locations": [{**r, "high_risk": int(r["high_risk"] or 0)} for r in a.locations(10)],
            "device_anomalies": [{**r, "high_risk": int(r["high_risk"] or 0)} for r in a.device_anomalies()],
            "behavioural_anomalies": a.behavioural_anomalies(),
            "indicator_frequency": a.indicator_frequency(),
            "top_rules": a.top_rules(10),
        }
