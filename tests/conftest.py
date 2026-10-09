"""Shared pytest fixtures.

Every test gets an isolated, process-unique data root under the approved
temporary directory, so no test can touch the user's real files or the
project's real `.goalsift_data`. The override is restored on teardown.
"""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

import pytest

from goalsift import paths

# Approved external temp root (pre-created by the harness). Tests must not
# write outside an app-sanctioned root; we place all test data here.
_APPROVED_TMP = Path(os.environ.get("TMPDIR", "/tmp")) / "goalsift_test"


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Force GoalSift's data root to a unique temp dir for each test."""
    root = tmp_path_factory.mktemp("goalsift_data_") / "data"
    root.mkdir(parents=True, exist_ok=True)
    paths.override_data_root(root)
    yield root
    paths.override_data_root(None)
    # Best-effort cleanup of any created state.
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def approved_tmp_root() -> Path:
    """The approved temporary directory for this process."""
    d = _APPROVED_TMP / uuid.uuid4().hex
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)
