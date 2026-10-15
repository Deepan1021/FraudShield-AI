import os
import shutil
import tempfile
from pathlib import Path

from app.core.config import PROJECT_ROOT, Settings
from app.domain.models import BaselineProfile
from app.services.container import build_container

BASELINE = {"average_amount": 15000, "usual_frequency": 4, "known_devices": ["DEV001"],
            "known_locations": ["Chennai"], "usual_hours": list(range(8, 22))}


def baseline() -> BaselineProfile:
    return BaselineProfile.from_dict("USER001", BASELINE)


def tx(**over) -> dict:
    """A normal USER001 transaction; override fields to build scenarios."""
    base = {"transaction_id": "TXN900", "user_id": "USER001", "amount": 9000, "transaction_time": "11:00",
            "device_trust": "TRUSTED", "device_id": "DEV001", "location": "Chennai", "login_behavior": "NORMAL",
            "transaction_frequency": 2, "account_activity": "ACTIVE"}
    base.update(over)
    return base


TXN001 = {"transaction_id": "TXN001", "user_id": "USER001", "amount": 85000, "transaction_time": "02:15 AM",
          "device_trust": "Untrusted", "location": "Delhi", "login_behavior": "Suspicious",
          "transaction_frequency": 12, "account_activity": "Active"}
TXN002 = {"transaction_id": "TXN002", "user_id": "USER002", "amount": 2500, "transaction_time": "14:30",
          "device_trust": "Trusted", "location": "Chennai", "login_behavior": "Normal",
          "transaction_frequency": 2, "account_activity": "Active"}


def make_settings(tmp: Path) -> Settings:
    return Settings(app_env="test", database_url=f"sqlite:///{(tmp / 'test.db').as_posix()}", log_level="WARNING",
                    api_host="127.0.0.1", api_port=8000, cors_origins=["http://localhost:5173"], max_request_bytes=1_000_000,
                    reports_dir=tmp / "reports", backups_dir=tmp / "backups", data_dir=PROJECT_ROOT / "data",
                    logs_dir=tmp / "logs", frontend_dist=tmp / "dist", serve_frontend=False, auto_seed_demo=False)


class TempContainer:
    """Context manager / mixin helper creating an isolated container in a temp directory."""

    def setup_container(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="fraudshield_test_"))
        self.container = build_container(make_settings(self._tmp))
        self.db = self.container.db
        return self.container

    def teardown_container(self):
        self.container.db.close_all()
        shutil.rmtree(self._tmp, ignore_errors=True)
