"""M4 tests — state machine, recovery, revision & atomicity (07 §7 PASS Gate).

Deterministic tests (the live crash-restart proof is a separate run).
Gate items:
  1. legal/illegal transitions
  2. single Job single executor (concurrent start)
  3. PAUSE/CANCEL -> no new external actions
  4. crash recovery (orphan -> PAUSED)
  5. Refine -> new revision, invalidation propagation
  6. atomic commit failure leaves no half objects
"""

from __future__ import annotations

import asyncio
import sqlite3
from unittest.mock import AsyncMock, MagicMock

import pytest

from goalsift.controller import Controller
from goalsift.models import JobStatus
from goalsift.paths import override_data_root
from goalsift.repository import Repository
from goalsift.validators import ValidationError, validate_transition


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    override_data_root(root)
    r = Repository()
    yield r
    r.close()
    override_data_root(None)


# --- Gate 1: legal/illegal transitions ------------------------------------


@pytest.mark.parametrize("frm,to,ok", [
    (JobStatus.CREATED, JobStatus.RESEARCHING, True),
    (JobStatus.CREATED, JobStatus.CANCELLED, True),
    (JobStatus.RESEARCHING, JobStatus.PAUSED, True),
    (JobStatus.RESEARCHING, JobStatus.COMPLETED, True),
    (JobStatus.RESEARCHING, JobStatus.NEEDS_INPUT, True),
    (JobStatus.COMPLETED, JobStatus.RESEARCHING, True),  # Refine
    (JobStatus.CANCELLED, JobStatus.RESEARCHING, False),  # terminal
    (JobStatus.CREATED, JobStatus.PAUSED, False),  # not allowed
    (JobStatus.PAUSED, JobStatus.COMPLETED, False),  # must resume first
])
def test_gate1_transitions(frm, to, ok):
    if ok:
        validate_transition(frm, to)  # must not raise
    else:
        with pytest.raises(ValidationError):
            validate_transition(frm, to)


# --- Gate 2: single Job single executor -----------------------------------


@pytest.mark.asyncio
async def test_gate2_concurrent_start_one_executor(repo):
    job = repo.create_job("goal")
    # mock the controller's run so it doesn't actually do work
    ctrl = Controller(repo, MagicMock(), MagicMock())
    ctrl._run = AsyncMock()
    first = await ctrl.start(job.id)
    second = await ctrl.start(job.id)  # already running
    assert first is True
    assert second is False, "second concurrent start must not create a second executor"
    # only one active_run_id set
    j = repo.get_job(job.id)
    assert j.active_run_id is not None
    assert j.status == JobStatus.RESEARCHING


# --- Gate 3: PAUSE/CANCEL -> no new external actions ----------------------


@pytest.mark.asyncio
async def test_gate3_cancel_stops_external_actions(repo):
    job = repo.create_job("goal")
    ctrl = Controller(repo, MagicMock(), MagicMock())
    calls = {"search": 0, "model": 0}

    async def fake_run(jid, run_id, rev):
        # simulate reaching the Discover checkpoint after a cancel
        if ctrl._stopped(jid):
            return
        calls["search"] += 1

    ctrl._run = fake_run
    await ctrl.start(job.id)
    # cancel immediately (before the task can proceed past the checkpoint)
    repo.set_job_status(job.id, JobStatus.CANCELLED.value, active_run_id=None)
    await asyncio.sleep(0.05)
    assert calls["search"] == 0, "cancelled job must not start new external actions"


# --- Gate 4: crash recovery (orphan -> PAUSED) ---------------------------


def test_gate4_orphan_recovery(repo):
    job = repo.create_job("goal")
    # simulate a crash: job stuck RESEARCHING with active_run_id
    repo.set_job_status(job.id, JobStatus.RESEARCHING.value, active_run_id="run_dead")
    recovered = repo.recover_orphans()
    assert job.id in recovered
    j = repo.get_job(job.id)
    assert j.status == JobStatus.PAUSED
    assert j.active_run_id is None


def test_gate4_no_orphans_when_clean(repo):
    job = repo.create_job("goal")
    assert repo.recover_orphans() == []
    assert repo.get_job(job.id).status == JobStatus.CREATED


# --- Gate 5: Refine -> new revision + invalidation ------------------------


def test_gate5_refine_new_revision_and_invalidation(repo):
    job = repo.create_job("goal")
    # simulate a completed revision-1 with a proposal + assessment
    from goalsift.models import new_id, Goal, Condition, Assessment, Proposal, Obligation, Dimension, AssessmentStatus, ReviewStatus, ProposalValidity, ValidityStatus
    g = Goal(id=new_id("goal"), job_id=job.id, statement="goal", original_user_text="goal", revision=1)
    repo.save_goal(g)
    c = Condition(id=new_id("cond"), job_id=job.id, statement="c",
                  obligation=Obligation.REQUIRED, dimension=Dimension.FUNCTIONAL,
                  origin="model-derived", revision_created=1)
    repo.save_condition(c)
    a = Assessment(id=new_id("a"), job_id=job.id, condition_id=c.id,
                   status=AssessmentStatus.SUPPORTED, review_status=ReviewStatus.CURRENT,
                   revision_evaluated=1)
    repo.save_assessment(a)
    p = Proposal(id=new_id("p"), job_id=job.id, title="t", summary="s",
                 assessment_ids=[a.id], validity_status=ProposalValidity.READY_FOR_REVIEW,
                 revision_created=1)
    repo.save_proposal(p)
    repo.set_job_status(job.id, JobStatus.COMPLETED.value)

    # Refine
    new_rev = repo.new_revision(job.id)
    assert new_rev == 2
    # old revision's objects must be invalidated
    conds = repo.list_conditions(job.id)
    assert conds[0].validity_status == ValidityStatus.NEEDS_REVIEW
    asses = repo.list_assessments(job.id)
    assert asses[0].review_status == ReviewStatus.NEEDS_REVIEW
    props = repo.get_proposal(job.id)
    assert props.validity_status == ProposalValidity.NEEDS_REVIEW
    # job revision bumped
    assert repo.get_job(job.id).current_revision == 2


# --- Gate 6: atomic commit failure leaves no half objects -----------------


def test_gate6_atomic_failure_no_half_objects(repo):
    job = repo.create_job("goal")
    from goalsift.models import Condition, Dimension, Obligation, ValidityStatus, new_id
    initial = repo._conn.execute("SELECT COUNT(*) FROM conditions WHERE job_id=?", (job.id,)).fetchone()[0]
    cond = Condition(
        id=new_id("cond"), job_id=job.id, statement="x",
        obligation=Obligation.REQUIRED, dimension=Dimension.FUNCTIONAL,
        origin="t", validity_status=ValidityStatus.ACTIVE, revision_created=1,
    )
    # open a transaction, save the condition inside it, then force a failure
    try:
        with repo.transaction() as c:
            c.execute(
                "INSERT INTO conditions (id, job_id, statement, obligation, dimension, "
                "origin, source_refs, scope, verification_method, relations, "
                "validity_status, revision_created, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cond.id, job.id, cond.statement, cond.obligation.value,
                 cond.dimension.value, cond.origin, "[]", None, None, "[]",
                 cond.validity_status.value, 1,
                 cond.created_at.isoformat(), cond.updated_at.isoformat()),
            )
            raise RuntimeError("simulated mid-commit failure")
    except RuntimeError:
        pass
    after = repo._conn.execute("SELECT COUNT(*) FROM conditions WHERE job_id=?", (job.id,)).fetchone()[0]
    assert after == initial, "rollback must leave no half-committed condition"


# --- Gate 4 bonus: recovery method on an isolated repo -------------------


def test_gate4_app_startup_recovery_isolated(tmp_path):
    """Simulate app startup recovery without touching the live DB."""
    from goalsift.paths import override_data_root
    root = tmp_path / "data"
    root.mkdir()
    override_data_root(root)
    r = Repository()
    jid = r.create_job("crash-probe").id
    r.set_job_status(jid, JobStatus.RESEARCHING.value, active_run_id="dead")
    recovered = r.recover_orphans()
    assert jid in recovered
    assert r.get_job(jid).status == JobStatus.PAUSED
    assert r.get_job(jid).active_run_id is None
    r.close()
    override_data_root(None)
