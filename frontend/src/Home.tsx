import { useEffect, useState } from "react";
import { createJob, listJobs, type JobListItem } from "./api";

interface HomeProps {
  onOpen: (id: string) => void;
}

export function Home({ onOpen }: HomeProps) {
  const [text, setText] = useState("");
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => listJobs().then(setJobs).catch((e) => setErr(String(e)));
  useEffect(() => { refresh(); }, []);

  const submit = async () => {
    if (!text.trim()) return;
    setBusy(true); setErr(null);
    try {
      const r = await createJob(text);
      setText("");
      await refresh();
      onOpen(r.id);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="home">
      <h1>GoalSift</h1>
      <p className="tag">From Goals to Viable Paths — describe an outcome, get researched, evidence-backed paths for your decision.</p>
      <textarea
        placeholder="e.g. 我要一个像成熟商业产品一样好看的 Agent 管理网页，接入我现在运行的多个 Agent。"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
      />
      <div className="row">
        <button onClick={submit} disabled={busy || !text.trim()}>{busy ? "Creating…" : "Create research job"}</button>
        <button className="ghost" onClick={refresh}>Refresh</button>
      </div>
      {err && <div className="error">{err}</div>}
      <h2>Jobs</h2>
      {jobs.length === 0 ? <p className="muted">No jobs yet.</p> : (
        <ul className="joblist">
          {jobs.map((j) => (
            <li key={j.id} onClick={() => onOpen(j.id)}>
              <span className={`badge ${j.status}`}>{j.status}</span>
              <span className="req">{j.original_request}</span>
              <span className="muted">rev {j.revision}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
