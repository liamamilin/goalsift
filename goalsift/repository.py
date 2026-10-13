"""SQLite repository — isolated persistence for research state.

Implements 05 field contracts with tables for Job, Goal, Condition, Resource,
Capability, Evidence, Assessment, Proposal, Event. Writes go through
`validators` before commit (04 §5). Path-guarded: the DB lives in the
sanctioned data root only (AGENTS.md §7).
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
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
CREATE TABLE IF NOT EXISTS checkpoints (
  job_id TEXT, revision INTEGER, data TEXT NOT NULL,
  PRIMARY KEY(job_id, revision)
);
CREATE TABLE IF NOT EXISTS revision_snapshots (
  job_id TEXT, revision INTEGER, data TEXT NOT NULL, created_at TEXT,
  PRIMARY KEY(job_id, revision)
);
CREATE TABLE IF NOT EXISTS proposal_decisions (
  decision_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, source_revision INTEGER NOT NULL,
  proposal_id TEXT NOT NULL, action TEXT NOT NULL, reason TEXT NOT NULL,
  annotation_version INTEGER NOT NULL, created_at TEXT NOT NULL,
  UNIQUE(job_id, annotation_version)
);
CREATE INDEX IF NOT EXISTS idx_proposal_decisions_job_revision
  ON proposal_decisions(job_id, source_revision, annotation_version);
CREATE TABLE IF NOT EXISTS checklist_annotations (
  annotation_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, source_revision INTEGER NOT NULL,
  item_id TEXT NOT NULL, basis_hash TEXT NOT NULL, status TEXT NOT NULL,
  notes TEXT NOT NULL, annotation_version INTEGER NOT NULL, created_at TEXT NOT NULL,
  UNIQUE(job_id, source_revision, item_id, annotation_version)
);
CREATE INDEX IF NOT EXISTS idx_checklist_annotations_item
  ON checklist_annotations(job_id, source_revision, item_id, annotation_version);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _j(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def synchronized(method):
    """Serialize an entire read/write operation on the shared SQLite connection.

    FastAPI sync endpoints run in worker threads while the controller uses the
    event loop. Locking just writes leaves cursors racing with commits/close.
    The reentrant lock also makes compound views a consistent read.
    """
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return wrapped


class Repository:
    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = resolve_under_root("goalsift.sqlite")
        self.db_path = str(resolve_under_root(db_path))
        self._lock = threading.RLock()
        self._tx_depth = 0
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        # Additive upgrades keep existing data and immutable snapshots intact.
        for table, column, default in (
            ('goals', 'condition_decisions', "'[]'"),
            ('goals', 'assumption_decisions', "'[]'"),
            ('conditions', 'provenance', "'SYSTEM_ASSUMED'"),
            ('conditions', 'lineage_id', 'NULL'),
        ):
            columns = {r['name'] for r in self._conn.execute(f'PRAGMA table_info({table})')}
            if column not in columns:
                nullable = '' if column == 'lineage_id' else 'NOT NULL '
                self._conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} TEXT {nullable}DEFAULT {default}')
        self._conn.commit()
        # write-ahead for concurrency
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            depth = self._tx_depth
            name = f"nested_{depth}"
            self._conn.execute("BEGIN IMMEDIATE" if not depth else f"SAVEPOINT {name}")
            self._tx_depth += 1
            try:
                yield self._conn
                self._conn.execute("COMMIT" if not depth else f"RELEASE SAVEPOINT {name}")
            except BaseException:
                self._conn.execute("ROLLBACK" if not depth else f"ROLLBACK TO SAVEPOINT {name}")
                if depth:
                    self._conn.execute(f"RELEASE SAVEPOINT {name}")
                raise
            finally:
                self._tx_depth -= 1

    @synchronized
    def close(self) -> None:
        self._conn.close()

    # --- Job -------------------------------------------------------------
    @synchronized
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

    @synchronized
    def set_job_status(self, job_id: str, status: str, **extra: Any) -> None:
        cols = ["status=?", "updated_at=?"]
        vals: list[Any] = [status, _now()]
        for k, v in extra.items():
            if k in ("current_goal_id", "current_revision", "active_run_id", "checkpoint_ref", "budget_config", "budget_usage"):
                cols.append(f"{k}=?")
                vals.append(_j(v) if k in ("budget_config", "budget_usage") else v)
        vals.append(job_id)
        with self.transaction() as c:
            c.execute(f"UPDATE jobs SET {', '.join(cols)} WHERE id=?", vals)

    @synchronized
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
            created_at=r["created_at"], updated_at=r["updated_at"],
        )

    @synchronized
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
            created_at=r["created_at"], updated_at=r["updated_at"],
        )

    # --- Goal ------------------------------------------------------------
    @synchronized
    def save_goal(self, g: Goal) -> None:
        with self.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO goals (id,job_id,statement,purpose,revision,original_user_text,requirements,constraints,assumptions,open_questions,created_at,updated_at,condition_decisions,assumption_decisions) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (g.id, g.job_id, g.statement, g.purpose, g.revision,
                 g.original_user_text, _j(g.requirements), _j(g.constraints),
                 _j(g.assumptions), _j(g.open_questions),
                 g.created_at.isoformat(), g.updated_at.isoformat(),
                 _j(g.condition_decisions), _j(g.assumption_decisions)),
            )

    @synchronized
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
            condition_decisions=json.loads(r['condition_decisions']),
            assumption_decisions=json.loads(r['assumption_decisions']),
            created_at=r["created_at"], updated_at=r["updated_at"],
        )

    # --- Condition -------------------------------------------------------
    @synchronized
    def save_condition(self, c_obj: Condition) -> None:
        with self.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO conditions (id,job_id,statement,obligation,dimension,origin,source_refs,scope,verification_method,relations,validity_status,revision_created,created_at,updated_at,provenance,lineage_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (c_obj.id, c_obj.job_id, c_obj.statement, c_obj.obligation.value,
                 c_obj.dimension.value, c_obj.origin, _j(c_obj.source_refs),
                 c_obj.scope, c_obj.verification_method, _j(c_obj.relations),
                 c_obj.validity_status.value, c_obj.revision_created,
                 c_obj.created_at.isoformat(), c_obj.updated_at.isoformat(), c_obj.provenance.value, c_obj.lineage_id),
            )

    @synchronized
    def list_conditions(self, job_id: str) -> list[Condition]:
        rows = self._conn.execute("SELECT * FROM conditions WHERE job_id=? ORDER BY created_at", (job_id,)).fetchall()
        from .models import Dimension, Obligation, ValidityStatus
        return [Condition(
            id=r["id"], job_id=r["job_id"], statement=r["statement"],
            obligation=Obligation(r["obligation"]), dimension=Dimension(r["dimension"]),
            origin=r["origin"], source_refs=json.loads(r["source_refs"] or "[]"),
            provenance=r['provenance'],
            lineage_id=r['lineage_id'],
            scope=r["scope"], verification_method=r["verification_method"],
            relations=json.loads(r["relations"] or "[]"),
            validity_status=ValidityStatus(r["validity_status"]),
            revision_created=r["revision_created"],
            created_at=r["created_at"], updated_at=r["updated_at"],
        ) for r in rows]

    # --- Resource --------------------------------------------------------
    @synchronized
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

    @synchronized
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
            discovered_at=r["discovered_at"], created_at=r["created_at"], updated_at=r["updated_at"],
        ) for r in rows]

    # --- Capability ------------------------------------------------------
    @synchronized
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

    @synchronized
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
            created_at=r["created_at"], updated_at=r["updated_at"],
        ) for r in rows]

    # --- Evidence --------------------------------------------------------
    @synchronized
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

    @synchronized
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
            retrieved_at=r["retrieved_at"], created_at=r["created_at"], updated_at=r["updated_at"],
        ) for r in rows]

    # --- Assessment ------------------------------------------------------
    @synchronized
    def save_assessment(self, a: Assessment) -> None:
        with self.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO assessments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (a.id, a.job_id, a.condition_id, _j(a.resource_ids), _j(a.capability_ids),
                 a.context, a.status.value, _j(a.evidence_ids), a.explanation,
                 _j(a.gaps), _j(a.assumptions), a.review_status.value, a.revision_evaluated,
                 a.created_at.isoformat(), a.updated_at.isoformat()),
            )

    @synchronized
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
            created_at=r["created_at"], updated_at=r["updated_at"],
        ) for r in rows]

    # --- Proposal --------------------------------------------------------
    @synchronized
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

    @synchronized
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
            created_at=r["created_at"], updated_at=r["updated_at"],
        )

    # --- Events ----------------------------------------------------------
    @synchronized
    def append_event(self, ev: ResearchEvent) -> None:
        with self.transaction() as c:
            c.execute(
                "INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (ev.event_id, ev.job_id, ev.revision, ev.run_id, ev.action_type.value,
                 ev.status, ev.started_at.isoformat(),
                 ev.ended_at.isoformat() if ev.ended_at else None,
                 _j(ev.related_object_ids), ev.tool_result_ref, _j(ev.usage), ev.error),
            )

    @synchronized
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

    @synchronized
    def max_event_rowid(self, job_id: str) -> int:
        r = self._conn.execute("SELECT MAX(rowid) FROM events WHERE job_id=?", (job_id,)).fetchone()
        return r[0] or 0

    @synchronized
    def annotation_records_at_event_cursor(self, job_id: str, cursor: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return user annotations whose append-only audit event is at/before cursor."""
        decision_ids: set[str] = set()
        checklist_ids: set[str] = set()
        rows = self._conn.execute(
            "SELECT action_type, status, related_object_ids FROM events "
            "WHERE job_id=? AND rowid<=? AND action_type='REVISE' ORDER BY rowid",
            (job_id, cursor),
        ).fetchall()
        for row in rows:
            status = row["status"] or ""
            if not (status.startswith("PROPOSAL_") or status.startswith("ADOPTION_CHECK_")):
                continue
            try:
                related = json.loads(row["related_object_ids"] or "[]")
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(related, list) or len(related) < 2:
                continue
            if status.startswith("PROPOSAL_"):
                decision_ids.add(str(related[-1]))
            else:
                checklist_ids.add(str(related[-1]))

        def records(table: str, key: str, ids: set[str]) -> list[dict[str, Any]]:
            if not ids:
                return []
            placeholders = ",".join("?" for _ in ids)
            found = self._conn.execute(
                f"SELECT * FROM {table} WHERE job_id=? AND {key} IN ({placeholders})",
                (job_id, *sorted(ids)),
            ).fetchall()
            return [dict(row) for row in found]

        decisions = records("proposal_decisions", "decision_id", decision_ids)
        checklist = records("checklist_annotations", "annotation_id", checklist_ids)
        decisions.sort(key=lambda r: r["annotation_version"])
        checklist.sort(key=lambda r: (r["source_revision"], r["item_id"], r["annotation_version"]))
        return decisions, checklist

    # --- M4: crash recovery, revisions, invalidation propagation --------

    @synchronized
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

    @synchronized
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

    @synchronized
    def new_revision(self, job_id: str) -> int:
        """Atomically preserve the completed revision and create its successor."""
        from .models import JobStatus
        with self.transaction():
            job = self.get_job(job_id)
            if not job or job.status != JobStatus.COMPLETED or job.active_run_id:
                raise ValueError("only a completed, idle job can be refined")
            old_rev = job.current_revision
            self.snapshot_revision(job_id)
            self.mark_revision_needs_review(job_id, old_rev)
            new_rev = old_rev + 1
            goal = self.get_goal(job_id)
            if goal:
                goal = goal.model_copy(deep=True)
                goal.id = new_id("goal")
                goal.revision = new_rev
                goal.open_questions = []
                self.save_goal(goal)
            self.set_job_status(job_id, JobStatus.RESEARCHING.value,
                                current_revision=new_rev, active_run_id=None,
                                current_goal_id=goal.id if goal else None,
                                budget_usage={}, checkpoint_ref=None)
            self.append_event(ResearchEvent(
                id=new_id("ev"), event_id=new_id("ev"), job_id=job_id,
                revision=new_rev, action_type="REVISE", status="REFINED",
                related_object_ids=[str(old_rev)],
            ))
            return new_rev

    @synchronized
    def add_constraint(self, job_id: str, text: str) -> None:
        """Append a user constraint to the current goal revision (used by Refine
        and NEEDS_INPUT answers). Updates the existing goal in place so
        get_goal reflects the clarification immediately."""
        job = self.get_job(job_id)
        if not job:
            return
        goal = self.get_goal(job_id)
        if goal:
            new_constraints = list(goal.constraints)
            new_constraints.append({"text": text, "provenance": "USER_STATED"})
            goal.constraints = new_constraints
            goal.updated_at = datetime.now(timezone.utc)
            self.save_goal(goal)  # INSERT OR REPLACE on same id -> in-place update
        else:
            g = Goal(
                id=new_id("goal"), job_id=job_id, statement=text,
                original_user_text=text, revision=job.current_revision,
                constraints=[{"text": text, "provenance": "USER_STATED"}],
            )
            self.save_goal(g)

    # Controller ownership is a database compare-and-set, not a UI lock.
    @synchronized
    def claim_run(self, job_id: str, run_id: str, *, refine: bool = False) -> bool:
        from .models import JobStatus
        from .validators import validate_transition, ValidationError
        with self.transaction() as conn:
            job = self.get_job(job_id)
            if not job or job.active_run_id:
                return False
            if job.status == JobStatus.COMPLETED or job.status == JobStatus.CANCELLED:
                return False
            if not (refine and job.status == JobStatus.RESEARCHING):
                try:
                    validate_transition(job.status, JobStatus.RESEARCHING)
                except ValidationError:
                    return False
            changed = conn.execute(
                "UPDATE jobs SET status='RESEARCHING', active_run_id=?, updated_at=?, checkpoint_ref=NULL "
                "WHERE id=? AND active_run_id IS NULL AND current_revision=?",
                (run_id, _now(), job_id, job.current_revision),
            ).rowcount
            return changed == 1

    @synchronized
    def owns_run(self, job_id: str, run_id: str, revision: int) -> bool:
        job = self.get_job(job_id)
        return bool(job and job.active_run_id == run_id
                    and job.current_revision == revision and job.status.value == "RESEARCHING")

    @synchronized
    def finish_run(self, job_id: str, run_id: str, revision: int, status: str,
                   usage: dict | None = None, reason: str | None = None) -> bool:
        from .models import JobStatus
        from .validators import validate_transition
        with self.transaction():
            if not self.owns_run(job_id, run_id, revision):
                return False
            validate_transition(JobStatus.RESEARCHING, JobStatus(status))
            self.set_job_status(job_id, status, active_run_id=None,
                                budget_usage=usage or {}, checkpoint_ref=reason)
            return True

    @synchronized
    def get_checkpoint(self, job_id: str, revision: int) -> dict:
        with self._lock:
            row = self._conn.execute(
                "SELECT data FROM checkpoints WHERE job_id=? AND revision=?", (job_id, revision)
            ).fetchone()
            return json.loads(row[0]) if row else {}

    @synchronized
    def save_checkpoint(self, job_id: str, revision: int, data: dict) -> None:
        with self.transaction() as conn:
            conn.execute("INSERT OR REPLACE INTO checkpoints VALUES (?,?,?)",
                         (job_id, revision, _j(data)))

    @synchronized
    def current_view(self, job_id: str) -> dict:
        """One consistent revision view shared by the UI, validators and exports."""
        with self._lock:
            job = self.get_job(job_id)
            if not job:
                raise KeyError(job_id)
            rev = job.current_revision
            state = self.get_checkpoint(job_id, rev)
            conditions = [c for c in self.list_conditions(job_id)
                          if c.revision_created == rev and c.validity_status.value == "ACTIVE"]
            cond_ids = {c.id for c in conditions}
            assessments = [a for a in self.list_assessments(job_id)
                           if a.revision_evaluated == rev and a.review_status.value == "CURRENT"
                           and a.condition_id in cond_ids]
            resource_ids = set(state.get("resource_ids", []))
            resource_ids.update(rid for a in assessments for rid in a.resource_ids)
            # Legacy completed runs predate checkpoints; their assessments are authoritative.
            proposal = self.get_proposal(job_id)
            if proposal and (proposal.revision_created != rev or
                             proposal.validity_status.value != "READY_FOR_REVIEW"):
                proposal = None
            if proposal:
                resource_ids.update(proposal.resource_ids)
            resources = [r for r in self.list_resources(job_id) if r.id in resource_ids]
            capabilities = [c for c in self.list_capabilities(job_id) if c.resource_id in resource_ids]
            evidence_ids = set(state.get("evidence_ids", []))
            evidence_ids.update(eid for c in capabilities for eid in c.evidence_ids)
            evidence_ids.update(eid for a in assessments for eid in a.evidence_ids)
            evidence = [e for e in self.list_evidence(job_id) if e.id in evidence_ids]
            goal = self.get_goal(job_id)
            return {
                "id": job.id, "status": job.status.value, "revision": rev,
                "original_request": job.original_request,
                "goal": goal.model_dump(mode="json") if goal else None,
                "conditions": [c.model_dump(mode="json") for c in conditions],
                "resources": [r.model_dump(mode="json") for r in resources],
                "capabilities": [c.model_dump(mode="json") for c in capabilities],
                "evidence": [e.model_dump(mode="json") for e in evidence],
                "assessments": [a.model_dump(mode="json") for a in assessments],
                "proposal": proposal.model_dump(mode="json") if proposal else None,
                "budget_usage": job.budget_usage,
                "budget_config": job.budget_config,
                "checkpoint": state.get("stage", "define"),
                "stopped_reason": job.checkpoint_ref,
                "delivery_notes": state.get("delivery_notes", []),
                "source_reviews": state.get("source_reviews", {}),
                "research_scope": state.get("research_scope"),
                "reused_assessment_ids": state.get("reused_assessment_ids", []),
            }

    @synchronized
    def snapshot_revision(self, job_id: str) -> None:
        view = self.current_view(job_id)
        with self.transaction() as conn:
            conn.execute("INSERT OR IGNORE INTO revision_snapshots VALUES (?,?,?,?)",
                         (job_id, view["revision"], _j(view), _now()))

    @synchronized
    def get_revision(self, job_id: str, revision: int) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data FROM revision_snapshots WHERE job_id=? AND revision=?", (job_id, revision)
            ).fetchone()
            return json.loads(row[0]) if row else None

    @synchronized
    def proposal_decisions(self, job_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM proposal_decisions WHERE job_id=? ORDER BY annotation_version",
            (job_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    @synchronized
    def latest_proposal_decision_version(self, job_id: str) -> int:
        row = self._conn.execute(
            "SELECT MAX(annotation_version) FROM proposal_decisions WHERE job_id=?", (job_id,)
        ).fetchone()
        return int(row[0] or 0)

    @synchronized
    def append_proposal_decision(self, decision: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO proposal_decisions VALUES (?,?,?,?,?,?,?,?)",
                (decision["decision_id"], decision["job_id"], decision["source_revision"],
                 decision["proposal_id"], decision["action"], decision["reason"],
                 decision["annotation_version"], decision["created_at"]),
            )

    @synchronized
    def checklist_annotations(self, job_id: str, revision: int) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM checklist_annotations WHERE job_id=? AND source_revision=? ORDER BY item_id, annotation_version",
            (job_id, revision),
        ).fetchall()
        return [dict(row) for row in rows]

    @synchronized
    def latest_checklist_annotation(self, job_id: str, revision: int, item_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM checklist_annotations WHERE job_id=? AND source_revision=? AND item_id=? ORDER BY annotation_version DESC LIMIT 1",
            (job_id, revision, item_id),
        ).fetchone()
        return dict(row) if row else None

    @synchronized
    def append_checklist_annotation(self, annotation: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO checklist_annotations VALUES (?,?,?,?,?,?,?,?,?)",
                (annotation["annotation_id"], annotation["job_id"], annotation["source_revision"],
                 annotation["item_id"], annotation["basis_hash"], annotation["status"],
                 annotation["notes"], annotation["annotation_version"], annotation["created_at"]),
            )

    @synchronized
    def list_revisions(self, job_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT revision, created_at FROM revision_snapshots WHERE job_id=? ORDER BY revision DESC",
                (job_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    @synchronized
    def events_page(self, job_id: str, after: int = 0) -> list[dict]:
        from .security import redact_secrets
        with self._lock:
            rows = self._conn.execute(
                "SELECT rowid AS cursor, * FROM events WHERE job_id=? AND rowid>? ORDER BY rowid",
                (job_id, after),
            ).fetchall()
            return [{"cursor": r["cursor"], "event_id": r["event_id"],
                     "revision": r["revision"], "event_type": r["action_type"],
                     "status": r["status"], "timestamp": r["started_at"],
                     "related": json.loads(r["related_object_ids"] or "[]"),
                     "error": redact_secrets(r["error"] or "") or None,
                     "usage": json.loads(r["usage"] or "{}"), "tool": r["tool_result_ref"]}
                    for r in rows]
