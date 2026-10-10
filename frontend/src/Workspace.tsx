import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  cancelJob, exportUrl, getJob, sendInput, startJob, subscribeEvents, pauseJob, listRevisions, getRevision, type RevisionItem,
  type AssessmentItem, type Condition, type EventItem, type JobResult, type JobStatus,
  type ProposalItem, type ResourceItem,
} from "./api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  AlertTriangle, ArrowLeft, CheckCircle2, Clock, Compass, DollarSign, ExternalLink,
  FileDown, FlaskRound, Layers, Lightbulb, Loader2, MessageSquare, Package, Play,
  ShieldCheck, Sparkles, Target, XCircle, ChevronRight,
} from "lucide-react";
import { runWorkspaceTour, stopTour, hasSeenTour as tourSeen } from "./tour";
import { Panel, Group } from "react-resizable-panels";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const STATUS_CONFIG: Record<JobStatus, { tone: string; icon: React.ReactNode; label: string }> = {
  CREATED: { tone: "bg-muted text-muted-foreground", icon: <Clock className="h-3 w-3" />, label: "Created" },
  RESEARCHING: { tone: "bg-primary text-primary-foreground", icon: <Loader2 className="h-3 w-3 animate-spin" />, label: "Researching" },
  NEEDS_INPUT: { tone: "bg-warning text-background", icon: <MessageSquare className="h-3 w-3" />, label: "Needs Input" },
  PAUSED: { tone: "bg-warning text-background", icon: <Clock className="h-3 w-3" />, label: "Paused" },
  PARTIAL: { tone: "bg-warning text-background", icon: <AlertTriangle className="h-3 w-3" />, label: "Partial" },
  FAILED: { tone: "bg-destructive text-destructive-foreground", icon: <XCircle className="h-3 w-3" />, label: "Failed" },
  COMPLETED: { tone: "bg-success text-background", icon: <CheckCircle2 className="h-3 w-3" />, label: "Completed" },
  CANCELLED: { tone: "bg-muted text-muted-foreground", icon: <XCircle className="h-3 w-3" />, label: "Cancelled" },
};

const BANNER: Partial<Record<JobStatus, { text: string; tone: string }>> = {
  PARTIAL: { text: "Budget / tools / sources were insufficient — results are incomplete.", tone: "border-warning bg-warning/10" },
  FAILED: { text: "Research errored. See the Events tab for details, then retry.", tone: "border-destructive bg-destructive/10" },
  NEEDS_INPUT: { text: "A clarifying question needs your answer to continue.", tone: "border-primary bg-primary/10" },
};

const NEXT_STEP: Record<JobStatus, { text: string; tab?: string; icon: string }> = {
  CREATED: { text: "Press Start research — GoalSift derives conditions, searches real resources, and proposes paths.", icon: "play" },
  RESEARCHING: { text: "Researching now. Open the Events tab to watch live activity.", tab: "events", icon: "spin" },
  NEEDS_INPUT: { text: "Answer the question below to unblock the research.", icon: "ask" },
  COMPLETED: { text: "Review the Proposal first, then trace evidence in Match. Export to share.", tab: "proposal", icon: "done" },
  PARTIAL: { text: "Review what was found, then Resume after resolving the limit or service error.", icon: "warn" },
  PAUSED: { text: "Paused. Press Resume to continue the research.", icon: "pause" },
  FAILED: { text: "Something went wrong. Open the Events tab for the error, then Resume.", tab: "events", icon: "warn" },
  CANCELLED: { text: "Cancelled. Create a new job from the Jobs list to continue.", icon: "stop" },
};

const ASSESS_TONE: Record<string, string> = {
  SUPPORTED: "bg-success text-background",
  VERIFIED: "bg-success text-background",
  UNKNOWN: "bg-muted text-muted-foreground",
  PARTIAL: "bg-warning text-background",
  NOT_SATISFIED: "bg-destructive text-destructive-foreground",
  CONFLICTED: "bg-destructive text-destructive-foreground",
};

const TAB_ICONS: Record<string, React.ReactNode> = {
  proposal: <Sparkles className="h-3.5 w-3.5" />,
  conditions: <Target className="h-3.5 w-3.5" />,
  resources: <Package className="h-3.5 w-3.5" />,
  match: <Layers className="h-3.5 w-3.5" />,
  events: <Clock className="h-3.5 w-3.5" />,
};

/**
 * Split a long block of text into readable paragraphs.
 * Detects natural break points: double newlines, dash-prefixed lines,
 * numbered lists, and long sentences ending with 。or .
 */
function splitIntoParagraphs(text: string): string[] {
  if (!text) return [];

  // First split on explicit double newlines
  const doubleNewlineParts = text.split(/\n\s*\n/);
  if (doubleNewlineParts.length > 1) {
    return doubleNewlineParts.map((p) => p.trim()).filter(Boolean);
  }

  // Split on dash-prefixed lines (common in Chinese/English mixed text)
  // Handle both \n- and " - " (space-dash-space) patterns
  const dashParts = text.split(/\n\s*[-–—]\s*|\s[-–—]\s+/);
  if (dashParts.length > 1 && dashParts.length <= 15) {
    return dashParts.map((p) => p.trim()).filter(Boolean);
  }

  // Split on numbered items like "1." or "- "
  const numberedParts = text.split(/\n\s*(?:\d+[.、]\s*|[-•]\s+)/);
  if (numberedParts.length > 1 && numberedParts.length <= 15) {
    return numberedParts.map((p) => p.trim()).filter(Boolean);
  }

  // For single-block text, split on sentence-ending punctuation followed by space
  // but only if the text is very long (> 200 chars)
  if (text.length > 200) {
    const sentences = text.split(/(?<=[。！？.!?])\s+/);
    // Group sentences into paragraphs of ~100-150 chars (shorter for better readability)
    const paragraphs: string[] = [];
    let current = "";
    for (const s of sentences) {
      if (current.length + s.length > 150 && current.length > 60) {
        paragraphs.push(current.trim());
        current = s;
      } else {
        current += (current ? " " : "") + s;
      }
    }
    if (current.trim()) paragraphs.push(current.trim());
    if (paragraphs.length > 1) return paragraphs;
  }

  return [text.trim()];
}

/**
 * Detect if text has a list structure (multiple items separated by - or •)
 * and return the items, or null if it's just regular text.
 */
function detectListStructure(text: string): string[] | null {
  // Try splitting on " - " pattern (space-dash-space)
  const dashItems = text.split(/\s[-–—]\s+/);
  if (dashItems.length >= 3 && dashItems.length <= 20) {
    const trimmed = dashItems.map((p) => p.trim()).filter(Boolean);
    if (trimmed.length >= 3) return trimmed;
  }

  // Try splitting on newline-dash pattern
  const newlineDashItems = text.split(/\n\s*[-–—]\s*/);
  if (newlineDashItems.length >= 3 && newlineDashItems.length <= 20) {
    const trimmed = newlineDashItems.map((p) => p.trim()).filter(Boolean);
    if (trimmed.length >= 3) return trimmed;
  }

  return null;
}

/** Highlight key terms in text (assessment statuses, important keywords) */
function highlightText(text: string): React.ReactNode {
  const keywords = [
    "NOT_SATISFIED", "SUPPORTED", "UNKNOWN", "PARTIAL", "VERIFIED", "CONFLICTED",
    "六字段", "Idea2Context", "Agent Context", "Product Brief", "Feature Specification",
  ];
  const pattern = new RegExp(`(${keywords.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "g");
  const parts = text.split(pattern);
  return parts.map((part, i) => {
    if (keywords.includes(part)) {
      const tone = part === "NOT_SATISFIED" || part === "CONFLICTED"
        ? "text-destructive font-semibold"
        : part === "SUPPORTED" || part === "VERIFIED"
          ? "text-success font-semibold"
          : part === "UNKNOWN"
            ? "text-muted-foreground font-semibold"
            : "text-primary font-semibold";
      return <span key={i} className={tone}>{part}</span>;
    }
    return <span key={i}>{part}</span>;
  });
}

interface WorkspaceProps {
  jobId: string;
  onBack: () => void;
}

export function Workspace({ jobId, onBack }: WorkspaceProps) {
  const [liveJob, setJob] = useState<JobResult | null>(null);
  const [historyJob, setHistoryJob] = useState<JobResult | null>(null);
  const job = historyJob ?? liveJob;
  const [revisions, setRevisions] = useState<RevisionItem[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [pausePending, setPausePending] = useState(false);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
  const [selectedTab, setTab] = useState("proposal");
  const [tabTouched, setTabTouched] = useState(false);
  const tab = tabTouched ? selectedTab : (job ? NEXT_STEP[job.status].tab ?? "proposal" : "proposal");
  const [selA, setSelA] = useState<string | null>(null);
  const cursorRef = useRef(0);

  const load = useCallback(async () => {
    try {
      const [result, saved] = await Promise.all([getJob(jobId), listRevisions(jobId)]);
      setJob(result); setRevisions(saved); setLoadError(null);
      if (result.status !== "RESEARCHING") setPausePending(false);
    } catch (e) { setLoadError(String(e)); }
  }, [jobId]);

  const displayedStatus = job?.status;
  useEffect(() => stopTour, []);
  useEffect(() => {
    if (displayedStatus && !tourSeen()) {
      const t = setTimeout(() => runWorkspaceTour(displayedStatus), 400);
      return () => clearTimeout(t);
    }
  }, [displayedStatus, jobId]);

  const onTabChange = (v: string) => { setTabTouched(true); setTab(v); };

  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  useEffect(() => {
    const stop = subscribeEvents(jobId, (ev) => {
      if (ev.cursor && ev.cursor <= cursorRef.current) return;
      cursorRef.current = ev.cursor ?? cursorRef.current;
      setEvents((prev) => [...prev, ev]);
      load();
    }, () => load(), cursorRef.current);
    // Polling keeps the state usable even when SSE drops or a proxy buffers events.
    const timer = setInterval(load, 2500);
    return () => { stop(); clearInterval(timer); };
  }, [jobId, liveJob?.status, liveJob?.revision, load]);

  const perform = async (fn: () => Promise<void>) => {
    setActionBusy(true);
    try { await fn(); await load(); } catch (e) { toast.error(String(e)); }
    finally { setActionBusy(false); }
  };
  const start = () => perform(() => startJob(jobId));
  const cancel = () => perform(() => cancelJob(jobId));
  const pause = () => perform(async () => { await pauseJob(jobId); setPausePending(true); });
  const submitInput = async () => {
    if (!inputText.trim()) return;
    setSending(true);
    try {
      await sendInput(jobId, inputText);
      setInputText("");
      toast.success(job?.status === "COMPLETED" ? "Refine submitted — new revision" : "Answer submitted — resuming");
      await load();
    } catch (e) { toast.error("Submit failed", { description: String(e) }); }
    finally { setSending(false); }
  };

  const running = liveJob?.status === "RESEARCHING";
  const showInput = !historyJob && (job?.status === "NEEDS_INPUT" || job?.status === "COMPLETED");
  const lastUsage = job?.budget_usage ? { usage: job.budget_usage } : null;

  const byId = useMemo(() => {
    const cond = new Map<string, Condition>();
    const res = new Map<string, ResourceItem>();
    const assess = new Map<string, AssessmentItem>();
    (job?.conditions || []).forEach((c) => cond.set(c.id, c));
    (job?.resources || []).forEach((r) => res.set(r.id, r));
    (job?.assessments || []).forEach((a) => assess.set(a.id, a));
    return { cond, res, assess };
  }, [job]);

  if (!job && loadError) return <div role="alert" className="p-6 text-destructive">{loadError}<Button variant="outline" onClick={load} className="ml-3">重试</Button></div>;
  if (!job) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 px-5 py-8">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const statusCfg = STATUS_CONFIG[job.status];
  const banner = BANNER[job.status];

  return (
    <div className="mx-auto max-w-4xl px-5 py-6">
      {/* Topbar */}
      <div className="animate-fade-in mb-5">
        <div className="mb-3 flex items-center gap-2 text-sm text-muted-foreground">
          <button onClick={onBack} className="flex items-center gap-1 transition-colors hover:text-foreground">
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Jobs</span>
          </button>
          <ChevronRight className="h-3 w-3 text-muted-foreground/50" />
          <span className="truncate font-medium text-foreground">{job.original_request.slice(0, 60)}{job.original_request.length > 60 ? "…" : ""}</span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Badge className={cn("gap-1.5", statusCfg.tone)} data-tour="ws-status">
            {statusCfg.icon}
            {statusCfg.label}
          </Badge>
          <span className="text-xs text-muted-foreground">Revision {job.revision}</span>
          {revisions.length > 0 && <select aria-label="研究修订" className="max-w-40 rounded border bg-background px-2 py-1 text-xs" value={historyJob?.revision ?? "current"}
            onChange={async (e) => {
              if (e.target.value === "current") { setHistoryJob(null); return; }
              try { setHistoryJob(await getRevision(jobId, Number(e.target.value))); }
              catch (error) { toast.error(String(error)); }
            }}>
            <option value="current">当前修订</option>
            {revisions.map((r) => <option key={r.revision} value={r.revision}>历史修订 {r.revision}</option>)}
          </select>}
          {historyJob && <Badge variant="outline">历史快照 · 只读</Badge>}

          <div className="ml-auto flex items-center gap-2" data-tour="ws-export">
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <a href={exportUrl(jobId, "markdown", historyJob?.revision)} download>
                <FileDown className="h-3.5 w-3.5" />Markdown
              </a>
            </Button>
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <a href={exportUrl(jobId, "json", historyJob?.revision)} download>
                <FileDown className="h-3.5 w-3.5" />JSON
              </a>
            </Button>
          </div>
        </div>
      </div>

      {loadError && <div role="alert" className="mb-4 text-sm text-destructive">连接中断：{loadError}，正在重试。</div>}
      {job.stopped_reason && <div role="alert" className="mb-4 rounded border border-warning p-3 text-sm">{job.stopped_reason}</div>}
      {!!job.delivery_notes?.length && <div className="mb-5 rounded border bg-card p-3 text-sm text-muted-foreground">{job.delivery_notes.map((note, i) => <p key={i} className="mb-2 last:mb-0">{note}</p>)}</div>}
      {/* State banner */}
      {banner && (
        <div className={cn(
          "animate-slide-down mb-5 flex items-start gap-3 rounded-lg border-l-4 px-4 py-3 text-sm",
          banner.tone,
        )}>
          {job.status === "NEEDS_INPUT" ? <MessageSquare className="mt-0.5 h-4 w-4 shrink-0" /> : <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />}
          <span className="text-muted-foreground">{banner.text}</span>
        </div>
      )}

      {/* Budget panel */}
      {lastUsage?.usage && (
        <div className="animate-fade-in mb-5 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border bg-card/50 px-4 py-2.5 text-xs">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            <span className="font-medium">Usage</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-muted-foreground">Actions: <b className="text-foreground">{String(lastUsage.usage.actions ?? "—")}</b></span>
            <span className="text-muted-foreground">Tools: <b className="text-foreground">{String(lastUsage.usage.tool_calls ?? "—")}</b></span>
            {lastUsage.usage.cost_usd == null && <span>费用未知</span>}
            {lastUsage.usage.input_tokens != null && <span>Tokens: {lastUsage.usage.input_tokens} / {lastUsage.usage.output_tokens ?? 0}</span>}
            {lastUsage.usage.cost_usd != null && <span className="text-muted-foreground">Cost: <b className="text-foreground">${lastUsage.usage.cost_usd}</b></span>}
            {!!lastUsage.usage.reserved_usd && <span>请求费用预留: ${lastUsage.usage.reserved_usd}</span>}
            {lastUsage.usage.elapsed_seconds != null && <span className="text-muted-foreground">Time: <b className="text-foreground">{lastUsage.usage.elapsed_seconds}s</b></span>}
            {lastUsage.usage.stopped_reason && <span className="text-destructive">{String(lastUsage.usage.stopped_reason)}</span>}
          </div>
        </div>
      )}

      {/* Goal card */}
      <Card className="animate-slide-up mb-5" data-tour="ws-goal">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Target className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="line-clamp-2 text-sm italic leading-relaxed">"{job.original_request}"</p>
              <Accordion type="single" collapsible>
                <AccordionItem value="goal-details" className="border-0">
                  <AccordionTrigger className="py-2 text-xs">目标详情、假设与待确认问题</AccordionTrigger>
                  <AccordionContent>
              {job.goal?.statement && <p className="mt-2 text-sm leading-relaxed">{job.goal.statement}</p>}
              {!!job.goal?.assumptions?.length && <div className="mt-3 text-xs text-warning">未确认假设：{job.goal.assumptions.map((a) => a.text).join("；")}</div>}
              {job.goal?.open_questions && job.goal.open_questions.length > 0 && (
                <div className="mt-3 rounded-lg border-l-4 border-primary bg-primary/5 p-3">
                  <div className="text-xs font-semibold text-primary">Needs clarification</div>
                  <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm text-muted-foreground">{job.goal.open_questions.map((q, i) => <li key={i}>{q}</li>)}</ul>
                </div>
              )}
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Action buttons */}
      <div className="animate-slide-up mb-5 flex flex-wrap gap-2" data-tour="ws-start">
        {!historyJob && <>
        {(job.status === "CREATED" || job.status === "PAUSED" || job.status === "FAILED" || job.status === "PARTIAL") && (
          <Button onClick={start} disabled={running || actionBusy} className="gap-2 shadow-sm">
            <Play className="h-4 w-4" />
            {job.status === "CREATED" ? "Start research" : "Resume"}
          </Button>
        )}
        {running && <Button variant="outline" onClick={pause} disabled={actionBusy || pausePending}>{pausePending ? "暂停中…" : "Pause"}</Button>}
        {job.status !== "COMPLETED" && job.status !== "CANCELLED" && <Button variant="destructive" onClick={cancel} disabled={actionBusy}>Cancel</Button>}
        </>}
        <Button variant="ghost" size="sm" onClick={() => runWorkspaceTour(job.status)} className="gap-1.5">
          <Compass className="h-4 w-4" /> Take a tour
        </Button>
      </div>

      {/* Input: NEEDS_INPUT */}
      {showInput && job.status === "NEEDS_INPUT" && (
        <Card className="animate-scale-in mb-5 border-primary/30" data-tour="ws-input">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <MessageSquare className="h-4 w-4 text-primary" />
              Answer the clarifying question
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            <Textarea
              placeholder="Answer the question above, or state the assumption to continue under…"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              rows={2}
              className="resize-none"
            />
            <Button onClick={submitInput} disabled={sending || !inputText.trim()} className="gap-2">
              {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Submit answer
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Refine accordion */}
      {showInput && job.status === "COMPLETED" && (
        <Accordion type="single" collapsible className="animate-scale-in mb-5" data-tour="ws-refine">
          <AccordionItem value="refine" className="rounded-xl border bg-card px-4">
            <AccordionTrigger className="hover:no-underline">
              <span className="flex items-center gap-2 text-sm font-medium">
                <Sparkles className="h-4 w-4 text-primary" /> Add a constraint (Refine)
              </span>
            </AccordionTrigger>
            <AccordionContent className="space-y-3 pt-2">
              <Textarea
                placeholder="Add a constraint, e.g. 只能使用允许商业使用的开源方案"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                rows={2}
                className="resize-none"
              />
              <Button onClick={submitInput} disabled={sending || !inputText.trim()} className="gap-2">
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Submit constraint
              </Button>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      )}

      {/* Tabbed workspace */}
      <Tabs value={tab} onValueChange={onTabChange} className="w-full animate-slide-up" data-tour="ws-tabs">
        <TabsList className="grid w-full grid-cols-5" data-tour="ws-tablist">
          {Object.entries(TAB_ICONS).map(([key, icon]) => (
            <TabsTrigger key={key} value={key} aria-label={key} className="gap-1.5 text-xs sm:text-sm">
              {icon}
              <span className="hidden sm:inline">{key.charAt(0).toUpperCase() + key.slice(1)}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="proposal" className="mt-5">
          {job.proposal ? <ProposalView p={job.proposal} onTrace={() => { setSelA(job.proposal?.assessment_ids?.[0] ?? null); onTabChange("match"); }} /> : (
            <EmptyTab label="No proposal yet" hint="Research still in progress or no credible path found." />
          )}
        </TabsContent>

        <TabsContent value="conditions" className="mt-5">
          <p className="mb-4 text-xs leading-relaxed text-muted-foreground">以下条件由研究推导。超出已确认目标的细节需先确认，可通过 Refine 调整。</p>
          {job.conditions.length ? (
            <div className="space-y-3">
              {job.conditions.map((c) => {
                const linkedAssessments = (job.assessments || []).filter((a) => a.condition_id === c.id);
                return (
                  <Card key={c.id} className="overflow-hidden">
                    <CardContent className="p-4">
                      <div className="flex flex-col items-start gap-3 sm:flex-row">
                        <div className="flex shrink-0 gap-1.5">
                          <Badge variant="outline" className={cn("text-[10px]", c.obligation === "REQUIRED" && "border-primary text-primary")}>{c.obligation}</Badge>
                          <Badge variant="outline" className="text-[10px]">{c.dimension}</Badge>
                        </div>
                        <p className="flex-1 text-sm leading-relaxed">{c.statement}</p>
                      </div>
                      <details className="mt-3 text-xs leading-relaxed text-muted-foreground">
                        <summary className="cursor-pointer">推导依据与验收方式</summary>
                        <p className="mt-2 break-words">依据：{c.origin || "未记录"}</p>
                        <p className="mt-2 break-words">验收：{c.verification_method || "待确认"}</p>
                      </details>
                      {linkedAssessments.length > 0 && (
                        <div className="mt-3 space-y-1.5 border-t pt-3">
                          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Assessments</div>
                          {linkedAssessments.map((a) => (
                            <button
                              key={a.id}
                              onClick={() => { setSelA(a.id); onTabChange("match"); }}
                              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors hover:bg-accent"
                            >
                              <Badge className={cn("shrink-0 text-[10px]", ASSESS_TONE[a.status] || "bg-muted")}>{a.status}</Badge>
                              <span className="line-clamp-2 flex-1 text-xs leading-relaxed text-muted-foreground">{a.explanation}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          ) : <EmptyTab label="No conditions derived yet" />}
        </TabsContent>

        <TabsContent value="resources" className="mt-5">
          {job.resources.length ? (
            <div className="grid gap-3">
              {job.resources.map((r) => (
                <Card key={r.id} className="transition-shadow hover:shadow-sm">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="truncate text-sm font-semibold">{r.name}</h4>
                          <a href={r.canonical_source} target="_blank" rel="noreferrer" className="text-primary transition-opacity hover:opacity-70">
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        </div>
                        <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{r.description}</p>
                        <div className="mt-2 flex items-center gap-2">
                          <Badge variant="outline" className="text-[10px]">{r.kind}</Badge>
                          <Badge variant="outline" className={cn("text-[10px]", r.license_claim === "UNKNOWN" ? "border-warning text-warning" : "")}>
                            {r.license_claim || "UNKNOWN"}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : <EmptyTab label="No resources discovered yet" />}
        </TabsContent>

        <TabsContent value="match" className="mt-5">
          {job.assessments.length ? (
            <MatchView
              assessments={job.assessments}
              byId={byId}
              evidence={job.evidence || []}
              selA={selA}
              setSelA={setSelA}
            />
          ) : <EmptyTab label="No assessments yet" hint="Start the research to generate traceable assessments." />}
        </TabsContent>

        <TabsContent value="events" className="mt-5">
          {events.length ? (
            <ScrollArea className="h-[60vh] rounded-xl border bg-card/30 p-4">
              <ol className="space-y-1">
                {events.map((e, i) => (
                  <li key={i} className="flex items-start gap-3 rounded-lg px-3 py-2 text-xs transition-colors hover:bg-accent/50">
                    <span className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono font-medium text-primary">{e.event_type}</span>
                        {e.revision && <span className="text-muted-foreground">r{e.revision}</span>}
                        {e.status && <Badge variant="outline" className="text-[10px]">{e.status}</Badge>}
                        {e.tool && <Badge variant="secondary" className="text-[10px]">{e.tool}</Badge>}
                      </div>
                      {e.error && <p className="mt-1 text-destructive">{e.error.slice(0, 140)}</p>}
                    </div>
                  </li>
                ))}
              </ol>
            </ScrollArea>
          ) : <EmptyTab label="No events yet" hint="Start the research to see live activity." />}
        </TabsContent>
      </Tabs>
    </div>
  );
}

/* ── Proposal View ─── */
function ProposalView({ p, onTrace }: { p: ProposalItem; onTrace: () => void }) {
  const valid = p.validity_status === "READY_FOR_REVIEW";
  const summaryParagraphs = useMemo(() => splitIntoParagraphs(p.summary), [p.summary]);
  const summaryListItems = useMemo(() => detectListStructure(p.summary), [p.summary]);

  return (
    <Card className="animate-scale-in">
      <CardHeader className="gap-3 border-b pb-4">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-base leading-snug">{p.title}</CardTitle>
          <Badge className={cn("shrink-0", valid ? "bg-success text-background" : "bg-muted text-muted-foreground")}>
            {p.validity_status.replace(/_/g, " ")}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6 p-5">
        {/* Summary — properly typeset */}
        <section>
          <SectionLabel icon={<Sparkles className="h-3.5 w-3.5" />}>Summary</SectionLabel>
          <div className="mt-3 max-w-none">
            {summaryListItems ? (
              // Render as a list with visual separation
              <ul className="space-y-3">
                {summaryListItems.map((item, i) => (
                  <li key={i} className="flex gap-2 text-[15px] leading-[1.75] text-foreground/90">
                    <span className="mt-2 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary/60" />
                    <span>{highlightText(item)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              // Render as paragraphs
              summaryParagraphs.map((para, i) => (
                <p key={i} className="mb-3 text-[15px] leading-[1.8] text-foreground/90 last:mb-0">
                  {highlightText(para)}
                </p>
              ))
            )}
          </div>
        </section>

        <Separator />

        {/* Why this + Costs */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border bg-muted/30 p-4">
            <SectionLabel icon={<Lightbulb className="h-3.5 w-3.5" />}>Why this</SectionLabel>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.recommendation_reason || "—"}</p>
          </div>
          <div className="rounded-xl border bg-muted/30 p-4">
            <SectionLabel icon={<DollarSign className="h-3.5 w-3.5" />}>Costs</SectionLabel>
            <p className="mt-2 font-mono text-xs leading-relaxed text-muted-foreground">
              {Object.keys(p.costs).length ? JSON.stringify(p.costs, null, 2) : "—"}
            </p>
          </div>
        </div>

        {!!p.integration_work?.length && <section><SectionLabel icon={<Layers className="h-3.5 w-3.5" />}>集成工作</SectionLabel><ul className="mt-2 list-disc space-y-2 pl-5 text-sm">{p.integration_work.map((item, i) => <li key={i}>{item}</li>)}</ul></section>}
        {!!p.new_work?.length && <section><SectionLabel icon={<Sparkles className="h-3.5 w-3.5" />}>补充工作</SectionLabel><ul className="mt-2 list-disc space-y-2 pl-5 text-sm">{p.new_work.map((item, i) => <li key={i}>{item}</li>)}</ul></section>}
        <Button variant="outline" onClick={onTrace}>查看条件匹配与来源证据</Button>
        {/* Risks */}
        {p.risks.length > 0 && (
          <>
            <Separator />
            <div>
              <SectionLabel icon={<AlertTriangle className="h-3.5 w-3.5" />}>Risks &amp; gaps</SectionLabel>
              <div className="mt-3 flex flex-wrap gap-2">
                {p.risks.map((r, i) => (
                  <span key={i} className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-1.5 text-xs text-muted-foreground">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Decision banner */}
        <div className={cn(
          "flex items-center gap-3 rounded-xl border-l-4 px-4 py-3 text-sm",
          valid ? "border-warning bg-warning/10" : "border-muted bg-muted/10",
        )}>
          <ShieldCheck className="h-4 w-4 shrink-0 text-muted-foreground" />
          {valid
            ? "For your review only. Not executed — your decision is required."
            : `Validity: ${p.validity_status}`}
        </div>
      </CardContent>
    </Card>
  );
}

/* ─── Match View (split pane) ─── */
function MatchView({
  assessments, byId, evidence, selA, setSelA,
}: {
  assessments: AssessmentItem[];
  byId: { cond: Map<string, Condition>; res: Map<string, ResourceItem>; assess: Map<string, AssessmentItem> };
  evidence: { id: string; source_ref: string; excerpt_or_summary: string }[];
  selA: string | null;
  setSelA: (id: string) => void;
}) {
  const [narrow, setNarrow] = useState(() => window.innerWidth < 640);
  useEffect(() => {
    const media = window.matchMedia("(max-width: 639px)");
    const update = () => setNarrow(media.matches);
    media.addEventListener("change", update); update();
    return () => media.removeEventListener("change", update);
  }, []);
  const sel = assessments.find((a) => a.id === selA) ?? assessments[0];
  const cond = byId.cond.get(sel.condition_id);
  const resources = (sel.resource_ids || []).map((rid) => byId.res.get(rid)).filter(Boolean) as ResourceItem[];
  const linkedEvidence = evidence.filter((e) => (sel.evidence_ids || []).includes(e.id));

  return (
    <div className="h-[68vh] rounded-xl border bg-card/30">
      <Group orientation={narrow ? "vertical" : "horizontal"} id="goalsift-match-split">
        {/* Master: assessment list */}
        <Panel defaultSize="38" minSize="22">
          <div className="flex h-full min-w-0 flex-col">
            <div className="flex items-center gap-2 border-b px-4 py-3">
              <Layers className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Assessments · {assessments.length}
              </span>
            </div>
            <ScrollArea className="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]>div]:!block">
              <div className="p-2">
                {assessments.map((a) => {
                  const c = byId.cond.get(a.condition_id);
                  const active = a.id === sel.id;
                  return (
                    <button
                      key={a.id}
                      onClick={() => setSelA(a.id)}
                      className={cn(
                        "mb-1 flex w-full items-start gap-2 rounded-lg px-3 py-2.5 text-left transition-all",
                        active ? "bg-primary/10 ring-1 ring-primary/30" : "hover:bg-accent",
                      )}
                    >
                      <Badge className={cn("mt-0.5 shrink-0 text-[10px]", ASSESS_TONE[a.status] || "bg-muted")}>{a.status}</Badge>
                      <span className="min-w-0 text-xs leading-snug">
                        <span className="block truncate text-[10px] text-muted-foreground">{(a.resource_ids ?? []).map((rid) => byId.res.get(rid)?.name ?? rid).join(" · ")}</span>
                        <span className="line-clamp-2">{c ? c.statement : "condition"}</span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </ScrollArea>
          </div>
        </Panel>
        <Separator className={cn(narrow ? "h-1.5 w-full" : "w-1.5", "bg-border transition-colors hover:bg-primary/40")} />
        {/* Detail: trace chain */}
        <Panel minSize="35">
          <ScrollArea className="h-full">
            <div className="min-w-0 space-y-5 p-5 [overflow-wrap:anywhere]">
              {/* Breadcrumb */}
              <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                <Layers className="h-3 w-3" />
                <span>Proposal</span><span className="text-muted-foreground/50">→</span>
                <span className="font-medium text-foreground">Assessment</span><span className="text-muted-foreground/50">→</span>
                <span>Condition</span><span className="text-muted-foreground/50">→</span>
                <span>Resource</span><span className="text-muted-foreground/50">→</span>
                <span>Evidence</span>
              </div>

              {/* Assessment explanation — typeset */}
              <div>
                <div className="flex items-center gap-2">
                  <Badge className={cn(ASSESS_TONE[sel.status] || "bg-muted")}>{sel.status}</Badge>
                  <SectionLabel icon={<Lightbulb className="h-3.5 w-3.5" />}>Assessment</SectionLabel>
                </div>
                <div className="mt-2">
                  {(() => {
                    const listItems = detectListStructure(sel.explanation);
                    if (listItems) {
                      return (
                        <ul className="space-y-2">
                          {listItems.map((item, i) => (
                            <li key={i} className="flex gap-2 text-sm leading-[1.75] text-muted-foreground">
                              <span className="mt-2 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary/60" />
                              <span>{highlightText(item)}</span>
                            </li>
                          ))}
                        </ul>
                      );
                    }
                    return splitIntoParagraphs(sel.explanation).map((para, i) => (
                      <p key={i} className="mb-2 text-sm leading-[1.75] text-muted-foreground last:mb-0">
                        {highlightText(para)}
                      </p>
                    ));
                  })()}
                </div>
              </div>

              {/* Gaps */}
              {sel.gaps.length > 0 && (
                <div>
                  <SectionLabel icon={<AlertTriangle className="h-3.5 w-3.5" />}>Gaps</SectionLabel>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {sel.gaps.map((g, gi) => (
                      <span key={gi} className="rounded-lg border border-warning/30 bg-warning/5 px-3 py-1.5 text-xs text-muted-foreground">{g}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Condition */}
              {cond && (
                <div className="rounded-xl border bg-muted/30 p-4">
                  <SectionLabel icon={<Target className="h-3.5 w-3.5" />}>Condition</SectionLabel>
                  <div className="mt-2 flex items-center gap-2">
                    <Badge variant="outline" className={cn("text-[10px]", cond.obligation === "REQUIRED" && "border-primary text-primary")}>{cond.obligation}</Badge>
                    <Badge variant="outline" className="text-[10px]">{cond.dimension}</Badge>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed">{cond.statement}</p>
                </div>
              )}

              {/* Resources */}
              {resources.length > 0 && (
                <div>
                  <SectionLabel icon={<Package className="h-3.5 w-3.5" />}>Resources</SectionLabel>
                  <div className="mt-2 space-y-2">
                    {resources.map((r) => (
                      <div key={r.id} className="flex flex-wrap items-center gap-3 rounded-lg border bg-muted/30 px-3 py-2.5">
                        <a href={r.canonical_source} target="_blank" rel="noreferrer" className="inline-flex min-w-0 items-center gap-1.5 break-all text-sm text-primary hover:underline">
                          {r.name} <ExternalLink className="h-3 w-3" />
                        </a>
                        <Badge variant="outline" className={cn("ml-auto shrink-0 text-[10px]", r.license_claim === "UNKNOWN" ? "border-warning text-warning" : "")}>
                          {r.license_claim || "UNKNOWN"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Evidence */}
              {linkedEvidence.length > 0 ? (
                <div>
                  <SectionLabel icon={<FlaskRound className="h-3.5 w-3.5" />}>Evidence</SectionLabel>
                  <div className="mt-2 space-y-3">
                    {linkedEvidence.map((e) => (
                      <blockquote key={e.id} className="rounded-lg border-l-4 border-primary/30 bg-muted/30 py-3 pl-4 pr-3">
                        <a href={e.source_ref} target="_blank" rel="noreferrer" className="font-mono text-xs text-primary hover:underline break-all">{e.source_ref}</a>
                        <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{e.excerpt_or_summary.slice(0, 200)}</p>
                      </blockquote>
                    ))}
                  </div>
                </div>
              ) : <div className="text-xs text-muted-foreground">No evidence linked.</div>}
            </div>
          </ScrollArea>
        </Panel>
      </Group>
    </div>
  );
}

/* ─── Shared helpers ─── */
function SectionLabel({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
      {icon}{children}
    </div>
  );
}

function EmptyTab({ label, hint }: { label: string; hint?: string }) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-muted/50">
          <Layers className="h-5 w-5 text-muted-foreground" />
        </div>
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}
