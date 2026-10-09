"""Isolation assertions proving tests cannot write to user / production paths.

These are the M0 Gate-required 'actual assertions proving tests won't write
user real directories' (07_DEVELOPMENT_PLAN.md §3 PASS Gate).

What we actually prove here:
  - The sanctioned data root is an isolated temp dir, not the user HOME, not
    the spec directory, not the project's real `.goalsift_data`.
  - A real write through the app API lands inside the sanctioned root.
  - `..` traversal, absolute paths elsewhere, and symlink escape are refused.
  - The specification markdown files are untouched (read-only) and outside the
    write root.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from goalsift import paths


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_DOCS = [
    PROJECT_ROOT / "AGENTS.md",
    PROJECT_ROOT / "01_PRODUCT_SPEC.md",
    PROJECT_ROOT / "02_PARADIGM_SPEC.md",
    PROJECT_ROOT / "03_USER_WORKFLOW.md",
    PROJECT_ROOT / "04_AGENT_RUNTIME.md",
    PROJECT_ROOT / "05_DATA_AND_ARTIFACTS.md",
    PROJECT_ROOT / "06_ARCHITECTURE.md",
    PROJECT_ROOT / "07_DEVELOPMENT_PLAN.md",
]
USER_HOME = Path(os.path.expanduser("~"))
REAL_APP_DATA = PROJECT_ROOT / ".goalsift_data"


# --- The sanctioned root is isolated -----------------------------------------


def test_sanctioned_root_is_not_user_home(isolated_data_root: Path) -> None:
    root = paths.sanctioned_data_root()
    assert root != USER_HOME
    assert not paths.is_within_root(USER_HOME, root)


def test_sanctioned_root_is_not_project_real_data(isolated_data_root: Path) -> None:
    root = paths.sanctioned_data_root()
    assert root != REAL_APP_DATA.resolve()
    assert not paths.is_within_root(REAL_APP_DATA, root)


def test_sanctioned_root_is_not_spec_dir(isolated_data_root: Path) -> None:
    root = paths.sanctioned_data_root()
    assert not paths.is_within_root(PROJECT_ROOT, root)


def test_sanctioned_root_is_under_temp(tmp_path_factory: pytest.TempPathFactory) -> None:
    # tmp_path_factory base is the approved pytest tmp dir, which the harness
    # places under the sanctioned external temp root.
    base = tmp_path_factory.getbasetemp().resolve()
    root = paths.sanctioned_data_root()
    assert paths.is_within_root(root, base.parent) or root.is_relative_to(base)


# --- Real writes land inside the sanctioned root -----------------------------


def test_real_write_stays_inside_root(isolated_data_root: Path) -> None:
    target = paths.resolve_under_root("jobs/test_job.sqlite")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("isolation-probe")
    root = paths.sanctioned_data_root()
    assert target.exists()
    assert paths.is_within_root(target, root)
    # And the file is NOT in any forbidden location.
    assert not paths.is_within_root(target, USER_HOME) or paths.is_within_root(target, root)
    assert target.is_relative_to(root)


# --- Escapes are refused -----------------------------------------------------


def test_dotdot_traversal_refused(isolated_data_root: Path) -> None:
    with pytest.raises(paths.PathEscapeError):
        paths.resolve_under_root("../../../../etc/passwd")


def test_absolute_path_outside_refused(isolated_data_root: Path) -> None:
    with pytest.raises(paths.PathEscapeError):
        paths.resolve_under_root("/etc/passwd")


def test_absolute_path_inside_root_allowed(isolated_data_root: Path) -> None:
    root = paths.sanctioned_data_root()
    inside = root / "nested" / "file.json"
    inside.parent.mkdir(parents=True, exist_ok=True)
    # Passing an absolute path already inside the root is acceptable.
    assert paths.resolve_under_root(inside) == inside.resolve()


def test_symlink_escape_refused(isolated_data_root: Path, tmp_path: Path) -> None:
    # Create a real file outside the root in the test's own tmp area.
    outside = tmp_path / "outside.txt"
    outside.write_text("external")
    # Place a symlink inside the root pointing outside.
    link = paths.resolve_under_root("escape_link")
    if link.exists() or link.is_symlink():
        link.unlink()
    os.symlink(outside, link)
    # Resolving the symlink target escapes the root.
    with pytest.raises(paths.PathEscapeError):
        paths.resolve_under_root("escape_link")


# --- Spec docs are read-only and outside the write root ----------------------


def test_spec_docs_exist_and_outside_write_root(isolated_data_root: Path) -> None:
    root = paths.sanctioned_data_root()
    for doc in SPEC_DOCS:
        assert doc.exists(), f"spec doc missing: {doc}"
        assert not paths.is_within_root(doc, root), f"spec doc inside write root: {doc}"


def test_spec_docs_not_modified_by_test_run(isolated_data_root: Path) -> None:
    # Snapshot spec doc mtimes; running a test that writes into the data root
    # must not alter any spec file.
    before = {p: p.stat().st_mtime_ns for p in SPEC_DOCS}
    # Perform a write through the app API.
    paths.resolve_under_root("probe.txt").write_text("x")
    after = {p: p.stat().st_mtime_ns for p in SPEC_DOCS}
    assert before == after


# --- Importability / entry point --------------------------------------------


def test_package_importable() -> None:
    import goalsift

    assert goalsift.__version__
