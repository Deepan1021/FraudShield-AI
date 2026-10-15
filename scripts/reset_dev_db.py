"""Development-only database reset. Refuses to run unless APP_ENV=development and --yes is given."""
import _bootstrap  # noqa: F401
import sys

from app.core.config import PROJECT_ROOT, load_settings
from app.database.database import sqlite_path_from_url

settings = load_settings()
if settings.app_env != "development":
    sys.exit(f"Refusing to reset: APP_ENV is '{settings.app_env}', not 'development'.")
if "--yes" not in sys.argv:
    sys.exit("This deletes the local SQLite database. Re-run with --yes to confirm.")
path = sqlite_path_from_url(settings.database_url, PROJECT_ROOT)
removed = []
for suffix in ("", "-wal", "-shm"):
    p = path.with_name(path.name + suffix)
    if p.exists():
        p.unlink()
        removed.append(p.name)
print("Removed:", ", ".join(removed) if removed else "nothing (database did not exist)")
