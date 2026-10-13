from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
import sqlite3

from goalsift.app import create_app
from goalsift.models import Condition, Dimension, Obligation, Proposal, ProposalValidity
from goalsift.repository import Repository


class ModelStub:
    pass


class SearchStub:
    pass


@pytest.fixture
def repo(isolated_data_root):
    repository = Repository()
    actual = Path(repository._conn.execute("PRAGMA database_list").fetchone()["file"]).resolve()
    assert actual.is_relative_to(isolated_data_root.resolve())
    yield repository
    repository.close()


def completed_job(repo: Repository, title: str = "复用现有方案", validity=ProposalValidity.READY_FOR_REVIEW):
    job = repo.create_job("搭建一个研究工作区")
    condition = Condition(
        id="condition_test", job_id=job.id, statement="状态信息清晰可读",
        obligation=Obligation.REQUIRED, dimension=Dimension.QUALITY, origin="用户目标",
    )
    repo.save_condition(condition)
    proposal = Proposal(
        id=f"proposal_{job.id}", job_id=job.id, title=title,
        summary="复用现有组件并完成适配", resource_ids=[],
        validity_status=validity, revision_created=1,
    )
    repo.save_proposal(proposal)
    repo.set_job_status(job.id, "COMPLETED")
    repo.snapshot_revision(job.id)
    return job, proposal


def test_decision_select_edit_withdraw_persists_and_never_changes_snapshot(repo):
    job, proposal = completed_job(repo)
    snapshot = repo.get_revision(job.id, 1)
    event_count = len(repo.list_events(job.id))
    app = create_app(repo, ModelStub(), SearchStub())
    with TestClient(app) as client:
        initial = client.get(f"/api/jobs/{job.id}/decision").json()
        assert initial["decision"] is None
        assert initial["proposal_available"] is True

        selected = client.put(f"/api/jobs/{job.id}/decision", json={
            "expected_revision": 1, "expected_annotation_version": 0,
            "action": "SELECT", "proposal_id": proposal.id, "reason": "符合目前的质量要求",
        })
        assert selected.status_code == 200, selected.text
        assert selected.json()["decision"]["reason"] == "符合目前的质量要求"
        assert selected.json()["decision"]["proposal"]["title"] == proposal.title

        edited = client.put(f"/api/jobs/{job.id}/decision", json={
            "expected_revision": 1, "expected_annotation_version": 1,
            "action": "UPDATE_REASON", "reason": "先做小范围验收",
        })
        assert edited.status_code == 200
        assert edited.json()["decision"]["annotation_version"] == 2
        assert edited.json()["decision"]["reason"] == "先做小范围验收"

        withdrawn = client.put(f"/api/jobs/{job.id}/decision", json={
            "expected_revision": 1, "expected_annotation_version": 2,
            "action": "WITHDRAW",
        })
        assert withdrawn.status_code == 200
        assert withdrawn.json()["decision"]["active"] is False
        assert [r["action"] for r in withdrawn.json()["history"]] == ["SELECT", "UPDATE_REASON", "WITHDRAW"]

    assert repo.get_revision(job.id, 1) == snapshot
    assert len(repo.list_events(job.id)) == event_count + 3
    reopened = Repository(repo.db_path)
    try:
        decision = reopened.proposal_decisions(job.id)
        assert len(decision) == 3
        assert decision[-1]["reason"] == "先做小范围验收"
    finally:
        reopened.close()


def test_new_revision_shows_old_decision_for_reconfirmation_without_copying(repo):
    job, proposal = completed_job(repo)
    from goalsift.adoption import ProposalDecisionUpdate, save_decision, decision_view

    save_decision(repo, job.id, ProposalDecisionUpdate(
        expected_revision=1, expected_annotation_version=0,
        action="SELECT", proposal_id=proposal.id, reason="初步倾向",
    ))
    rev2 = repo.new_revision(job.id)
    assert rev2 == 2
    view = decision_view(repo, job.id)
    assert view["decision"] is None
    assert view["previous_decision"]["needs_reconfirmation"] is True
    assert view["previous_decision"]["proposal"]["title"] == proposal.title
    assert view["previous_decision"]["reason"] == "初步倾向"
    app = create_app(repo, ModelStub(), SearchStub())
    with TestClient(app) as client:
        historical = client.get(f"/api/jobs/{job.id}/decision?revision=1").json()
        assert historical["read_only"] is True
        assert historical["decision"]["proposal"]["title"] == proposal.title
        assert client.get(f"/api/jobs/{job.id}/decision?revision=98").status_code == 404


def test_stale_revision_version_state_and_invalid_proposal_are_rejected_atomically(repo):
    job, proposal = completed_job(repo)
    other, _ = completed_job(repo)
    app = create_app(repo, ModelStub(), SearchStub())
    with TestClient(app) as client:
        endpoint = f"/api/jobs/{job.id}/decision"
        foreign = client.put(endpoint, json={
            "expected_revision": 1, "expected_annotation_version": 0,
            "action": "SELECT", "proposal_id": f"proposal_{other.id}",
        })
        assert foreign.status_code == 422
        assert client.put(endpoint, json={
            "expected_revision": 1, "expected_annotation_version": 0,
            "action": "SELECT", "proposal_id": "missing",
        }).status_code == 422
        assert client.put(endpoint, json={
            "expected_revision": 1, "expected_annotation_version": 0,
            "action": "SELECT", "proposal_id": proposal.id, "extra": "forbidden",
        }).status_code == 422
        assert repo.proposal_decisions(job.id) == []

        accepted = client.put(endpoint, json={
            "expected_revision": 1, "expected_annotation_version": 0,
            "action": "SELECT", "proposal_id": proposal.id,
        })
        assert accepted.status_code == 200
        assert client.put(endpoint, json={
            "expected_revision": 1, "expected_annotation_version": 0,
            "action": "UPDATE_REASON", "reason": "旧版本提交",
        }).status_code == 409
        assert client.put(endpoint, json={
            "expected_revision": 2, "expected_annotation_version": 1,
            "action": "UPDATE_REASON", "reason": "旧修订",
        }).status_code == 409
        assert len(repo.proposal_decisions(job.id)) == 1

    repo.set_job_status(job.id, "RESEARCHING")
    # A completed decision API must not write while its controller is researching.
    with TestClient(create_app(repo, ModelStub(), SearchStub())) as client:
        result = client.put(f"/api/jobs/{job.id}/decision", json={
            "expected_revision": 1, "expected_annotation_version": 1,
            "action": "UPDATE_REASON", "reason": "运行中修改",
        })
    assert result.status_code == 409
    assert len(repo.proposal_decisions(job.id)) == 1


def test_candidate_proposal_is_not_selectable(repo):
    job, _ = completed_job(repo, validity=ProposalValidity.CANDIDATE)
    app = create_app(repo, ModelStub(), SearchStub())
    with TestClient(app) as client:
        view = client.get(f"/api/jobs/{job.id}/decision").json()
        assert view["proposal_available"] is False
        result = client.put(f"/api/jobs/{job.id}/decision", json={
            "expected_revision": 1, "expected_annotation_version": 0,
            "action": "SELECT", "proposal_id": f"proposal_{job.id}",
        })
        assert result.status_code == 422
    assert repo.proposal_decisions(job.id) == []


def test_decision_and_audit_event_roll_back_together(repo, monkeypatch):
    job, proposal = completed_job(repo)
    before_events = len(repo.list_events(job.id))

    def fail_event(_event):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(repo, "append_event", fail_event)
    from goalsift.adoption import ProposalDecisionUpdate, save_decision
    with pytest.raises(RuntimeError, match="audit write failed"):
        save_decision(repo, job.id, ProposalDecisionUpdate(
            expected_revision=1, expected_annotation_version=0,
            action="SELECT", proposal_id=proposal.id,
        ))
    assert repo.proposal_decisions(job.id) == []
    assert len(repo.list_events(job.id)) == before_events


def test_additive_decision_table_migration_keeps_existing_snapshot(repo):
    job, _ = completed_job(repo)
    snapshot = repo.get_revision(job.id, 1)
    path = repo.db_path
    repo.close()
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE proposal_decisions")
    reopened = Repository(path)
    try:
        tables = {row[0] for row in reopened._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "proposal_decisions" in tables
        assert reopened.get_revision(job.id, 1) == snapshot
    finally:
        reopened.close()
