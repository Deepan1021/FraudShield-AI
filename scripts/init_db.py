"""Create or upgrade the database schema and synchronise the rule base (idempotent)."""
import _bootstrap  # noqa: F401

from app.services.container import build_container

c = build_container()
print("Startup checks:")
for check in c.startup_report:
    print(f"  [{check['status']}] {check['name']}: {check['detail']}")
print(f"Database ready at {c.db.path}")
c.db.close_all()
