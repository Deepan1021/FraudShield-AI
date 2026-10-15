"""System-level operations: health, info, startup checks, backup and demo-data seeding."""
from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from app.core.config import Settings
from app.core.errors import FraudShieldError, ReportError, StartupError
from app.core.logging import get_logger
from app.core.version import APP_FULL_NAME, APP_NAME, APP_VERSION, ENGINE_VERSION
from app.database.database import Database
from app.database.migrations import LATEST_SCHEMA_VERSION
from app.pipeline import AnalysisPipeline
from app.services.analysis_service import AnalysisService
from app.utils.files import unique_path
from app.utils.timeutil import utc_now, utc_now_iso, to_iso

_started = time.time()


class SystemService:
    def __init__(self, settings: Settings, db: Database, pipeline: AnalysisPipeline, analysis: AnalysisService):
        self.settings = settings
        self.db = db
        self.pipeline = pipeline
        self.analysis = analysis

    # -- startup -------------------------------------------------------------------------
    def startup_checks(self) -> List[dict]:
        checks: List[dict] = []

        def check(name: str, fn, fatal: bool = True):
            try:
                detail = fn()
                checks.append({"name": name, "status": "PASS", "detail": detail})
            except Exception as exc:  # noqa: BLE001 - reported with an actionable message
                msg = exc.message if isinstance(exc, FraudShieldError) else str(exc)
                checks.append({"name": name, "status": "FAIL" if fatal else "WARN", "detail": msg})
                if fatal:
                    raise StartupError(f"Startup check '{name}' failed: {msg}") from exc

        def db_check():
            version = self.db.initialize()
            problems = self.db.verify_schema()
            if problems:
                raise StartupError("Schema invalid: " + "; ".join(problems))
            return f"{self.db.path.name}, schema v{version}"

        def rules_check():
            n = len(self.pipeline.rulebase.active_rules)
            if n == 0:
                raise StartupError("No active rules loaded.")
            with self.db.unit_of_work() as uow:
                uow.rules.sync(self.pipeline.rulebase.version, [r.to_dict() for r in self.pipeline.rulebase.rules])
            return f"{n} active rules, rule base v{self.pipeline.rulebase.version}"

        def dirs_check():
            for d in (self.settings.reports_dir, self.settings.backups_dir):
                d.mkdir(parents=True, exist_ok=True)
                probe = d / ".write_test"
                probe.write_text("ok")
                probe.unlink()
            return "reports and backups directories writable"

        def data_check():
            for name in ("sample_transactions.csv", "user_baselines.json"):
                p = self.settings.data_dir / name
                if not p.is_file():
                    raise FileNotFoundError(f"{p} is missing (demo data seeding unavailable)")
            return "demo data files readable"

        check("Configuration", lambda: f"environment={self.settings.app_env}")
        check("Database", db_check)
        check("Rule engine", rules_check)
        check("Knowledge base", lambda: f"{len(self.pipeline.registry.all())} predicates loaded")
        check("Writable directories", dirs_check)
        check("Demo data files", data_check, fatal=False)
        return checks

    # -- health / info ---------------------------------------------------------------------
    def health(self) -> dict:
        db_ok = self.db.ping()
        rules = len(self.pipeline.rulebase.active_rules)
        ok = db_ok and rules > 0
        return {
            "status": "ok" if ok else "degraded",
            "api": "ONLINE",
            "database": "CONNECTED" if db_ok else "DISCONNECTED",
            "rule_engine": "READY" if rules > 0 else "ERROR",
            "knowledge_base": "LOADED" if self.pipeline.registry.all() else "EMPTY",
            "active_rules": rules,
            "versions": self.versions(),
            "uptime_seconds": int(time.time() - _started),
            "environment": self.settings.app_env,
        }

    def versions(self) -> dict:
        return {"application": APP_VERSION, "engine": ENGINE_VERSION, "rulebase": self.pipeline.rulebase.version,
                "schema": self.db.schema_version() if self.db.ping() else None, "schema_expected": LATEST_SCHEMA_VERSION}

    def info(self) -> dict:
        return {"name": APP_NAME, "full_name": APP_FULL_NAME, "versions": self.versions(), "config": self.settings.public_dict(),
                "thresholds": self.pipeline.config.to_dict(), "rulebase": {"name": self.pipeline.rulebase.name, "version": self.pipeline.rulebase.version},
                "transaction_count": self.db.read().transactions.count(),
                "synthetic_count": self.db.read().analytics.synthetic_count()}

    # -- backup ----------------------------------------------------------------------------
    def backup(self, actor: str = "analyst") -> dict:
        stamp = utc_now().strftime("%Y%m%d_%H%M%S")
        dest = unique_path(self.settings.backups_dir, f"fraudshield_backup_{stamp}.db")
        try:
            self.db.backup_to(dest)
        except Exception as exc:  # noqa: BLE001
            if dest.exists():
                dest.unlink()
            raise ReportError(f"Database snapshot failed: {exc}") from exc
        with self.db.unit_of_work() as uow:
            uow.audit.add("DATABASE_BACKUP", f"Database snapshot written to {dest.name}", actor,
                          rulebase_version=self.pipeline.rulebase.version, metadata={"filename": dest.name, "size_bytes": dest.stat().st_size})
        return {"filename": dest.name, "size_bytes": dest.stat().st_size, "created_at": utc_now_iso()}

    # -- demo data ---------------------------------------------------------------------------
    def seed_demo(self, actor: str = "system") -> dict:
        data_dir = self.settings.data_dir
        try:
            baselines = json.loads((data_dir / "user_baselines.json").read_text(encoding="utf-8"))["users"]
            with open(data_dir / "sample_transactions.csv", newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
        except (OSError, ValueError, KeyError) as exc:
            raise ReportError(f"Demo data files could not be read from {data_dir}: {exc}") from exc
        now = utc_now()
        with self.db.unit_of_work() as uow:
            for uid, b in baselines.items():
                uow.users.upsert(uid, baseline={k: v for k, v in b.items() if k != "display_name"},
                                 display_name=b.get("display_name"), is_synthetic=True)
        created = skipped = failed = 0
        for row in rows:
            days_ago = int(row.pop("days_ago", 0) or 0)
            raw = {k: v for k, v in row.items() if v != ""}
            if self.db.read().transactions.exists(raw["transaction_id"].upper()):
                skipped += 1
                continue
            hh, mm = [int(x) for x in raw["transaction_time"].split(":")[:2]]
            when = (now - timedelta(days=days_ago)).replace(hour=hh, minute=mm, second=0, microsecond=0)
            if when > now:
                when = now
            try:
                self.analysis.analyze(raw, actor=actor, is_synthetic=True, submitted_at=to_iso(when))
                created += 1
            except FraudShieldError as exc:
                failed += 1
                get_logger().warning("Demo row %s skipped: %s", raw.get("transaction_id"), exc.message)
        with self.db.unit_of_work() as uow:
            uow.audit.add("DEMO_DATA_SEEDED", f"Synthetic demonstration data seeded: {created} created, {skipped} already present",
                          actor, rulebase_version=self.pipeline.rulebase.version, metadata={"created": created, "skipped": skipped, "failed": failed})
        return {"created": created, "skipped": skipped, "failed": failed, "label": "Synthetic Demonstration Data"}
