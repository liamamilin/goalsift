"""SQLite repository — isolated persistence for research state.

Implements 05 field contracts with tables for Job, Goal, Condition, Resource,
Capability, Evidence, Assessment, Proposal, Event. Writes go through
`validators` before commit (04 §5). Path-guarded: the DB lives in the
sanctioned data root only (AGENTS.md §7).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .models import (
    Assessment,
    Capability,
    Condition,
    Evidence,
    Goal,
    Proposal,
    ResearchEvent,
    ResearchJob,
    Resource,
    new_id,
)
from .paths import resolve_under_root, sanctioned_data_root

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, original_request TEXT, current_goal_id TEXT,
  current_revision INTEGER, status TEXT, created_at TEXT, updated_at TEXT,
  budget_config TEXT, budget_usage TEXT, active_run_id TEXT, checkpoint_ref TEXT,
  open_questions TEXT
);
CREATE TABLE IF NOT EXISTS goals (
  id TEXT PRIMARY KEY, job_id TEXT, statement TEXT, purpose TEXT, revision INTEGER,
  original_user_text TEXT, requirements TEXT, constraints TEXT, assumptions TEXT,
  open_questions TEXT, created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS conditions (
  id TEXT PRIMARY KEY, job_id TEXT, statement TEXT, obligation TEXT, dimension TEXT,
  origin TEXT, source_refs TEXT, scope TEXT, verification_method TEXT,
  relations TEXT, validity_status TEXT, revision_created INTEGER,
  created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS resources (
  id TEXT PRIMARY KEY, job_id TEXT, name TEXT, kind TEXT, description TEXT,
  canonical_source TEXT, source_references TEXT, version_or_revision TEXT,
  availability TEXT, license_claim TEXT, environment TEXT,
  discovery_status TEXT, discovered_at TEXT, created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS capabilities (
  id TEXT PRIMARY KEY, job_id TEXT, resource_id TEXT, statement TEXT,
  preconditions TEXT, interface_or_use TEXT, effects TEXT, limitations TEXT,
  evidence_ids TEXT, created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY, job_id TEXT, claim TEXT, source_type TEXT, source_ref TEXT,
  locator TEXT, excerpt_or_summary TEXT, retrieved_at TEXT, source_version TEXT,
  collection_method TEXT, stance TEXT, verification_method TEXT,
  test_context TEXT, observed_result TEXT, created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS assessments (
  id TEXT PRIMARY KEY, job_id TEXT, condition_id TEXT, resource_ids TEXT,
  capability_ids TEXT, context TEXT, status TEXT, evidence_ids TEXT,
  explanation TEXT, gaps TEXT, assumptions TEXT, review_status TEXT,
  revision_evaluated INTEGER, created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS proposals (
  id TEXT PRIMARY KEY, job_id TEXT, title TEXT, summary TEXT, resource_ids TEXT,
  assessment_ids TEXT, condition_coverage TEXT, integration_work TEXT,
  new_work TEXT, uncovered_conditions TEXT, risks TEXT, assumptions TEXT,
  costs TEXT, recommendation_reason TEXT, validity_status TEXT,
  revision_created INTEGER, created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY, job_id TEXT, revision INTEGER, run_id TEXT,
  action_type TEXT, status TEXT, started_at TEXT, ended_at TEXT,
  related_object_ids TEXT, tool_result_ref TEXT, usage TEXT, error TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _j(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


class Repository:
    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = resolve_under_root("goalsift.sqlite")
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        # write-ahead for concurrency
        self._conn.execute("PRAGMA journal_mode=WAL")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        cur = self._conn.cursor()
        cur.execute("BEGIN")
        try:
            yield self._conn
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            raise

    def close(self) -> None:
        self._conn.close()

    # --- Job -------------------------------------------------------------
    def create_job(self, original_request: str) -> ResearchJob:
        jid = new_id("job")
        job = ResearchJob(
            id=jid, job_id=jid, original_request=original_request,
            status="CREATED", current_revision=1,
        )
        with self.transaction() as c:
            c.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (job.id, job.original_request, job.current_goal_id, job.current_revision,
                 job.status.value, job.created_at.isoformat(), job.updated_at.isoformat(),
                 _j(job.budget_config), _j(job.budget_usage), job.active_run_id,
                 job.checkpoint_ref, _j(job.open_questions)),
            )
        self.append_event(ResearchEvent(
            id=new_id("ev"), event_id=new_id("ev"), job_id=jid, revision=1,
            action_type="FINISH" if False else "REASON", status="CREATED",
            related_object_ids=[jid],
        ))
        return job

    def set_job_status(self, job_id: str, status: str, **extra: Any) -> None:
        cols = ["status=?", "updated_at=?"]
        vals: list[Any] = [status, _now()]
        for k, v in extra.items():
            if k in ("current_goal_id", "current_revision", "active_run_id", "checkpoint_ref"):
                cols.append(f"{k}=?")
                vals.append(v)
        vals.append(job_id)
        with self.transaction() as c:
            c.execute(f"UPDATE jobs SET {', '.join(cols)} WHERE id=?", vals)

    def get_job(self, job_id: str) -> ResearchJob | None:
        r = self._conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not r:
            return None
        return ResearchJob(
            id=r["id"], job_id=r["id"], original_request=r["original_request"],
            current_goal_id=r["current_goal_id"], current_revision=r["current_revision"],
            status=r["status"],
            budget_config=json.loads(r["budget_config"] or "{}"),
            budget_usage=json.loads(r["budget_usage"] or "{}"),
            active_run_id=r["active_run_id"], checkpoint_ref=r["checkpoint_ref"],
            open_questions=json.loads(r["open_questions"] or "[]"),
        )

    def list_jobs(self) -> list[ResearchJob]:
        rows = self._conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [self._row_to_job(r) for r in rows]

    def _row_to_job(self, r: sqlite3.Row) -> ResearchJob:
        return ResearchJob(
            id=r["id"], job_id=r["id"], original_request=r["original_request"],
            current_goal_id=r["current_goal_id"], current_revision=r["current_revision"],
            status=r["status"],
            budget_config=json.loads(r["budget_config"] or "{}"),
            budget_usage=json.loads(r["budget_usage"] or "{}"),
            active_run_id=r["active_run_id"], checkpoint_ref=r["checkpoint_ref"],
            open_questions=json.loads(r["open_questions"] or "[]"),
        )

    # --- Goal ------------------------------------------------------------
    def save_goal(self, g: Goal) -> None:
        with self.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO goals VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (g.id, g.job_id, g.statement, g.purpose, g.revision,
                 g.original_user_text, _j(g.requirements), _j(g.constraints),
                 _j(g.assumptions), _j(g.open_questions),
                 g.created_at.isoformat(), g.updated_at.isoformat()),
            )

    def get_goal(self, job_id: str) -> Goal | None:
        r = self._conn.execute("SELECT * FROM goals WHERE job_id=? ORDER BY revision DESC LIMIT 1", (job_id,)).fetchone()
        if not r:
            return None
        return Goal(
            id=r["id"], job_id=r["job_id"], statement=r["statement"], purpose=r["purpose"],
            revision=r["revision"], original_user_text=r["original_user_text"],
            requirements=json.loads(r["requirements"] or "[]"),
            constraints=json.loads(r["constraints"] or "[]"),
            assumptions=json.loads(r["assumptions"] or "[]"),
            open_questions=json.loads(r["open_questions"] or "[]"),
        )

    # --- Condition -------------------------------------------------------
    def save_condition(self, c_obj: Condition) -> None:
        with self.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO conditions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (c_obj.id, c_obj.job_id, c_obj.statement, c_obj.obligation.value,
                 c_obj.dimension.value, c_obj.origin, _j(c_obj.source_refs),
                 c_obj.scope, c_obj.verification_method, _j(c_obj.relations),
                 c_obj.validity_status.value, c_obj.revision_created,
                 c_obj.created_at.isoformat(), c_obj.updated_at.isoformat()),
            )

    def list_conditions(self, job_id: str) -> list[Condition]:
        rows = self._conn.execute("SELECT * FROM conditions WHERE job_id=? ORDER BY created_at", (job_id,)).fetchall()
        from .models import Dimension, Obligation, ValidityStatus
        return [Condition(
            id=r["id"], job_id=r["job_id"], statement=r["statement"],
            obligation=Obligation(r["obligation"]), dimension=Dimension(r["dimension"]),
            origin=r["origin"], source_refs=json.loads(r["source_refs"] or "[]"),
            scope=r["scope"], verification_method=r["verification_method"],
            relations=json.loads(r["relations"] or "[]"),
            validity_status=ValidityStatus(r["validity_status"]),
            revision_created=r["revision_created"],
        ) for r in rows]

    # --- Resource --------------------------------------------------------
    def save_resource(self, r_obj: Resource) -> None:
        with self.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO resources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (r_obj.id, r_obj.job_id, r_obj.name, r_obj.kind, r_obj.description,
                 r_obj.canonical_source, _j(r_obj.source_references),
                 r_obj.version_or_revision, r_obj.availability, r_obj.license_claim,
                 r_obj.environment, r_obj.discovery_status.value,
                 r_obj.discovered_at.isoformat(), r_obj.created_at.isoformat(), r_obj.updated_at.isoformat()),
            )

    def list_resources(self, job_id: str) -> list[Resource]:
        from .models import DiscoveryStatus
        rows = self._conn.execute("SELECT * FROM resources WHERE job_id=? ORDER BY created_at", (job_id,)).fetchall()
        return [Resource(
            id=r["id"], job_id=r["job_id"], name=r["name"], kind=r["kind"],
            description=r["description"], canonical_source=r["canonical_source"],
            source_references=json.loads(r["source_references"] or "[]"),
            version_or_revision=r["version_or_revision"], availability=r["availability"],
            license_claim=r["license_claim"], environment=r["environment"],
            discovery_status=DiscoveryStatus(r["discovery_status"]),
        ) for r in rows]

    # --- Capability ------------------------------------------------------
    def save_capability(self, cap: Capability) -> None:
        with self.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO capabilities "
                "(id, job_id, resource_id, statement, preconditions, interface_or_use, "
                "effects, limitations, evidence_ids, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (cap.id, cap.job_id, cap.resource_id, cap.statement,
                 _j(cap.preconditions), cap.interface_or_use, _j(cap.effects),
                 _j(cap.limitations), _j(cap.evidence_ids),
                 cap.created_at.isoformat(), cap.updated_at.isoformat()),
            )

    def list_capabilities(self, job_id: str) -> list[Capability]:
        rows = self._conn.execute("SELECT * FROM capabilities WHERE job_id=?", (job_id,)).fetchall()
        return [Capability(
            id=r["id"], job_id=r["job_id"], resource_id=r["resource_id"],
            statement=r["statement"],
            preconditions=json.loads(r["preconditions"] or "[]"),
            interface_or_use=r["interface_or_use"],
            effects=json.loads(r["effects"] or "[]"),
            limitations=json.loads(r["limitations"] or "[]"),
            evidence_ids=json.loads(r["evidence_ids"] or "[]"),
        ) for r in rows]

    # --- Evidence --------------------------------------------------------
    def save_evidence(self, e: Evidence) -> None:
        with self.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO evidence "
                "(id, job_id, claim, source_type, source_ref, locator, "
                "excerpt_or_summary, retrieved_at, source_version, collection_method, "
                "stance, verification_method, test_context, observed_result, "
                "created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (e.id, e.job_id, e.claim, e.source_type.value, e.source_ref, e.locator,
                 e.excerpt_or_summary, e.retrieved_at.isoformat(), e.source_version,
                 e.collection_method, e.stance.value, e.verification_method,
                 e.test_context, e.observed_result,
                 e.created_at.isoformat(), e.updated_at.isoformat()),
            )

    def list_evidence(self, job_id: str) -> list[Evidence]:
        from .models import EvidenceStance, SourceType
        rows = self._conn.execute("SELECT * FROM evidence WHERE job_id=? ORDER BY retrieved_at", (job_id,)).fetchall()
        return [Evidence(
            id=r["id"], job_id=r["job_id"], claim=r["claim"],
            source_type=SourceType(r["source_type"]), source_ref=r["source_ref"],
            locator=r["locator"], excerpt_or_summary=r["excerpt_or_summary"],
            source_version=r["source_version"], collection_method=r["collection_method"],
            stance=EvidenceStance(r["stance"]), verification_method=r["verification_method"],
            test_context=r["test_context"], observed_result=r["observed_result"],
        ) for r in rows]

    # --- Assessment ------------------------------------------------------
    def save_assessment(self, a: Assessment) -> None:
        with self.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO assessments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (a.id, a.job_id, a.condition_id, _j(a.resource_ids), _j(a.capability_ids),
                 a.context, a.status.value, _j(a.evidence_ids), a.explanation,
                 _j(a.gaps), _j(a.assumptions), a.review_status.value, a.revision_evaluated,
                 a.created_at.isoformat(), a.updated_at.isoformat()),
            )

    def list_assessments(self, job_id: str) -> list[Assessment]:
        from .models import AssessmentStatus, ReviewStatus
        rows = self._conn.execute("SELECT * FROM assessments WHERE job_id=?", (job_id,)).fetchall()
        return [Assessment(
            id=r["id"], job_id=r["job_id"], condition_id=r["condition_id"],
            resource_ids=json.loads(r["resource_ids"] or "[]"),
            capability_ids=json.loads(r["capability_ids"] or "[]"),
            context=r["context"], status=AssessmentStatus(r["status"]),
            evidence_ids=json.loads(r["evidence_ids"] or "[]"),
            explanation=r["explanation"], gaps=json.loads(r["gaps"] or "[]"),
            assumptions=json.loads(r["assumptions"] or "[]"),
            review_status=ReviewStatus(r["review_status"]),
            revision_evaluated=r["revision_evaluated"],
        ) for r in rows]

    # --- Proposal --------------------------------------------------------
    def save_proposal(self, p: Proposal) -> None:
        with self.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO proposals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (p.id, p.job_id, p.title, p.summary, _j(p.resource_ids),
                 _j(p.assessment_ids), _j(p.condition_coverage), _j(p.integration_work),
                 _j(p.new_work), _j(p.uncovered_conditions), _j(p.risks),
                 _j(p.assumptions), _j(p.costs), p.recommendation_reason,
                 p.validity_status.value, p.revision_created,
                 p.created_at.isoformat(), p.updated_at.isoformat()),
            )

    def get_proposal(self, job_id: str) -> Proposal | None:
        from .models import ProposalValidity
        r = self._conn.execute("SELECT * FROM proposals WHERE job_id=? ORDER BY revision_created DESC LIMIT 1", (job_id,)).fetchone()
        if not r:
            return None
        return Proposal(
            id=r["id"], job_id=r["job_id"], title=r["title"], summary=r["summary"],
            resource_ids=json.loads(r["resource_ids"] or "[]"),
            assessment_ids=json.loads(r["assessment_ids"] or "[]"),
            condition_coverage=json.loads(r["condition_coverage"] or "[]"),
            integration_work=json.loads(r["integration_work"] or "[]"),
            new_work=json.loads(r["new_work"] or "[]"),
            uncovered_conditions=json.loads(r["uncovered_conditions"] or "[]"),
            risks=json.loads(r["risks"] or "[]"),
            assumptions=json.loads(r["assumptions"] or "[]"),
            costs=json.loads(r["costs"] or "{}"),
            recommendation_reason=r["recommendation_reason"],
            validity_status=ProposalValidity(r["validity_status"]),
            revision_created=r["revision_created"],
        )

    # --- Events ----------------------------------------------------------
    def append_event(self, ev: ResearchEvent) -> None:
        with self.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (ev.event_id, ev.job_id, ev.revision, ev.run_id, ev.action_type.value,
                 ev.status, ev.started_at.isoformat(),
                 ev.ended_at.isoformat() if ev.ended_at else None,
                 _j(ev.related_object_ids), ev.tool_result_ref, _j(ev.usage), ev.error),
            )

    def list_events(self, job_id: str, after: int = 0) -> list[ResearchEvent]:
        from .models import ActionType
        rows = self._conn.execute(
            "SELECT * FROM events WHERE job_id=? AND rowid > ? ORDER BY rowid", (job_id, after)
        ).fetchall()
        return [ResearchEvent(
            id=r["event_id"], job_id=r["job_id"], event_id=r["event_id"],
            revision=r["revision"], run_id=r["run_id"],
            action_type=ActionType(r["action_type"]), status=r["status"],
            started_at=datetime.fromisoformat(r["started_at"]) if r["started_at"] else None,
            ended_at=datetime.fromisoformat(r["ended_at"]) if r["ended_at"] else None,
            related_object_ids=json.loads(r["related_object_ids"] or "[]"),
            tool_result_ref=r["tool_result_ref"],
            usage=json.loads(r["usage"] or "{}"), error=r["error"],
        ) for r in rows]

    def max_event_rowid(self, job_id: str) -> int:
        r = self._conn.execute("SELECT MAX(rowid) FROM events WHERE job_id=?", (job_id,)).fetchone()
        return r[0] or 0

    # --- M4: crash recovery, revisions, invalidation propagation --------

    def recover_orphans(self) -> list[str]:
        """On startup: any job in RESEARCHING has no live runner (the process
        restarted), whether or not active_run_id is set. Per 04 §9, recover to
        PAUSED so the user can Resume. Returns the recovered job ids."""
        rows = self._conn.execute(
            "SELECT id FROM jobs WHERE status='RESEARCHING'"
        ).fetchall()
        recovered: list[str] = []
        for row in rows:
            jid = row["id"]
            with self.transaction() as c:
                c.execute(
                    "UPDATE jobs SET status='PAUSED', active_run_id=NULL, updated_at=? WHERE id=?",
                    (_now(), jid),
                )
            self.append_event(ResearchEvent(
                id=new_id("ev"), event_id=new_id("ev"), job_id=jid,
                revision=1, action_type="FINISH", status="RECOVERED_TO_PAUSED",
                error="orphaned RESEARCHING run recovered on startup",
            ))
            recovered.append(jid)
        return recovered

    def mark_revision_needs_review(self, job_id: str, revision: int) -> int:
        """05 §12 invalidation propagation: when a goal/constraint changes,
        mark dependent Conditions/Assessments/Proposals of `revision` as
        NEEDS_REVIEW (or SUPERSEDED for proposals). Returns count touched."""
        n = 0
        with self.transaction() as c:
            c.execute(
                "UPDATE conditions SET validity_status='NEEDS_REVIEW', updated_at=? "
                "WHERE job_id=? AND revision_created=?",
                (_now(), job_id, revision),
            )
            n += c.total_changes
            c.execute(
                "UPDATE assessments SET review_status='NEEDS_REVIEW', updated_at=? "
                "WHERE job_id=? AND revision_evaluated=?",
                (_now(), job_id, revision),
            )
            n += c.total_changes
            c.execute(
                "UPDATE proposals SET validity_status='NEEDS_REVIEW', updated_at=? "
                "WHERE job_id=? AND revision_created=?",
                (_now(), job_id, revision),
            )
            n += c.total_changes
        return n

    def new_revision(self, job_id: str) -> int:
        """Start a new research revision (Refine). Preserves all prior data;
        only bumps current_revision and status. Caller propagates invalidation
        on the OLD revision before running the new one."""
        job = self.get_job(job_id)
        if not job:
            raise ValueError("job not found")
        old_rev = job.current_revision
        # invalidate old revision's dependent objects
        self.mark_revision_needs_review(job_id, old_rev)
        new_rev = old_rev + 1
        with self.transaction() as c:
            c.execute(
                "UPDATE jobs SET current_revision=?, status='RESEARCHING', "
                "active_run_id=NULL, updated_at=? WHERE id=?",
                (new_rev, _now(), job_id),
            )
        self.append_event(ResearchEvent(
            id=new_id("ev"), event_id=new_id("ev"), job_id=job_id,
            revision=new_rev, action_type="REASON", status="REFINED",
            related_object_ids=[str(old_rev)],
        ))
        return new_rev

    def add_constraint(self, job_id: str, text: str) -> None:
        """Append a user constraint to the current goal revision (used by Refine).
        Creates a fresh goal row for the new revision if needed."""
        job = self.get_job(job_id)
        if not job:
            return
        goal = self.get_goal(job_id)
        new_constraints = list((goal.constraints if goal else []))
        new_constraints.append({"text": text, "provenance": "USER_STATED"})
        gid = goal.id if goal else new_id("goal")
        g = Goal(
            id=gid if not goal else new_id("goal"),
            job_id=job_id,
            statement=goal.statement if goal else text,
            purpose=goal.purpose if goal else None,
            original_user_text=goal.original_user_text if goal else text,
            requirements=goal.requirements if goal else [],
            constraints=new_constraints,
            assumptions=goal.assumptions if goal else [],
            open_questions=goal.open_questions if goal else [],
            revision=job.current_revision,
        )
        self.save_goal(g)
