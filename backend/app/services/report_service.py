"""ReportService: builds, exports and records reports. A failed report never affects the analysis."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from app.core.errors import NotFoundError, ReportError
from app.core.logging import get_logger
from app.database.database import Database
from app.reporting.builder import build_report
from app.reporting.csv_export import export_csv
from app.reporting.json_export import export_json
from app.reporting.pdf_export import export_pdf
from app.utils.files import ensure_within, sanitize_filename, unique_path
from app.utils.timeutil import utc_now_iso

EXPORTERS = {"json": (export_json, "application/json"), "csv": (export_csv, "text/csv"), "pdf": (export_pdf, "application/pdf")}


class ReportService:
    def __init__(self, db: Database, reports_dir: Path, rulebase_version: str):
        self.db = db
        self.reports_dir = reports_dir
        self.rulebase_version = rulebase_version

    def _load(self, transaction_id: str):
        uow = self.db.read()
        row = uow.transactions.get(transaction_id.strip().upper())
        if not row:
            raise NotFoundError(f"Transaction {transaction_id} was not found.", field="transaction_id")
        result = uow.inference.get_result(row["pk"])
        return row, result, uow.audit.for_transaction(row["transaction_id"])

    def view(self, transaction_id: str) -> dict:
        row, result, audit = self._load(transaction_id)
        return build_report(result, row, audit)

    def generate(self, transaction_id: str, fmt: str = "json", actor: str = "analyst") -> dict:
        fmt = (fmt or "json").lower()
        if fmt not in EXPORTERS:
            raise ReportError(f"Unsupported report format '{fmt}'. Choose one of: {', '.join(EXPORTERS)}.", field="format")
        row, result, audit = self._load(transaction_id)
        report_id = "RPT-" + uuid.uuid4().hex[:10].upper()
        report = build_report(result, row, audit, report_id)
        now = utc_now_iso()
        tid = row["transaction_id"]
        try:
            data = EXPORTERS[fmt][0](report)
            filename = sanitize_filename(f"fraudshield_report_{tid}_{now.replace(':', '').replace('-', '')}.{fmt}")
            path = unique_path(self.reports_dir, filename)
            path.write_bytes(data)
        except ReportError as exc:
            self._record(row, report_id, fmt, None, None, None, "FAILED", exc.message, now, actor, tid)
            raise
        except (OSError, ValueError) as exc:
            self._record(row, report_id, fmt, None, None, None, "FAILED", str(exc), now, actor, tid)
            raise ReportError(f"Report export failed: {exc}") from exc
        self._record(row, report_id, fmt, path.name, str(path), len(data), "COMPLETED", None, now, actor, tid)
        get_logger().info("report=%s transaction=%s format=%s bytes=%s", report_id, tid, fmt, len(data))
        return {"report_id": report_id, "format": fmt, "filename": path.name, "size_bytes": len(data), "created_at": now,
                "download_url": f"/api/reports/{report_id}/download", "report": report}

    def _record(self, row, report_id, fmt, filename, file_path, size, status, error, now, actor, tid) -> None:
        with self.db.unit_of_work() as uow:
            uow.reports.add(report_id, row["pk"], fmt, filename, file_path, size, status, error, now)
            if status == "COMPLETED":
                uow.audit.add("REPORT_GENERATED", f"{fmt.upper()} report {report_id} generated for {tid}", actor, tid,
                              row.get("risk_level"), rulebase_version=self.rulebase_version, metadata={"report_id": report_id, "filename": filename})
            else:
                uow.audit.add("REPORT_FAILED", f"{fmt.upper()} report for {tid} failed: {error}", actor, tid,
                              row.get("risk_level"), rulebase_version=self.rulebase_version, metadata={"report_id": report_id})

    def list(self, limit: int = 100) -> list:
        return self.db.read().reports.list(limit)

    def get_document(self, report_id: str) -> dict:
        rec = self._record_row(report_id)
        row, result, audit = self._load(rec["transaction_id"])
        return build_report(result, row, audit, report_id)

    def _record_row(self, report_id: str) -> dict:
        rec = self.db.read().reports.get(report_id)
        if not rec:
            raise NotFoundError(f"Report {report_id} was not found.", field="report_id")
        return rec

    def file_for(self, report_id: str):
        rec = self._record_row(report_id)
        if rec["status"] != "COMPLETED" or not rec["file_path"]:
            raise NotFoundError(f"Report {report_id} has no exported file.", field="report_id")
        try:
            path = ensure_within(self.reports_dir, Path(rec["file_path"]))
        except ValueError:
            raise NotFoundError("Report file is outside the permitted directory.") from None
        if not path.is_file():
            raise NotFoundError(f"Report file {rec['filename']} no longer exists on disk.")
        return path, EXPORTERS[rec["format"]][1], rec["filename"]
