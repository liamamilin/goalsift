import { useEffect, useRef, useState } from "react";
import {
  cancelJob, exportUrl, getJob, sendInput, startJob, subscribeEvents,
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

const STATE_BANNER: Record<string, string> = {
  PARTIAL: "预算/工具/资料不足，结果不完整 — 可补充配置后继续。",
  FAILED: "研究出错 — 可查看事件中的错误并重试。",
  NEEDS_INPUT: "需要你的输入才能继续 — 请回答下方问题。",
};

export function Workspace({ jobId, onBack }: WorkspaceProps) {
  const [job, setJob] = useState<JobResult | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
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
  const submitInput = async () => {
    if (!inputText.trim()) return;
    setSending(true); setErr(null);
    try {
      await sendInput(jobId, inputText);
      setInputText("");
      await load();
    } catch (e) { setErr(String(e)); }
    finally { setSending(false); }
  };

  const running = job?.status === "RESEARCHING";
  // latest usage snapshot from events (budget panel)
  const lastUsage = [...events].reverse().find((e) => e.usage && Object.keys(e.usage).length);

  return (
    <div className="workspace">
      <div className="topbar">
        <button className="ghost" onClick={onBack}>← Back</button>
        <span className={`badge ${STATUS_COLOR[job?.status || ""] || ""}`}>{job?.status}</span>
        <a className="ghost" href={exportUrl(jobId, "markdown")} target="_blank" rel="noreferrer">Export MD</a>
        <a className="ghost" href={exportUrl(jobId, "json")} target="_blank" rel="noreferrer">Export JSON</a>
      </div>

      {err && <div className="error">{err}</div>}

      {job?.status && STATE_BANNER[job.status] && (
        <div className={`state-banner ${STATUS_COLOR[job.status]}`}>{STATE_BANNER[job.status]}</div>
      )}

      {lastUsage?.usage && (
        <div className="budget-panel">
          <span>actions: {String(lastUsage.usage.actions ?? "?")}</span>
          <span>tool calls: {String(lastUsage.usage.tool_calls ?? "?")}</span>
          {lastUsage.usage.cost_usd != null && <span>cost $: {String(lastUsage.usage.cost_usd)}</span>}
          {lastUsage.usage.elapsed_seconds != null && <span>elapsed s: {String(lastUsage.usage.elapsed_seconds)}</span>}
          {lastUsage.usage.stopped_reason ? <span className="error-inline">stopped: {String(lastUsage.usage.stopped_reason)}</span> : null}
        </div>
      )}

      <section className="goal">
        <h2>Goal</h2>
        <p className="orig">“{job?.original_request}”</p>
        <p className="muted">revision {job?.revision}</p>
        {job?.goal?.open_questions && job.goal.open_questions.length > 0 && (
          <div className="open-questions">
            <strong>需要澄清：</strong>
            <ul>{job.goal.open_questions.map((q, i) => <li key={i}>{q}</li>)}</ul>
          </div>
        )}
      </section>

      <div className="controls">
        {(job?.status === "CREATED" || job?.status === "PAUSED" || job?.status === "FAILED") && (
          <button onClick={start} disabled={running}>{job?.status === "CREATED" ? "Start research" : "Resume"}</button>
        )}
        {running && <button className="danger" onClick={cancel}>Cancel</button>}
      </div>

      {(job?.status === "NEEDS_INPUT" || job?.status === "COMPLETED") && (
        <section className="input-section">
          <h3>{job?.status === "NEEDS_INPUT" ? "回答澄清问题" : "继续研究（Refine）"}</h3>
          <textarea
            placeholder={job?.status === "NEEDS_INPUT"
              ? "回答上方问题，或说明在何种假设下继续…"
              : "追加约束，如：只能使用允许商业使用的开源方案"}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            rows={2}
          />
          <div className="row">
            <button onClick={submitInput} disabled={sending || !inputText.trim()}>
              {sending ? "提交中…" : (job?.status === "NEEDS_INPUT" ? "提交回答" : "提交新约束")}
            </button>
          </div>
        </section>
      )}

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
