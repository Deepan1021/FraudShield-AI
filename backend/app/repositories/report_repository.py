from __future__ import annotations

from typing import List, Optional

from app.repositories.base import BaseRepository


class ReportRepository(BaseRepository):
    def add(self, report_id: str, pk: int, fmt: str, filename: Optional[str], file_path: Optional[str],
            size_bytes: Optional[int], status: str, error: Optional[str], created_at: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO reports(report_id, transaction_pk, format, filename, file_path, size_bytes, status, error, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (report_id, pk, fmt, filename, file_path, size_bytes, status, error, created_at))
        return int(cur.lastrowid)

    def get(self, report_id: str) -> Optional[dict]:
        return self._one("SELECT r.*, t.transaction_id FROM reports r JOIN transactions t ON t.id = r.transaction_pk WHERE r.report_id = ?", (report_id,))

    def list(self, limit: int = 100) -> List[dict]:
        return self._all("SELECT r.report_id, r.format, r.filename, r.size_bytes, r.status, r.error, r.created_at, t.transaction_id "
                         "FROM reports r JOIN transactions t ON t.id = r.transaction_pk ORDER BY r.created_at DESC, r.id DESC LIMIT ?",
                         (max(1, min(500, limit)),))
