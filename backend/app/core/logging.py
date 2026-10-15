"""Logging setup: application, inference and error logs with levels INFO/WARNING/ERROR/CRITICAL."""
from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CARD_LIKE = re.compile(r"\b\d{13,19}\b")


class RedactingFilter(logging.Filter):
    """Defence in depth: never let card-number-like digit runs reach a log file."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _CARD_LIKE.sub("[REDACTED]", str(record.msg))
        return True


def setup_logging(level: str, logs_dir: Path) -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s - %(message)s")
    root = logging.getLogger("fraudshield")
    if getattr(root, "_configured", False):
        root.setLevel(level)
        return
    root.setLevel(level)
    root.propagate = False
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        for name, logger_name, lvl in (("app.log", "fraudshield", level), ("error.log", "fraudshield", "ERROR"),
                                       ("inference.log", "fraudshield.inference", level)):
            handler = RotatingFileHandler(logs_dir / name, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
            handler.setFormatter(fmt)
            handler.setLevel(lvl)
            logging.getLogger(logger_name).addHandler(handler)
    except OSError as exc:  # logging to files is best effort
        root.warning("File logging disabled: %s", exc)
    root.addFilter(RedactingFilter())
    root._configured = True  # type: ignore[attr-defined]


def get_logger(name: str = "") -> logging.Logger:
    return logging.getLogger("fraudshield" + (f".{name}" if name else ""))
