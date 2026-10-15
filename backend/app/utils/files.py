"""Safe filename and path helpers (path-traversal protection for exports)."""
from __future__ import annotations

import re
from pathlib import Path

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str, max_len: int = 120) -> str:
    base = name.replace("\\", "/").split("/")[-1]
    cleaned = _SAFE.sub("_", base).strip("._") or "file"
    return cleaned[:max_len]


def ensure_within(directory: Path, target: Path) -> Path:
    directory = directory.resolve()
    resolved = target.resolve()
    if directory != resolved and directory not in resolved.parents:
        raise ValueError("Path escapes the permitted directory")
    return resolved


def unique_path(directory: Path, filename: str) -> Path:
    """Return a path inside `directory` that does not exist yet (never overwrites)."""
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    stem, dot, ext = sanitize_filename(filename).rpartition(".")
    if not dot:
        stem, ext = ext, ""
    candidate = directory / (f"{stem}.{ext}" if ext else stem)
    i = 1
    while candidate.exists():
        candidate = directory / (f"{stem}-{i}.{ext}" if ext else f"{stem}-{i}")
        i += 1
    return ensure_within(directory, candidate)
