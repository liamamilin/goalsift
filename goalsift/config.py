"""Minimal environment loader (no third-party dependency).

Reads `.env` from the project root into `os.environ` if present, without
overwriting already-set variables. Used by spikes and (later) the app runtime
so secrets never appear in code or logs.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["load_env", "project_root"]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def project_root() -> Path:
    return _PROJECT_ROOT


def load_env(path: Path | str | None = None) -> dict[str, str]:
    """Load `.env` into os.environ (does not override existing values).

    Returns the set of keys that were loaded, for presence-only diagnostics.
    Values are never returned by this function to avoid leaking secrets.
    """
    env_path = Path(path) if path else (_PROJECT_ROOT / ".env")
    if not env_path.exists():
        return {}
    loaded: list[str] = []
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val
            loaded.append(key)
    return {k: "***" for k in loaded}  # presence only, no values
