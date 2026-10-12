export const API = import.meta.env.VITE_API_BASE_URL ?? "";

export type JobStatus =
  | "CREATED" | "RESEARCHING" | "NEEDS_INPUT" | "PAUSED"
  | "PARTIAL" | "FAILED" | "COMPLETED" | "CANCELLED";

export interface GoalBrief {
  id: string;
  statement: string;
  purpose?: string;
  original_user_text: string;
  revision: number;
  requirements?: {text: string; provenance: string}[];
  condition_decisions?: {action: string; original_statement: string; statement: string; revision: number}[];
  assumption_decisions?: {action: string; text: string; revision: number}[];
  open_questions?: string[];
  constraints?: {text: string; provenance: string}[];
  assumptions?: {text: string; provenance: string}[];
}

export interface Condition {
  id: string;
  statement: string;
  obligation: "REQUIRED" | "OPTIONAL";
  dimension: "FUNCTIONAL" | "QUALITY" | "COMPLIANCE" | "OTHER";
  origin?: string;
  provenance?: "USER_STATED" | "USER_CONFIRMED" | "SYSTEM_ASSUMED";
  lineage_id?: string | null;
  verification_method?: string;
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
  resource_ids?: string[];
  capability_ids?: string[];
  evidence_ids?: string[];
}

export interface ProposalItem {
  id: string;
  title: string;
  summary: string;
  risks: string[];
  costs: Record<string, unknown>;
  recommendation_reason: string;
  validity_status: string;
  integration_work?: string[];
  new_work?: string[];
  assessment_ids?: string[];
  uncovered_conditions?: string[];
  condition_coverage?: string[];
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
  budget_usage?: UsageSnapshot;
  stopped_reason?: string | null;
  delivery_notes?: string[];
  source_reviews?: Record<string, {status?: string; documents: {url: string; category: string; version?: string}[]; notes: string[]; match_context?: {evidence_id: string; url: string; stored_characters: number; supplied_characters: number; is_partial: boolean; excerpt_ranges: [number, number][]}[]}>;
  research_scope?: {type: string; base_revision: number; condition_ids: string[]; resource_ids: string[]; refreshed_resource_ids: string[]; budget_usd: number; question: string} | null;
  reused_assessment_ids?: string[];
}

export interface ResearchRequest {
  expected_revision: number;
  condition_ids: string[];
  resource_ids: string[];
  budget_usd: number;
  question: string;
}
export async function investigate(id: string, body: ResearchRequest): Promise<void> {
  const r = await fetch(`${API}/api/jobs/${id}/investigate`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  if (!r.ok) { const error = await r.json().catch(() => null); throw new Error(typeof error?.detail === "string" ? error.detail : "补查未提交，请检查内容后重试"); }
}
export interface RevisionDiff {
  base_revision: number; target_revision: number; target_status: JobStatus; is_partial: boolean;
  scope: JobResult["research_scope"]; goal_changes: string[];
  conditions: {added: Condition[]; removed: Condition[]; changed: {before: Condition; after: Condition}[]; unchanged: number};
  resources: {before: ResourceItem | null; after: ResourceItem | null}[];
  documents: {url: string; kind: "new" | "changed" | "reread"; category: string; version: string | null; before_version: string | null; retrieved_at: string}[];
  assessment_changes: {condition: string; condition_id: string; resource: string; url: string; before: string[]; after: string[]; before_explanations: string[]; explanations: string[]; gaps: string[]}[];
  newly_covered: string[]; newly_uncovered: string[];
  summary: {new_sources: number; changed_sources: number; reread_sources: number; new_evidence: number; reused_assessments: number; coverage_before: number; coverage_after: number; conditions_before: number; conditions_after: number};
  usage: {before: UsageSnapshot; after: UsageSnapshot};
}
export async function compareRevisions(id: string, base: number, target?: number): Promise<RevisionDiff> {
  const r = await fetch(`${API}/api/jobs/${id}/compare?base=${base}${target ? `&target=${target}` : ""}`);
  if (!r.ok) throw new Error("无法读取修订比较，请刷新后重试");
  return r.json();
}

export interface ConditionEdit {
  condition_id: string;
  action: "confirm" | "update" | "remove";
  statement?: string;
  obligation?: Condition["obligation"];
  dimension?: Condition["dimension"];
  verification_method?: string;
}
export interface GoalReview {
  expected_revision: number;
  conditions: ConditionEdit[];
  assumptions: {index: number; action: "confirm" | "remove"}[];
  purpose?: string;
}
export async function reviewGoal(id: string, review: GoalReview): Promise<void> {
  const r = await fetch(`${API}/api/jobs/${id}/review`, {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(review),
  });
  if (!r.ok) {
    const body = await r.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : "调整未提交，请检查内容后重试");
  }
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
  if (!r.ok) throw new Error(`start failed: ${r.status} ${await r.text()}`);
}

export async function cancelJob(id: string): Promise<void> {
  const r = await fetch(`${API}/api/jobs/${id}/cancel`, { method: "POST" });
  if (!r.ok) throw new Error(`cancel failed: ${r.status} ${await r.text()}`);
}

export async function sendInput(id: string, text: string): Promise<void> {
  /** Refine (COMPLETED) or answer a clarifying question (NEEDS_INPUT). */
  const r = await fetch(`${API}/api/jobs/${id}/input`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ constraint: text }),
  });
  if (!r.ok) throw new Error(`input failed: ${r.status} ${await r.text()}`);
}

export function exportUrl(id: string, fmt: "markdown" | "json", revision?: number): string {
  return `${API}/api/jobs/${id}/export?fmt=${fmt}${revision ? `&revision=${revision}` : ""}`;
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

export interface UsageSnapshot {
  actions?: number;
  tool_calls?: number;
  cost_usd?: number | null;
  input_tokens?: number;
  output_tokens?: number;
  cost_unknown?: boolean;
  reserved_usd?: number;
  elapsed_seconds?: number;
  stopped_reason?: string | null;
  [k: string]: unknown;
}

export interface EventItem {
  event_id?: string;
  cursor?: number;
  revision?: number;
  event_type: string;
  status?: string;
  timestamp?: string;
  error?: string;
  usage?: UsageSnapshot;
  tool?: string;
}

/** Native SSE reconnects with Last-Event-ID. Workspace restarts streams for new runs. */
export function subscribeEvents(
  jobId: string,
  onEvent: (e: EventItem) => void,
  onDone: () => void,
  last = 0,
  onError?: () => void,
): () => void {
  const stream = new EventSource(`${API}/api/jobs/${jobId}/events?last=${last}`);
  stream.onmessage = ({ data }) => {
    try {
      const ev = JSON.parse(data) as EventItem;
      if (ev.event_type === "DONE") { stream.close(); onDone(); return; }
      onEvent(ev);
    } catch { onError?.(); }
  };
  stream.onerror = () => onError?.();
  return () => stream.close();
}

export async function pauseJob(id: string): Promise<void> {
  const r = await fetch(`${API}/api/jobs/${id}/pause`, { method: "POST" });
  if (!r.ok) throw new Error(`pause failed: ${r.status} ${await r.text()}`);
}
export interface RevisionItem { revision: number; created_at: string }
export async function listRevisions(id: string): Promise<RevisionItem[]> {
  const r = await fetch(`${API}/api/jobs/${id}/revisions`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function getRevision(id: string, revision: number): Promise<JobResult> {
  const r = await fetch(`${API}/api/jobs/${id}/revisions/${revision}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
