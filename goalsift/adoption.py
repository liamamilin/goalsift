"""User-owned decisions made after research; these never mutate research state."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import ActionType, JobStatus, ProposalValidity, ResearchEvent, new_id
from .repository import Repository


class DecisionConflict(RuntimeError):
    """The job or annotation changed since the client loaded it."""


class ProposalDecisionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    expected_annotation_version: int = Field(ge=0)
    action: Literal["SELECT", "UPDATE_REASON", "WITHDRAW"]
    proposal_id: str | None = Field(default=None, min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=6000)


class ChecklistItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    expected_annotation_version: int = Field(ge=0)
    basis_hash: str = Field(min_length=64, max_length=64)
    status: Literal["PENDING", "RECORDED", "FOLLOW_UP"]
    notes: str | None = Field(default=None, max_length=4000)


def _snapshot(repo: Repository, job_id: str, revision: int, current_revision: int) -> dict[str, Any] | None:
    stored = repo.get_revision(job_id, revision)
    if stored is not None:
        return stored
    job = repo.get_job(job_id)
    if job and job.status == JobStatus.COMPLETED and revision == current_revision:
        # Compatibility for a completed legacy task whose snapshot predates persistence.
        return repo.current_view(job_id)
    return None


def _enrich(repo: Repository, record: dict[str, Any] | None, requested_revision: int) -> dict[str, Any] | None:
    if record is None:
        return None
    rev = int(record["source_revision"])
    snapshot = repo.get_revision(record["job_id"], rev)
    if snapshot is None:
        job = repo.get_job(record["job_id"])
        if job and job.status == JobStatus.COMPLETED and job.current_revision == rev:
            snapshot = repo.current_view(job.id)
    proposal = snapshot.get("proposal") if snapshot else None
    if not proposal or proposal.get("id") != record["proposal_id"]:
        proposal = None
    resources = {r["id"]: r for r in (snapshot or {}).get("resources", [])}
    return {
        **record,
        "active": record["action"] != "WITHDRAW",
        "needs_reconfirmation": rev != requested_revision,
        "proposal": ({
            "id": proposal["id"],
            "title": proposal["title"],
            "summary": proposal.get("summary", ""),
            "resource_ids": proposal.get("resource_ids", []),
            "resources": [resources[rid] for rid in proposal.get("resource_ids", []) if rid in resources],
        } if proposal else None),
    }


def decision_view(repo: Repository, job_id: str, revision: int | None = None) -> dict[str, Any]:
    """Read decisions against the requested revision without resolving old IDs in current data."""
    with repo.transaction():
        job = repo.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        selected_revision = revision if revision is not None else job.current_revision
        snapshot = _snapshot(repo, job_id, selected_revision, job.current_revision)
        if revision is not None and selected_revision != job.current_revision and snapshot is None:
            raise KeyError(selected_revision)
        records = repo.proposal_decisions(job_id)
        for_revision = [r for r in records if r["source_revision"] == selected_revision]
        previous = next((r for r in reversed(records) if r["source_revision"] < selected_revision), None)
        latest_version = repo.latest_proposal_decision_version(job_id)
        return {
            "job_id": job_id,
            "revision": selected_revision,
            "current_revision": job.current_revision,
            "read_only": selected_revision != job.current_revision,
            "annotation_version": latest_version,
            "proposal_available": bool(snapshot and snapshot.get("proposal") and
                snapshot["proposal"].get("validity_status") == ProposalValidity.READY_FOR_REVIEW.value),
            "decision": _enrich(repo, for_revision[-1] if for_revision else None, selected_revision),
            "previous_decision": _enrich(repo, previous, selected_revision),
            "history": [_enrich(repo, record, selected_revision) for record in records],
        }


def save_decision(repo: Repository, job_id: str, update: ProposalDecisionUpdate) -> dict[str, Any]:
    with repo.transaction():
        job = repo.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        if job.status != JobStatus.COMPLETED or job.active_run_id:
            raise DecisionConflict("只可在已完成且空闲的修订中记录方案决定")
        if job.current_revision != update.expected_revision:
            raise DecisionConflict("研究修订已变化，请刷新后重新确认")
        current_version = repo.latest_proposal_decision_version(job_id)
        if current_version != update.expected_annotation_version:
            raise DecisionConflict("方案决定已被更新，请刷新后重试")

        revision_records = [r for r in repo.proposal_decisions(job_id)
                            if r["source_revision"] == job.current_revision]
        active = revision_records[-1] if revision_records and revision_records[-1]["action"] != "WITHDRAW" else None
        snapshot = _snapshot(repo, job_id, job.current_revision, job.current_revision)
        proposal = snapshot.get("proposal") if snapshot else None

        if update.action == "SELECT":
            if not update.proposal_id:
                raise ValueError("选择方案时必须提供方案 ID")
            if not proposal or proposal.get("id") != update.proposal_id:
                raise ValueError("方案不属于该修订或当前没有有效方案")
            if proposal.get("validity_status") != ProposalValidity.READY_FOR_REVIEW.value:
                raise ValueError("只能选择当前可供审查的方案")
            proposal_id = update.proposal_id
            reason = (update.reason or "").strip()
        elif update.action == "UPDATE_REASON":
            if not active:
                raise ValueError("当前修订没有可编辑的方案决定")
            if update.proposal_id and update.proposal_id != active["proposal_id"]:
                raise ValueError("改理由不能更换所选方案")
            proposal_id = active["proposal_id"]
            reason = (update.reason or "").strip()
        else:
            if not active:
                raise ValueError("当前修订没有可撤回的方案决定")
            if update.proposal_id and update.proposal_id != active["proposal_id"]:
                raise ValueError("撤回的方案与当前决定不一致")
            proposal_id = active["proposal_id"]
            reason = active["reason"]

        now = datetime.now(timezone.utc).isoformat()
        record = {
            "decision_id": new_id("decision"),
            "job_id": job_id,
            "source_revision": job.current_revision,
            "proposal_id": proposal_id,
            "action": update.action,
            "reason": reason,
            "annotation_version": current_version + 1,
            "created_at": now,
        }
        repo.append_proposal_decision(record)
        event_status = {
            "SELECT": "PROPOSAL_SELECTED",
            "UPDATE_REASON": "PROPOSAL_REASON_UPDATED",
            "WITHDRAW": "PROPOSAL_SELECTION_WITHDRAWN",
        }[update.action]
        repo.append_event(ResearchEvent(
            id=new_id("ev"), event_id=new_id("ev"), job_id=job_id,
            revision=job.current_revision, action_type=ActionType.REVISE,
            status=event_status, related_object_ids=[proposal_id, record["decision_id"]],
        ))
    return decision_view(repo, job_id, job.current_revision)


_ASSESSMENT_ORDER = {
    "CONFLICTED": 0, "NOT_SATISFIED": 1, "UNKNOWN": 2,
    "PARTIAL": 3, "SUPPORTED": 4, "VERIFIED": 5,
}


def _json_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _item_id(job_id: str, revision: int, item_type: str, source_id: str, index: int = 0) -> str:
    raw = f"{job_id}:{revision}:{item_type}:{source_id}:{index}"
    return "check_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _condition_next_step(status: str, method: str | None) -> str:
    if not method:
        return "待明确标准：通过目标与条件复核补充验收方式。"
    return {
        "VERIFIED": "确认已有测试环境与当前采用情景一致，并检查实际记录。",
        "SUPPORTED": f"在目标环境按验收方式实测：{method}。来源支持不等于实际验收。",
        "PARTIAL": f"补齐已知缺口后按验收方式复核：{method}。",
        "NOT_SATISFIED": "处理未满足事项，或重新评估这条方案是否可接受。",
        "UNKNOWN": f"按验收方式收集实际结果：{method}。",
        "CONFLICTED": "核对相互矛盾的来源，解决冲突后再判断。",
    }[status]


def build_checklist_items(view: dict[str, Any], selected_proposal_id: str) -> list[dict[str, Any]]:
    """Project traceable adoption checks from one frozen research revision."""
    proposal = view.get("proposal")
    if not proposal or proposal.get("id") != selected_proposal_id:
        return []
    resources = {r["id"]: r for r in view.get("resources", [])}
    evidence = {e["id"]: e for e in view.get("evidence", [])}
    assessments_by_condition: dict[str, list[dict[str, Any]]] = {}
    for assessment in view.get("assessments", []):
        assessments_by_condition.setdefault(assessment["condition_id"], []).append(assessment)

    items: list[dict[str, Any]] = []
    for condition in view.get("conditions", []):
        assessments = assessments_by_condition.get(condition["id"], [])
        statuses = sorted({a["status"] for a in assessments},
                          key=lambda status: _ASSESSMENT_ORDER.get(status, 9))
        status = statuses[0] if statuses else "UNKNOWN"
        if condition.get("obligation") != "REQUIRED" and status == "VERIFIED":
            continue
        assessment_ids = sorted(a["id"] for a in assessments)
        resource_ids = sorted({rid for a in assessments for rid in a.get("resource_ids", [])})
        resource_ids = list(dict.fromkeys(resource_ids + [rid for rid in proposal.get("resource_ids", []) if rid in resources]))
        evidence_ids = sorted({eid for a in assessments for eid in a.get("evidence_ids", [])})
        method = (condition.get("verification_method") or "").strip() or None
        basis = {
            "item_type": "condition", "condition": condition, "status": status,
            "assessments": assessments,
            "resources": [resources[rid] for rid in resource_ids if rid in resources],
            "evidence": [evidence[eid] for eid in evidence_ids if eid in evidence],
            "proposal_id": proposal["id"],
        }
        items.append({
            "item_id": _item_id(view["id"], view["revision"], "condition", condition["id"]),
            "item_type": "condition", "title": condition["statement"],
            "source_revision": view["revision"], "condition_id": condition["id"],
            "proposal_id": proposal["id"], "obligation": condition.get("obligation"),
            "dimension": condition.get("dimension"), "assessment_status": status,
            "assessment_statuses": statuses, "assessments": assessments,
            "resources": [resources[rid] for rid in resource_ids if rid in resources],
            "evidence": [evidence[eid] for eid in evidence_ids if eid in evidence],
            "verification_method": method,
            "gaps": list(dict.fromkeys(gap for a in assessments for gap in a.get("gaps", []))),
            "next_step": _condition_next_step(status, method),
            "basis_hash": _json_hash(basis),
        })

    for field, label, item_type in (
        ("integration_work", "集成工作", "integration"),
        ("new_work", "补充工作", "new_work"),
        ("risks", "风险与限制", "risk"),
    ):
        for index, text in enumerate(proposal.get(field, [])):
            basis = {"item_type": item_type, "proposal_id": proposal["id"], "text": text}
            items.append({
                "item_id": _item_id(view["id"], view["revision"], item_type, proposal["id"], index),
                "item_type": item_type, "title": text, "group_label": label,
                "source_revision": view["revision"], "condition_id": None,
                "proposal_id": proposal["id"], "obligation": None, "dimension": None,
                "assessment_status": None, "assessment_statuses": [], "assessments": [],
                "resources": [resources[rid] for rid in proposal.get("resource_ids", []) if rid in resources],
                "evidence": [], "verification_method": None, "gaps": [],
                "next_step": "由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。",
                "basis_hash": _json_hash(basis),
            })
    return items


def _active_decision(repo: Repository, job_id: str, revision: int) -> dict[str, Any] | None:
    records = [r for r in repo.proposal_decisions(job_id) if r["source_revision"] == revision]
    if not records or records[-1]["action"] == "WITHDRAW":
        return None
    return records[-1]


def checklist_view(repo: Repository, job_id: str, revision: int | None = None) -> dict[str, Any]:
    with repo.transaction():
        job = repo.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        selected_revision = revision if revision is not None else job.current_revision
        snapshot = _snapshot(repo, job_id, selected_revision, job.current_revision)
        if revision is not None and selected_revision != job.current_revision and snapshot is None:
            raise KeyError(selected_revision)
        decision = _active_decision(repo, job_id, selected_revision)
        proposal = snapshot.get("proposal") if snapshot else None
        selected = bool(decision and proposal and decision["proposal_id"] == proposal.get("id")
                        and proposal.get("validity_status") == ProposalValidity.READY_FOR_REVIEW.value)
        items = build_checklist_items(snapshot, decision["proposal_id"]) if selected and snapshot else []
        items = _attach_annotations(repo, job_id, selected_revision, items)
        if selected:
            reason = None
        elif job.status != JobStatus.COMPLETED and selected_revision == job.current_revision:
            reason = "请等待本修订研究完成，再检查并明确选择当前方案。"
        elif not proposal or proposal.get("validity_status") != ProposalValidity.READY_FOR_REVIEW.value:
            reason = "当前修订没有可供审查的有效方案，请先继续研究。"
        else:
            reason = "请先在方案页记录倾向方案，再生成对应检查清单。"
        return {
            "job_id": job_id, "revision": selected_revision,
            "current_revision": job.current_revision,
            "read_only": selected_revision != job.current_revision,
            "selection_required": not selected,
            "reason": reason,
            "proposal_id": proposal.get("id") if selected and proposal else None,
            "proposal_title": proposal.get("title") if selected and proposal else None,
            "items": items,
        }


def handoff_annotations(repo: Repository, job_id: str, view: dict[str, Any], cursor: int) -> dict[str, Any]:
    """Freeze decision and checklist annotations alongside one research revision."""
    revision = int(view["revision"])
    all_decisions, all_checks = repo.annotation_records_at_event_cursor(job_id, cursor)
    decisions = [r for r in all_decisions if r["source_revision"] <= revision]
    checks = [r for r in all_checks if r["source_revision"] == revision]
    exact = [r for r in decisions if r["source_revision"] == revision]
    previous = next((r for r in reversed(decisions) if r["source_revision"] < revision), None)
    latest = exact[-1] if exact else None
    proposal = view.get("proposal")
    active = bool(latest and latest["action"] != "WITHDRAW" and proposal
                  and latest["proposal_id"] == proposal.get("id")
                  and proposal.get("validity_status") == ProposalValidity.READY_FOR_REVIEW.value)
    previous_active = bool(previous and previous["action"] != "WITHDRAW")
    if active:
        state = "SELECTED"
    elif previous_active:
        state = "NEEDS_RECONFIRMATION"
    else:
        state = "PENDING_DECISION"

    selected_record = _enrich(repo, latest, revision) if latest else None
    if selected_record is not None:
        selected_record["active"] = active
    previous_record = _enrich(repo, previous, revision) if previous else None
    decision_history = [_enrich(repo, r, revision) for r in exact]
    candidate_id = (latest or previous or {}).get("proposal_id")
    checklist_basis: dict[str, dict[str, Any]] = {}
    if proposal and candidate_id == proposal.get("id"):
        checklist_basis = {item["item_id"]: item for item in build_checklist_items(view, candidate_id)}

    latest_checks: dict[str, dict[str, Any]] = {}
    for row in checks:
        current = latest_checks.get(row["item_id"])
        if current is None or row["annotation_version"] > current["annotation_version"]:
            latest_checks[row["item_id"]] = row

    def project_check(row: dict[str, Any], item: dict[str, Any] | None) -> dict[str, Any]:
        return {
            **row,
            "title": item.get("title") if item else None,
            "check_type": item.get("item_type") if item else None,
            "basis_matches": bool(item and row["basis_hash"] == item["basis_hash"]),
        }

    checklist_items: list[dict[str, Any]] = []
    if active and proposal:
        for item_id, item in checklist_basis.items():
            row = latest_checks.get(item_id)
            matches = bool(row and row["basis_hash"] == item["basis_hash"])
            checklist_items.append({
                **item,
                "status": row["status"] if matches else "PENDING",
                "notes": row["notes"] if matches else "",
                "annotation_version": int(row["annotation_version"]) if row else 0,
                "needs_review": bool(row and not matches),
                "previous_annotation": project_check(row, item) if row and not matches else None,
            })

    annotation_times = [r["created_at"] for r in decisions + checks if r.get("created_at")]
    return {
        "research_revision": revision,
        "annotation_cursor": cursor,
        "annotation_cutoff_at": max(annotation_times) if annotation_times else None,
        "status": state,
        "selection_required": not active,
        "decision_annotation_version": int(latest["annotation_version"]) if latest else 0,
        "decision": selected_record,
        "previous_decision": previous_record,
        "decision_history": decision_history,
        "checklist": {
            "active": active,
            "proposal_id": proposal.get("id") if active and proposal else None,
            "selection_required": not active,
            "items": checklist_items,
            "history": [project_check(r, checklist_basis.get(r["item_id"])) for r in checks],
        },
    }


def _attach_annotations(repo: Repository, job_id: str, revision: int, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in items:
        annotation = repo.latest_checklist_annotation(job_id, revision, item["item_id"])
        same_basis = bool(annotation and annotation["basis_hash"] == item["basis_hash"])
        output.append({
            **item,
            "status": annotation["status"] if same_basis else "PENDING",
            "notes": annotation["notes"] if same_basis else "",
            "annotation_version": int(annotation["annotation_version"]) if annotation else 0,
            "needs_review": bool(annotation and not same_basis),
            "previous_annotation": ({
                "status": annotation["status"], "notes": annotation["notes"],
                "basis_hash": annotation["basis_hash"],
                "annotation_version": annotation["annotation_version"],
            } if annotation and not same_basis else None),
        })
    return output


def save_checklist_item(repo: Repository, job_id: str, item_id: str, update: ChecklistItemUpdate) -> dict[str, Any]:
    with repo.transaction():
        job = repo.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        if job.status != JobStatus.COMPLETED or job.active_run_id:
            raise DecisionConflict("只可在已完成且空闲的修订中记录检查进度")
        if job.current_revision != update.expected_revision:
            raise DecisionConflict("研究修订已变化，请刷新检查清单")
        snapshot = _snapshot(repo, job_id, job.current_revision, job.current_revision)
        decision = _active_decision(repo, job_id, job.current_revision)
        proposal = snapshot.get("proposal") if snapshot else None
        if not snapshot or not decision or not proposal or decision["proposal_id"] != proposal.get("id"):
            raise DecisionConflict("当前修订没有有效的已选择方案")
        item = next((candidate for candidate in build_checklist_items(snapshot, proposal["id"])
                     if candidate["item_id"] == item_id), None)
        if not item:
            raise ValueError("检查项不属于当前修订")
        if item["basis_hash"] != update.basis_hash:
            raise DecisionConflict("检查依据已变化，请刷新后重新记录")
        latest = repo.latest_checklist_annotation(job_id, job.current_revision, item_id)
        latest_version = int(latest["annotation_version"]) if latest else 0
        if latest_version != update.expected_annotation_version:
            raise DecisionConflict("检查进度已被更新，请刷新后重试")
        now = datetime.now(timezone.utc).isoformat()
        annotation = {
            "annotation_id": new_id("checknote"), "job_id": job_id,
            "source_revision": job.current_revision, "item_id": item_id,
            "basis_hash": item["basis_hash"], "status": update.status,
            "notes": (update.notes or "").strip(), "annotation_version": latest_version + 1,
            "created_at": now,
        }
        repo.append_checklist_annotation(annotation)
        repo.append_event(ResearchEvent(
            id=new_id("ev"), event_id=new_id("ev"), job_id=job_id,
            revision=job.current_revision, action_type=ActionType.REVISE,
            status=f"ADOPTION_CHECK_{update.status}", related_object_ids=[item_id, annotation["annotation_id"]],
        ))
    return checklist_view(repo, job_id, job.current_revision)
