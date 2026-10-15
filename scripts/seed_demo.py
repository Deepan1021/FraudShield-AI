"""Seed the labelled synthetic demonstration data (idempotent; every row is classified by the rule engine)."""
import _bootstrap  # noqa: F401

from app.services.container import build_container

c = build_container()
result = c.system.seed_demo(actor="cli")
print(result)
dash = c.analytics.dashboard()
print("Risk distribution:", dash["risk_counts"])
c.db.close_all()
