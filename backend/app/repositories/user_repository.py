from __future__ import annotations

import json
from typing import Optional

from app.domain.models import BaselineProfile
from app.repositories.base import BaseRepository, dumps
from app.utils.timeutil import utc_now_iso


class UserRepository(BaseRepository):
    def upsert(self, user_id: str, baseline: Optional[dict] = None, display_name: Optional[str] = None,
               is_synthetic: bool = False, now: Optional[str] = None) -> None:
        now = now or utc_now_iso()
        existing = self._one("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if existing is None:
            self.conn.execute(
                "INSERT INTO users(user_id, display_name, baseline_json, is_synthetic, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                (user_id, display_name, dumps(baseline) if baseline is not None else None, int(is_synthetic), now, now))
        elif baseline is not None:
            self.conn.execute("UPDATE users SET baseline_json = ?, display_name = COALESCE(?, display_name), updated_at = ? WHERE user_id = ?",
                              (dumps(baseline), display_name, now, user_id))

    def get_baseline(self, user_id: str) -> Optional[BaselineProfile]:
        row = self._one("SELECT baseline_json FROM users WHERE user_id = ?", (user_id,))
        if not row or not row["baseline_json"]:
            return None
        return BaselineProfile.from_dict(user_id, json.loads(row["baseline_json"]))

    def count(self) -> int:
        return int(self._scalar("SELECT COUNT(*) FROM users"))
