export const API = "http://127.0.0.1:8000";

export type JobStatus =
  | "CREATED" | "RESEARCHING" | "NEEDS_INPUT" | "PAUSED"
  | "PARTIAL" | "FAILED" | "COMPLETED" | "CANCELLED";

export interface GoalBrief {
  id: string;
  statement: string;
  original_user_text: string;
  revision: number;
}

export interface Condition {
  id: string;
  statement: string;
  obligation: "REQUIRED" | "OPTIONAL";
  dimension: "FUNCTIONAL" | "QUALITY" | "COMPLIANCE" | "OTHER";
}

export interface ResourceItem {
  id: string;
  name: string;
  kind: string;
  canonical_source: string;
  license_claim: string | null;
  description: string;
}

export interface EvidenceItem {
  id: string;
  claim: string;
  source_ref: string;
  locator: string;
  excerpt_or_summary: string;
}

export interface AssessmentItem {
  id: string;
  condition_id: string;
  status: "VERIFIED" | "SUPPORTED" | "PARTIAL" | "NOT_SATISFIED" | "UNKNOWN" | "CONFLICTED";
  explanation: string;
  gaps: string[];
}

export interface ProposalItem {
  id: string;
  title: string;
  summary: string;
  risks: string[];
  costs: Record<string, unknown>;
  recommendation_reason: string;
  validity_status: string;
}

export interface JobResult {
  id: string;
  status: JobStatus;
  revision: number;
  original_request: string;
  goal: GoalBrief | null;
  conditions: Condition[];
  resources: ResourceItem[];
  evidence: EvidenceItem[];
  assessments: AssessmentItem[];
  proposal: ProposalItem | null;
}

export interface JobListItem {
  id: string;
  status: JobStatus;
  original_request: string;
  revision: number;
}

export async function createJob(request: string): Promise<{ id: string; status: string }> {
  const r = await fetch(`${API}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request }),
  });
  if (!r.ok) throw new Error(`create failed: ${r.status}`);
  return r.json();
}

export async function listJobs(): Promise<JobListItem[]> {
  const r = await fetch(`${API}/api/jobs`);
  if (!r.ok) throw new Error(`list failed: ${r.status}`);
  return r.json();
}

export async function getJob(id: string): Promise<JobResult> {
  const r = await fetch(`${API}/api/jobs/${id}`);
  if (!r.ok) throw new Error(`get failed: ${r.status}`);
  return r.json();
}

export async function startJob(id: string): Promise<void> {
  const r = await fetch(`${API}/api/jobs/${id}/start`, { method: "POST" });
  if (!r.ok && r.status !== 409) throw new Error(`start failed: ${r.status}`);
}

export async function cancelJob(id: string): Promise<void> {
  const r = await fetch(`${API}/api/jobs/${id}/cancel`, { method: "POST" });
  if (!r.ok && r.status !== 409) throw new Error(`cancel failed: ${r.status}`);
}

export function exportUrl(id: string, fmt: "markdown" | "json"): string {
  return `${API}/api/jobs/${id}/export?fmt=${fmt}`;
}

export interface Settings {
  llm: { configured: boolean; provider: string; model: string; key_preview: string };
  search: { configured: boolean; provider: string; key_preview: string };
  budget: {
    max_actions: number;
    max_tool_calls: number;
    max_runtime_seconds: number;
    budget_usd: string;
  };
  binding: string;
  note: string;
}

export async function getSettings(): Promise<Settings> {
  const r = await fetch(`${API}/api/settings`);
  if (!r.ok) throw new Error(`settings failed: ${r.status}`);
  return r.json();
}

export interface EventItem {
  event_id?: string;
  event_type: string;
  status?: string;
  timestamp?: string;
  error?: string;
  usage?: Record<string, unknown>;
  tool?: string;
}

/** SSE subscription that resyncs from last event id (04 §10). */
export function subscribeEvents(
  jobId: string,
  onEvent: (e: EventItem) => void,
  onDone: () => void
): () => void {
  const ctrl = new AbortController();
  fetch(`${API}/api/jobs/${jobId}/events`, { signal: ctrl.signal, headers: { Accept: "text/event-stream" } })
    .then(async (resp) => {
      if (!resp.body) return;
      const reader = resp.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() || "";
        for (const part of parts) {
          const line = part.replace(/^data: /, "").trim();
          if (!line) continue;
          try {
            const ev = JSON.parse(line) as EventItem;
            onEvent(ev);
            if (ev.event_type === "DONE") { onDone(); return; }
          } catch { /* skip partial */ }
        }
      }
    })
    .catch(() => {});
  return () => ctrl.abort();
}
