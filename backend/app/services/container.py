"""Composition root: wires settings, database, engine and services."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from app.core.config import PROJECT_ROOT, Settings, load_settings
from app.core.logging import get_logger, setup_logging
from app.database.database import Database, sqlite_path_from_url
from app.pipeline import AnalysisPipeline
from app.services.analysis_service import AnalysisService
from app.services.analytics_service import AnalyticsService
from app.services.report_service import ReportService
from app.services.system_service import SystemService
from app.services.transaction_service import TransactionService


@dataclass
class Container:
    settings: Settings
    db: Database
    pipeline: AnalysisPipeline
    analysis: AnalysisService
    transactions: TransactionService
    analytics: AnalyticsService
    reports: ReportService
    system: SystemService
    startup_report: List[dict] = field(default_factory=list)


def build_container(settings: Settings | None = None, pipeline: AnalysisPipeline | None = None) -> Container:
    settings = settings or load_settings()
    setup_logging(settings.log_level, settings.logs_dir)
    log = get_logger()
    db = Database(sqlite_path_from_url(settings.database_url, PROJECT_ROOT))
    pipeline = pipeline or AnalysisPipeline()
    analysis = AnalysisService(db, pipeline)
    system = SystemService(settings, db, pipeline, analysis)
    container = Container(
        settings=settings, db=db, pipeline=pipeline, analysis=analysis, transactions=TransactionService(db),
        analytics=AnalyticsService(db), reports=ReportService(db, settings.reports_dir, pipeline.rulebase.version), system=system)
    container.startup_report = system.startup_checks()
    for c in container.startup_report:
        log.info("startup check %-20s %s %s", c["name"], c["status"], c["detail"])
    with db.unit_of_work() as uow:
        uow.audit.add("SYSTEM_STARTUP", f"FraudShield AI started ({settings.app_env})", "system", rulebase_version=pipeline.rulebase.version)
    if settings.auto_seed_demo and db.read().transactions.count() == 0:
        log.info("AUTO_SEED_DEMO enabled: seeding synthetic demonstration data")
        system.seed_demo()
    return container
