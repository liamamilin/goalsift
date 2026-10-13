from __future__ import annotations

from pathlib import Path
from threading import Event, Thread

import pytest
from fastapi.testclient import TestClient

from goalsift.adoption import (
    ChecklistItemUpdate, ProposalDecisionUpdate, build_checklist_items,
    checklist_view, save_decision,
)
from goalsift.app import create_app
from goalsift.exporter import to_json, to_markdown
from goalsift.models import (
    Assessment, AssessmentStatus, Condition, Dimension, Evidence, EvidenceStance,
    Obligation, Proposal, ProposalValidity, Resource, ReviewStatus, SourceType,
)
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


def prepared_selected_job(repo: Repository):
    job = repo.create_job("测试采用前检查准备")
    resource = Resource(
        id="resource_check_fixture", job_id=job.id, name="固定测试资源", kind="library",
        description="隔离验收数据", canonical_source="https://example.org/check-fixture",
        license_claim="UNKNOWN",
    )
    repo.save_resource(resource)
    evidence = Evidence(
        id="evidence_check_fixture", job_id=job.id,
        claim="文档支持状态面板能力", source_type=SourceType.OFFICIAL_DOC,
        source_ref="https://example.org/check-fixture", locator="测试段落",
        excerpt_or_summary="固定测试摘录，不代表真实外部调查", stance=EvidenceStance.SUPPORTS,
    )
    repo.save_evidence(evidence)
    required = Condition(
        id="condition_required_supported", job_id=job.id, statement="必须显示运行状态",
        obligation=Obligation.REQUIRED, dimension=Dimension.FUNCTIONAL, origin="用户要求",
        verification_method="在目标浏览器查看运行状态刷新",
    )
    optional_done = Condition(
        id="condition_optional_verified", job_id=job.id, statement="最好有深色模式",
        obligation=Obligation.OPTIONAL, dimension=Dimension.QUALITY, origin="可选偏好",
        verification_method="检查深色模式切换",
    )
    unknown = Condition(
        id="condition_optional_unknown", job_id=job.id, statement="导出应便于阅读",
        obligation=Obligation.OPTIONAL, dimension=Dimension.QUALITY, origin="质量要求",
    )
    conflicted = Condition(
        id="condition_conflicted", job_id=job.id, statement="兼容目标浏览器",
        obligation=Obligation.REQUIRED, dimension=Dimension.FUNCTIONAL, origin="用户要求",
        verification_method="在目标浏览器打开并操作关键页面",
    )
    for condition in (required, optional_done, unknown, conflicted):
        repo.save_condition(condition)

    repo.save_assessment(Assessment(
        id="assessment_supported", job_id=job.id, condition_id=required.id,
        resource_ids=[resource.id], status=AssessmentStatus.SUPPORTED,
        evidence_ids=[evidence.id], explanation="来源支持状态显示能力",
        gaps=["目标环境仍需实测"], review_status=ReviewStatus.CURRENT, revision_evaluated=1,
    ))
    repo.save_assessment(Assessment(
        id="assessment_optional_done", job_id=job.id, condition_id=optional_done.id,
        resource_ids=[resource.id], status=AssessmentStatus.VERIFIED,
        evidence_ids=[evidence.id], explanation="固定夹具中的限定检查记录",
        review_status=ReviewStatus.CURRENT, revision_evaluated=1,
    ))
    repo.save_assessment(Assessment(
        id="assessment_conflicted_a", job_id=job.id, condition_id=conflicted.id,
        resource_ids=[resource.id], status=AssessmentStatus.SUPPORTED,
        evidence_ids=[evidence.id], explanation="来源 A 支持兼容",
        review_status=ReviewStatus.CURRENT, revision_evaluated=1,
    ))
    repo.save_assessment(Assessment(
        id="assessment_conflicted_b", job_id=job.id, condition_id=conflicted.id,
        resource_ids=[resource.id], status=AssessmentStatus.CONFLICTED,
        evidence_ids=[evidence.id], explanation="来源 B 存在版本冲突",
        gaps=["核实兼容版本"], review_status=ReviewStatus.CURRENT, revision_evaluated=1,
    ))
    proposal = Proposal(
        id="proposal_check_fixture", job_id=job.id, title="隔离清单测试方案",
        summary="用于检查采用前清单行为。", resource_ids=[resource.id],
        assessment_ids=["assessment_supported", "assessment_conflicted_a", "assessment_conflicted_b"],
        condition_coverage=[required.id], uncovered_conditions=[conflicted.id, unknown.id],
        integration_work=["接入状态事件接口"], new_work=["完成目标浏览器验收"],
        risks=["许可证适用性尚未核实"], recommendation_reason="测试夹具",
        validity_status=ProposalValidity.READY_FOR_REVIEW, revision_created=1,
    )
    repo.save_proposal(proposal)
    repo.set_job_status(job.id, "COMPLETED")
    repo.snapshot_revision(job.id)
    save_decision(repo, job.id, ProposalDecisionUpdate(
        expected_revision=1, expected_annotation_version=0,
        action="SELECT", proposal_id=proposal.id, reason="隔离验收选择",
    ))
    return job, proposal, (required, optional_done, unknown, conflicted), evidence


def test_projection_includes_required_supported_gaps_and_proposal_work_but_omits_verified_optional(repo):
    job, proposal, conditions, evidence = prepared_selected_job(repo)
    result = checklist_view(repo, job.id)
    assert result["selection_required"] is False
    assert result["proposal_id"] == proposal.id
    items = result["items"]
    by_condition = {item["condition_id"]: item for item in items if item["item_type"] == "condition"}
    required, optional_done, unknown, conflicted = conditions
    assert required.id in by_condition
    assert by_condition[required.id]["assessment_status"] == "SUPPORTED"
    assert "不等于实际验收" in by_condition[required.id]["next_step"]
    assert by_condition[required.id]["verification_method"] == "在目标浏览器查看运行状态刷新"
    assert by_condition[required.id]["evidence"][0]["id"] == evidence.id
    assert by_condition[required.id]["resources"][0]["id"] == "resource_check_fixture"
    assert optional_done.id not in by_condition
    assert by_condition[unknown.id]["assessment_status"] == "UNKNOWN"
    assert "待明确标准" in by_condition[unknown.id]["next_step"]
    assert by_condition[conflicted.id]["assessment_status"] == "CONFLICTED"
    assert set(by_condition[conflicted.id]["assessment_statuses"]) == {"SUPPORTED", "CONFLICTED"}
    assert {item["item_type"] for item in items} == {"condition", "integration", "new_work", "risk"}
    again = checklist_view(repo, job.id)["items"]
    assert [(i["item_id"], i["basis_hash"]) for i in again] == [(i["item_id"], i["basis_hash"]) for i in items]
    assert build_checklist_items(repo.get_revision(job.id, 1), proposal.id)[0]["item_id"] == items[0]["item_id"]


def test_no_current_choice_or_no_proposal_returns_actionable_empty_state(repo):
    job = repo.create_job("无选择")
    repo.set_job_status(job.id, "COMPLETED")
    repo.snapshot_revision(job.id)
    result = checklist_view(repo, job.id)
    assert result["selection_required"] is True
    assert result["items"] == []
    assert "没有可供审查" in result["reason"]

    job2 = repo.create_job("有方案但尚未选择")
    proposal = Proposal(id="proposal_unselected", job_id=job2.id, title="可审查方案", summary="",
                        validity_status=ProposalValidity.READY_FOR_REVIEW, revision_created=1)
    repo.save_proposal(proposal)
    repo.set_job_status(job2.id, "COMPLETED")
    repo.snapshot_revision(job2.id)
    result2 = checklist_view(repo, job2.id)
    assert result2["selection_required"] is True
    assert result2["items"] == []
    assert "记录倾向方案" in result2["reason"]


def test_check_annotation_is_persisted_and_cannot_change_evidence_or_assessment(repo):
    job, _, _, _ = prepared_selected_job(repo)
    before_snapshot = repo.get_revision(job.id, 1)
    before_view = repo.current_view(job.id)
    before_events = len(repo.list_events(job.id))
    item = next(item for item in checklist_view(repo, job.id)["items"]
                if item["item_type"] == "condition" and item["assessment_status"] == "SUPPORTED")
    app = create_app(repo, ModelStub(), SearchStub())
    endpoint = f"/api/jobs/{job.id}/adoption-checklist/{item['item_id']}"
    body = {
        "expected_revision": 1, "expected_annotation_version": 0,
        "basis_hash": item["basis_hash"], "status": "RECORDED",
        "notes": "接口还没有接入；此记录只说明检查准备进度。",
    }
    with TestClient(app) as client:
        listed = client.get(f"/api/jobs/{job.id}/adoption-checklist")
        assert listed.status_code == 200
        assert listed.json()["selection_required"] is False
        saved = client.put(endpoint, json=body)
        assert saved.status_code == 200, saved.text
        updated = next(i for i in saved.json()["items"] if i["item_id"] == item["item_id"])
        assert updated["status"] == "RECORDED"
        assert updated["notes"] == body["notes"]
        assert updated["annotation_version"] == 1

        assert client.put(endpoint, json=body).status_code == 409
        stale_basis = {**body, "expected_annotation_version": 1, "basis_hash": "0" * 64}
        assert client.put(endpoint, json=stale_basis).status_code == 409
        stale_revision = {**body, "expected_revision": 2}
        assert client.put(endpoint, json=stale_revision).status_code == 409
        foreign_item = client.put(f"/api/jobs/{job.id}/adoption-checklist/foreign", json=body)
        assert foreign_item.status_code == 422
        invalid_status = {**body, "status": "VERIFIED"}
        assert client.put(endpoint, json=invalid_status).status_code == 422

    after_view = repo.current_view(job.id)
    assert repo.get_revision(job.id, 1) == before_snapshot
    assert len(after_view["evidence"]) == len(before_view["evidence"])
    assert [(a["id"], a["status"]) for a in after_view["assessments"]] == [(a["id"], a["status"]) for a in before_view["assessments"]]
    assert all(a["status"] != "VERIFIED" for a in after_view["assessments"] if a["id"] == "assessment_supported")
    assert len(repo.list_events(job.id)) == before_events + 1


def test_checklist_notes_stay_with_old_revision_after_refine(repo):
    job, old_proposal, _, _ = prepared_selected_job(repo)
    from goalsift.adoption import save_checklist_item

    old_item = next(item for item in checklist_view(repo, job.id)["items"] if item["item_type"] == "condition")
    save_checklist_item(repo, job.id, old_item["item_id"], ChecklistItemUpdate(
        expected_revision=1, expected_annotation_version=0, basis_hash=old_item["basis_hash"],
        status="FOLLOW_UP", notes="旧修订仍需确认。",
    ))
    assert repo.new_revision(job.id) == 2
    condition = Condition(
        id="condition_r2", job_id=job.id, statement="新修订仍要显示状态",
        obligation=Obligation.REQUIRED, dimension=Dimension.FUNCTIONAL, origin="新修订", revision_created=2,
    )
    repo.save_condition(condition)
    new_proposal = Proposal(
        id="proposal_r2", job_id=job.id, title="修订二方案", summary="",
        validity_status=ProposalValidity.READY_FOR_REVIEW, revision_created=2,
    )
    repo.save_proposal(new_proposal)
    repo.set_job_status(job.id, "COMPLETED")
    repo.snapshot_revision(job.id)
    save_decision(repo, job.id, ProposalDecisionUpdate(
        expected_revision=2, expected_annotation_version=1,
        action="SELECT", proposal_id=new_proposal.id,
    ))
    current = checklist_view(repo, job.id)
    assert all(item["status"] == "PENDING" and item["annotation_version"] == 0 for item in current["items"])
    historical = checklist_view(repo, job.id, 1)
    old_annotated = next(item for item in historical["items"] if item["item_id"] == old_item["item_id"])
    assert old_annotated["status"] == "FOLLOW_UP"
    assert old_annotated["notes"] == "旧修订仍需确认。"
    assert historical["read_only"] is True
    assert repo.get_revision(job.id, 1)["proposal"]["id"] == old_proposal.id


def test_exports_freeze_decision_checklist_and_event_cursor(repo):
    job, proposal, _, _ = prepared_selected_job(repo)
    initial = to_json(repo, job.id)
    start_cursor = initial["handoff"]["annotation_cursor"]
    assert initial["handoff"]["status"] == "SELECTED"
    assert initial["handoff"]["decision"]["proposal"]["title"] == proposal.title
    assert initial["handoff"]["decision"]["reason"] == "隔离验收选择"
    assert initial["handoff"]["checklist"]["active"] is True
    item = next(item for item in initial["handoff"]["checklist"]["items"]
                if item["item_type"] == "condition")
    assert item["status"] == "PENDING"

    from goalsift.adoption import save_checklist_item
    save_checklist_item(repo, job.id, item["item_id"], ChecklistItemUpdate(
        expected_revision=1, expected_annotation_version=0, basis_hash=item["basis_hash"],
        status="RECORDED", notes="计划在目标浏览器检查；还没有运行验收。",
    ))
    later_cursor = repo.max_event_rowid(job.id)
    old_cutoff = to_json(repo, job.id, annotation_cursor=start_cursor)
    new_cutoff = to_json(repo, job.id, annotation_cursor=later_cursor)
    old_item = next(row for row in old_cutoff["handoff"]["checklist"]["items"]
                    if row["item_id"] == item["item_id"])
    new_item = next(row for row in new_cutoff["handoff"]["checklist"]["items"]
                    if row["item_id"] == item["item_id"])
    assert old_item["status"] == "PENDING" and old_item["notes"] == ""
    assert new_item["status"] == "RECORDED"
    assert new_item["notes"] == "计划在目标浏览器检查；还没有运行验收。"
    assert new_item["annotation_version"] == 1
    markdown = to_markdown(repo, job.id, data=new_cutoff)
    assert "隔离验收选择" in markdown
    assert "计划在目标浏览器检查；还没有运行验收。" in markdown
    assert "只表示准备进度" in markdown
    assert "研究费用：未知" in markdown

    app = create_app(repo, ModelStub(), SearchStub())
    with TestClient(app) as client:
        historical_cutoff = client.get(
            f"/api/jobs/{job.id}/export?fmt=json&revision=1&annotation_cursor={start_cursor}"
        )
        assert historical_cutoff.status_code == 200
        assert historical_cutoff.json()["handoff"]["checklist"]["items"]
        markdown_cutoff = client.get(
            f"/api/jobs/{job.id}/export?fmt=markdown&revision=1&annotation_cursor={later_cursor}"
        )
        assert markdown_cutoff.status_code == 200
        assert "计划在目标浏览器检查；还没有运行验收。" in markdown_cutoff.text
        assert f"事件游标 {later_cursor}" in markdown_cutoff.text
        assert client.get(f"/api/jobs/{job.id}/export?annotation_cursor={later_cursor + 1}").status_code == 400
        assert client.get(f"/api/jobs/{job.id}/export?annotation_cursor=-1").status_code == 400


def test_export_without_selection_is_clear_pending_material(repo):
    job = repo.create_job("仅用于无选择交接导出验收")
    repo.set_job_status(job.id, "COMPLETED")
    repo.snapshot_revision(job.id)
    data = to_json(repo, job.id)
    handoff = data["handoff"]
    assert handoff["status"] == "PENDING_DECISION"
    assert handoff["decision"] is None
    assert handoff["selection_required"] is True
    assert handoff["checklist"]["active"] is False
    assert handoff["checklist"]["items"] == []
    markdown = to_markdown(repo, job.id, data=data)
    assert "待决策；当前没有已记录的倾向方案" in markdown
    assert "本报告描述研究候选，不代表用户已选择或开始实施" in markdown
    assert "研究费用：未知" in markdown


def test_new_revision_export_marks_old_choice_and_history_is_reproducible(repo):
    job, proposal, _, _ = prepared_selected_job(repo)
    from goalsift.adoption import save_checklist_item

    selected = checklist_view(repo, job.id)["items"][0]
    save_checklist_item(repo, job.id, selected["item_id"], ChecklistItemUpdate(
        expected_revision=1, expected_annotation_version=0, basis_hash=selected["basis_hash"],
        status="FOLLOW_UP", notes="保留在旧修订。",
    ))
    cursor = repo.max_event_rowid(job.id)
    snapshot = repo.get_revision(job.id, 1)
    first = to_json(repo, job.id, view=snapshot, annotation_cursor=cursor)
    second = to_json(repo, job.id, view=snapshot, annotation_cursor=cursor)
    first.pop("exported_at")
    second.pop("exported_at")
    assert first == second
    history_item = next(row for row in first["handoff"]["checklist"]["items"]
                        if row["item_id"] == selected["item_id"])
    assert history_item["notes"] == "保留在旧修订。"

    repo.new_revision(job.id)
    current = to_json(repo, job.id)
    assert current["revision"] == 2
    assert current["handoff"]["status"] == "NEEDS_RECONFIRMATION"
    assert current["handoff"]["decision"] is None
    assert current["handoff"]["previous_decision"]["proposal"]["title"] == proposal.title
    assert current["handoff"]["checklist"]["active"] is False
    assert current["handoff"]["checklist"]["items"] == []


def test_export_reconstructs_exact_unicode_source_excerpt_and_legacy_limits(repo):
    job, _, _, _ = prepared_selected_job(repo)
    resource_id = "resource_check_fixture"
    source_text = "前言🙂状态信息与运行情况"
    evidence = Evidence(
        id="evidence_unicode_excerpt", job_id=job.id, claim="保存的源文档",
        source_type=SourceType.OFFICIAL_DOC, source_ref="https://example.org/source",
        locator="README", excerpt_or_summary=source_text, source_version="commit-abc123",
        retrieved_at="2026-10-13T02:03:04+00:00", stance=EvidenceStance.CONTEXT,
    )
    repo.save_evidence(evidence)
    checkpoint = repo.get_checkpoint(job.id, 1)
    checkpoint["evidence_ids"] = [evidence.id]
    checkpoint["source_reviews"] = {resource_id: {
        "documents": [{"url": evidence.source_ref, "category": "接口文档", "version": evidence.source_version}],
        "notes": [],
        "match_context": [{
            "evidence_id": evidence.id, "url": evidence.source_ref,
            "stored_characters": len(source_text), "supplied_characters": 3,
            "is_partial": True, "excerpt_ranges": [[2, 5]],
        }],
    }}
    repo.save_checkpoint(job.id, 1, checkpoint)
    result = to_json(repo, job.id)
    context = result["source_reviews"][resource_id]["match_context"][0]
    assert context["supplied_excerpt"] == "🙂状态"
    assert context["retrieved_at"].startswith("2026-10-13T02:03:04")
    assert context["source_version"] == "commit-abc123"
    markdown = to_markdown(repo, job.id, data=result)
    assert "[2, 5)" in markdown
    assert "🙂状态" in markdown
    assert "不能据此判断整份资料不存在" in markdown

    checkpoint["source_reviews"][resource_id].pop("match_context")
    repo.save_checkpoint(job.id, 1, checkpoint)
    legacy = to_json(repo, job.id)
    assert "match_context" not in legacy["source_reviews"][resource_id]
    assert "旧记录未保存模型实际收到的摘录范围" in to_markdown(repo, job.id)


def test_export_keeps_research_and_annotations_consistent_during_concurrent_edit(repo, monkeypatch):
    job, _, _, _ = prepared_selected_job(repo)
    from goalsift.adoption import save_checklist_item

    item = next(item for item in checklist_view(repo, job.id)["items"]
                if item["item_type"] == "condition")
    captured_cursor = repo.max_event_rowid(job.id)
    annotation_reading = Event()
    allow_export_to_finish = Event()
    writer_started = Event()
    writer_done = Event()
    result = []
    original = repo.annotation_records_at_event_cursor

    def pause_during_annotation_read(job_id, cursor):
        annotation_reading.set()
        assert allow_export_to_finish.wait(3)
        return original(job_id, cursor)

    monkeypatch.setattr(repo, "annotation_records_at_event_cursor", pause_during_annotation_read)
    exporter = Thread(target=lambda: result.append(to_json(repo, job.id)))
    exporter.start()
    assert annotation_reading.wait(3)

    def write_note():
        writer_started.set()
        save_checklist_item(repo, job.id, item["item_id"], ChecklistItemUpdate(
            expected_revision=1, expected_annotation_version=0, basis_hash=item["basis_hash"],
            status="RECORDED", notes="并发写入完成。",
        ))
        writer_done.set()

    writer = Thread(target=write_note)
    writer.start()
    assert writer_started.wait(3)
    assert writer_done.wait(0.1) is False
    allow_export_to_finish.set()
    exporter.join(3)
    writer.join(3)
    assert not exporter.is_alive() and not writer.is_alive()
    exported = result[0]
    exported_item = next(row for row in exported["handoff"]["checklist"]["items"]
                         if row["item_id"] == item["item_id"])
    assert exported["handoff"]["annotation_cursor"] == captured_cursor
    assert exported_item["status"] == "PENDING"
    current = to_json(repo, job.id)
    current_item = next(row for row in current["handoff"]["checklist"]["items"]
                        if row["item_id"] == item["item_id"])
    assert current_item["status"] == "RECORDED"
    assert current_item["notes"] == "并发写入完成。"
