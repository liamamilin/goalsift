"""Isolated data-root resolution and path guard rails.

Centralizes where the application may write (its own isolated database / cache /
temp directory) and enforces that no resolved write target escapes that root.
This directly implements the isolation requirements of AGENTS.md §7/§8 and
`07_DEVELOPMENT_PLAN.md` §3/§10: tests must use isolated directories and prove
via path assertions that production / user locations cannot be touched.

Design:
- The sanctioned root is resolved from env `GOALSIFT_DATA_DIR` if set, else a
  project-local `.goalsift_data` (gitignored). Tests force the root to an
  isolated temp directory via `override_data_root`.
- `resolve_under_root(rel)` returns an absolute path inside the root and raises
  `PathEscapeError` for any relative path that resolves outside it (including
  `..` traversal, absolute paths elsewhere, symlinks pointing out).
- The guard is a real, reusable enforcement layer used by the Repository and
  tool adapters in later milestones, not a test-only stub.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

__all__ = [
    "PathEscapeError",
    "sanctioned_data_root",
    "resolve_under_root",
    "override_data_root",
    "is_within_root",
]

_LOCK = threading.Lock()
_OVERRIDE: Path | None = None


class PathEscapeError(RuntimeError):
    """Raised when a resolved path would escape the sanctioned data root."""


def sanctioned_data_root() -> Path:
    """Return the absolute path of the application's isolated data root.

    Resolution order:
      1. A test/process override set via `override_data_root` (thread-safe).
      2. `GOALSIFT_DATA_DIR` env var.
      3. `./.goalsift_data` relative to the package parent (gitignored).
    The root is created if missing. It is always returned as a resolved absolute
    path with symlinks expanded so subsequent containment checks are reliable.
    """
    with _LOCK:
        root = _OVERRIDE
    if root is None:
        env_dir = os.environ.get("GOALSIFT_DATA_DIR")
        if env_dir:
            root = Path(env_dir).expanduser()
        else:
            root = Path(__file__).resolve().parent.parent / ".goalsift_data"
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def override_data_root(path: Path | str | None) -> None:
    """Force the sanctioned root to `path` (used by tests).

    Passing None clears the override so production resolution resumes. This is
    the only mechanism that lets tests point writes at an isolated temp dir
    without touching `GOALSIFT_DATA_DIR` semantics for the real app.
    """
    with _LOCK:
        global _OVERRIDE
        _OVERRIDE = Path(path).resolve() if path is not None else None


def is_within_root(target: Path, root: Path | None = None) -> bool:
    """True iff `target` (resolved, symlinks expanded) is inside `root`.

    `root` defaults to the current sanctioned data root. Uses `os.path.commonpath`
    on resolved paths so symlinked locations that point outside are detected.
    """
    root = (root or sanctioned_data_root()).resolve()
    try:
        resolved = target.resolve()
    except OSError:
        return False
    try:
        return os.path.commonpath([resolved, root]) == os.path.commonpath([root])
    except ValueError:
        # Different drives / platforms where commonpath is undefined.
        return False


def resolve_under_root(relative: str | os.PathLike[str]) -> Path:
    """Resolve `relative` to an absolute path guaranteed inside the data root.

    Accepts a relative path. Absolute paths are rejected unless already inside
    the root. `..` segments that escape the root, and symlinked targets that
    resolve outside, raise `PathEscapeError`.
    """
    root = sanctioned_data_root()
    raw = Path(relative)
    if raw.is_absolute():
        candidate = raw
    else:
        candidate = root / raw
    resolved = candidate.resolve()
    if not is_within_root(resolved, root):
        raise PathEscapeError(
            f"Refused path outside sanctioned data root: {relative!r} "
            f"resolves to {resolved} (root={root})"
        )
    return resolved
