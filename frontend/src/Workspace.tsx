import { useEffect, useRef, useState } from "react";
import {
  cancelJob, exportUrl, getJob, startJob, subscribeEvents,
  type EventItem, type JobResult,
} from "./api";

interface WorkspaceProps {
  jobId: string;
  onBack: () => void;
}

const STATUS_COLOR: Record<string, string> = {
  CREATED: "created", RESEARCHING: "running", NEEDS_INPUT: "input",
  PAUSED: "paused", PARTIAL: "partial", FAILED: "failed",
  COMPLETED: "completed", CANCELLED: "cancelled",
};

export function Workspace({ jobId, onBack }: WorkspaceProps) {
  const [job, setJob] = useState<JobResult | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const stopRef = useRef<null | (() => void)>(null);

  const load = () => getJob(jobId).then(setJob).catch((e) => setErr(String(e)));

  useEffect(() => {
    load();
    const stop = subscribeEvents(jobId, (ev) => {
      setEvents((prev) => [...prev, ev]);
      load();
    }, () => load());
    stopRef.current = stop;
    return () => { stop(); };
  }, [jobId]);

  const start = async () => {
    setErr(null);
    try { await startJob(jobId); } catch (e) { setErr(String(e)); }
  };
  const cancel = async () => {
    try { await cancelJob(jobId); await load(); } catch (e) { setErr(String(e)); }
  };

  const running = job?.status === "RESEARCHING";

  return (
    <div className="workspace">
      <div className="topbar">
        <button className="ghost" onClick={onBack}>← Back</button>
        <span className={`badge ${STATUS_COLOR[job?.status || ""] || ""}`}>{job?.status}</span>
        <a className="ghost" href={exportUrl(jobId, "markdown")} target="_blank" rel="noreferrer">Export MD</a>
        <a className="ghost" href={exportUrl(jobId, "json")} target="_blank" rel="noreferrer">Export JSON</a>
      </div>

      {err && <div className="error">{err}</div>}

      <section className="goal">
        <h2>Goal</h2>
        <p className="orig">“{job?.original_request}”</p>
        <p className="muted">revision {job?.revision}</p>
      </section>

      <div className="controls">
        {(job?.status === "CREATED" || job?.status === "PAUSED" || job?.status === "FAILED") && (
          <button onClick={start} disabled={running}>{job?.status === "CREATED" ? "Start research" : "Resume"}</button>
        )}
        {running && <button className="danger" onClick={cancel}>Cancel</button>}
      </div>

      {events.length > 0 && (
        <section>
          <h3>Live research events</h3>
          <ul className="events">
            {events.map((e, i) => (
              <li key={i}>
                <span className="ev-type">{e.event_type}</span>
                {e.status && <span className="ev-status">{e.status}</span>}
                {e.tool && <span className="muted">tool: {e.tool}</span>}
                {e.error && <span className="error-inline">⚠ {e.error.slice(0, 120)}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h3>Proposal</h3>
        {job?.proposal ? (
          <div className="proposal">
            <h4>{job.proposal.title}</h4>
            <p>{job.proposal.summary}</p>
            <p className="muted">Reason: {job.proposal.recommendation_reason}</p>
            {job.proposal.risks.length > 0 && <p>Risks: {job.proposal.risks.join("; ")}</p>}
            <p className="cost">Costs: {JSON.stringify(job.proposal.costs)}</p>
            <p className="muted note">READY_FOR_REVIEW — not executed. Your decision required.</p>
          </div>
        ) : <p className="muted">No proposal yet.</p>}
      </section>

      <section>
        <h3>Conditions</h3>
        {job && job.conditions.length > 0 ? (
          <ul className="conditions">
            {job.conditions.map((c) => (
              <li key={c.id}>
                <span className={`obl ${c.obligation}`}>{c.obligation}</span>
                <span className={`dim ${c.dimension}`}>{c.dimension}</span>
                <span>{c.statement}</span>
              </li>
            ))}
          </ul>
        ) : <p className="muted">None derived yet.</p>}
      </section>

      <section>
        <h3>Resources</h3>
        {job && job.resources.length > 0 ? (
          <ul className="resources">
            {job.resources.map((r) => (
              <li key={r.id}>
                <strong>{r.name}</strong>
                <a href={r.canonical_source} target="_blank" rel="noreferrer"> source ↗</a>
                <span className={`lic ${r.license_claim === "UNKNOWN" ? "unknown" : ""}`}>
                  license: {r.license_claim || "UNKNOWN"}
                </span>
                <p className="muted">{r.description.slice(0, 180)}</p>
              </li>
            ))}
          </ul>
        ) : <p className="muted">No resources discovered yet.</p>}
      </section>

      <section>
        <h3>Assessments</h3>
        {job && job.assessments.length > 0 ? (
          <ul className="assessments">
            {job.assessments.map((a) => (
              <li key={a.id}>
                <span className={`astatus ${a.status}`}>{a.status}</span>
                <span>{a.explanation}</span>
                {a.gaps.length > 0 && <span className="muted"> gaps: {a.gaps.join("; ")}</span>}
              </li>
            ))}
          </ul>
        ) : <p className="muted">No assessments yet.</p>}
      </section>

      <section>
        <h3>Evidence</h3>
        {job && job.evidence.length > 0 ? job.evidence.map((e) => (
          <div key={e.id} className="evidence">
            <p>{e.claim}</p>
            <a href={e.source_ref} target="_blank" rel="noreferrer">{e.source_ref}</a>
            <p className="muted">locator: {e.locator}</p>
            <p className="muted">{e.excerpt_or_summary.slice(0, 160)}</p>
          </div>
        )) : <p className="muted">No evidence yet.</p>}
      </section>
    </div>
  );
}
