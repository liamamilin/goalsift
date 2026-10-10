import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  cancelJob, exportUrl, getJob, sendInput, startJob, subscribeEvents, pauseJob, listRevisions, getRevision, type RevisionItem,
  type AssessmentItem, type Condition, type EventItem, type JobResult, type JobStatus,
  type ProposalItem, type ResourceItem,
} from "./api";
import { GoalReviewView } from "./GoalReview";
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
  ShieldCheck, Sparkles, Target, XCircle, ChevronRight, ChevronDown,
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
  const [contextOpen, setContextOpen] = useState(false);
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
      const t = setTimeout(() => {
        if (displayedStatus === "CREATED" || displayedStatus === "COMPLETED") setContextOpen(true);
        requestAnimationFrame(() => runWorkspaceTour(displayedStatus, { onDestroyed: () => setContextOpen(false) }));
      }, 400);
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
      setContextOpen(false);
      toast.success(job?.status === "COMPLETED" ? "Refine submitted — new revision" : "Answer submitted — resuming");
      await load();
    } catch (e) { toast.error("Submit failed", { description: String(e) }); }
    finally { setSending(false); }
  };

  const running = liveJob?.status === "RESEARCHING";
  const showInput = !historyJob && (job?.status === "NEEDS_INPUT" || job?.status === "COMPLETED");
  const usage = job?.budget_usage;

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
    <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6 sm:py-6">
      <header className="mb-5 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
            <button onClick={onBack} className="flex shrink-0 items-center gap-1 hover:text-foreground">
              <ArrowLeft className="h-3.5 w-3.5" />Jobs
            </button>
            <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground/50" />
            <h1 className="truncate font-semibold text-foreground">Research workspace</h1>
          </div>
          <Button variant="ghost" size="sm" className="shrink-0 gap-1.5 text-muted-foreground" onClick={() => {
            const wasOpen = contextOpen;
            if (job.status === "CREATED" || (job.status === "COMPLETED" && !historyJob)) setContextOpen(true);
            requestAnimationFrame(() => runWorkspaceTour(job.status, {
              readOnly: !!historyJob,
              onDestroyed: () => setContextOpen(wasOpen),
            }));
          }}>
            <Compass className="h-3.5 w-3.5" />Tour
          </Button>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge className={cn("gap-1.5", statusCfg.tone)} data-tour="ws-status">
              {statusCfg.icon}{statusCfg.label}
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
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {!historyJob && <div className="flex gap-2" data-tour="ws-start">
              {(job.status === "CREATED" || job.status === "PAUSED" || job.status === "FAILED" || job.status === "PARTIAL") && (
                <Button size="sm" onClick={start} disabled={running || actionBusy} className="gap-1.5">
                  <Play className="h-3.5 w-3.5" />{job.status === "CREATED" ? "Start research" : "Resume"}
                </Button>
              )}
              {running && <Button size="sm" variant="outline" onClick={pause} disabled={actionBusy || pausePending}>{pausePending ? "暂停中…" : "Pause"}</Button>}
              {job.status !== "COMPLETED" && job.status !== "CANCELLED" && <Button size="sm" variant="destructive" onClick={cancel} disabled={actionBusy}>Cancel</Button>}
            </div>}
            <div className="flex gap-2" data-tour="ws-export">
              <Button variant="outline" size="sm" asChild className="gap-1.5">
                <a href={exportUrl(jobId, "markdown", historyJob?.revision)} download><FileDown className="h-3.5 w-3.5" />Markdown</a>
              </Button>
              <Button variant="outline" size="sm" asChild className="gap-1.5">
                <a href={exportUrl(jobId, "json", historyJob?.revision)} download><FileDown className="h-3.5 w-3.5" />JSON</a>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {loadError && <div role="alert" className="mb-4 text-sm text-destructive">连接中断：{loadError}，正在重试。</div>}
      {job.stopped_reason && <div role="alert" className="mb-4 rounded-lg border border-warning bg-warning/5 p-3 text-sm">{job.stopped_reason}</div>}
      {banner && (
        <div role="status" className={cn("mb-4 flex items-start gap-3 rounded-lg border-l-4 px-4 py-3 text-sm", banner.tone)}>
          {job.status === "NEEDS_INPUT" ? <MessageSquare className="mt-0.5 h-4 w-4 shrink-0" /> : <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />}
          <span>{banner.text}</span>
        </div>
      )}

          {showInput && job.status === "NEEDS_INPUT" && (
            <Card className="mb-4 gap-0 border-primary/30 py-0" data-tour="ws-input">
              <CardHeader className="p-4 pb-3">
                <CardTitle className="flex items-center gap-2 text-sm"><MessageSquare className="h-4 w-4 text-primary" />Answer the clarifying question</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 p-4 pt-0">
                {!!job.goal?.open_questions?.length && <ul className="list-disc space-y-2 pl-4 text-sm leading-relaxed">{job.goal.open_questions.map((q, i) => <li key={i}>{q}</li>)}</ul>}
                <Textarea placeholder="Answer the question above, or state the assumption to continue under…" value={inputText} onChange={(e) => setInputText(e.target.value)} rows={3} className="resize-none" />
                <Button onClick={submitInput} disabled={sending || !inputText.trim()} className="gap-2">{sending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}Submit answer</Button>
              </CardContent>
            </Card>
          )}

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_272px] xl:gap-5">
        <aside className="min-w-0 xl:col-start-2 xl:row-start-1" aria-label="研究背景与用量">
          <button className="flex w-full items-center justify-between gap-3 rounded-lg border bg-card px-3 py-2.5 text-xs xl:hidden" aria-expanded={contextOpen} aria-controls="research-context" onClick={() => setContextOpen(!contextOpen)}>
            <span className="flex items-center gap-2"><Target className="h-3.5 w-3.5 text-primary" />目标、研究范围与继续研究</span>
            <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", contextOpen && "rotate-180")} />
          </button>
          <div id="research-context" className={cn("space-y-4 xl:block", contextOpen ? "mt-3 block xl:mt-0" : "hidden")}>
            <Card className="gap-0 py-0" data-tour="ws-goal">
              <CardContent className="p-4">
                <SectionLabel icon={<Target className="h-3.5 w-3.5" />}>{job.goal?.purpose ? "目标理解" : "原始需求"}</SectionLabel>
                <p className="mt-2 line-clamp-3 text-sm leading-relaxed">{job.goal?.purpose || job.original_request}</p>
                <button className="mt-2 text-xs font-medium text-primary hover:underline" onClick={() => onTabChange('conditions')}>复核目标与条件 · {job.conditions.filter(c => c.provenance !== 'USER_CONFIRMED').length} 项待确认</button>
                <Accordion type="single" collapsible>
                  <AccordionItem value="original-request" className="border-0">
                    <AccordionTrigger className="py-2.5 text-xs">查看原始需求</AccordionTrigger>
                    <AccordionContent className="text-xs leading-relaxed text-muted-foreground">{job.original_request}</AccordionContent>
                  </AccordionItem>
                  <AccordionItem value="goal-details" className="border-0">
                    <AccordionTrigger className="py-2.5 text-xs">目标详情、假设与待确认问题</AccordionTrigger>
                    <AccordionContent className="space-y-3 text-xs leading-relaxed">
                      {job.goal?.statement && <p>{job.goal.statement}</p>}
                      {!!job.goal?.assumptions?.length && <div className="text-warning">未确认假设：{job.goal.assumptions.map((a) => a.text).join("；")}</div>}
                      {!!job.goal?.open_questions?.length && <ul className="list-disc space-y-2 pl-4 text-muted-foreground">{job.goal.open_questions.map((q, i) => <li key={i}>{q}</li>)}</ul>}
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              </CardContent>
            </Card>

            <Card className="gap-0 py-0">
              <CardContent className="p-4">
                <SectionLabel icon={<Layers className="h-3.5 w-3.5" />}>研究范围</SectionLabel>
                <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                  {[[job.conditions.length, "条件"], [job.resources.length, "资源"], [job.assessments.length, "评估"]].map(([value, label]) => (
                    <div key={label} className="rounded-lg bg-muted/40 py-2"><div className="text-lg font-semibold tabular-nums">{value}</div><div className="text-[11px] text-muted-foreground">{label}</div></div>
                  ))}
                </div>
                <p className="mt-3 text-xs leading-relaxed text-muted-foreground">来源支持不等于实测验证，研究完成不代表目标已实现。</p>
                {!!job.delivery_notes?.length && <details className="mt-3 border-t pt-3 text-xs leading-relaxed text-muted-foreground">
                  <summary className="cursor-pointer font-medium">研究边界说明</summary>
                  <div className="mt-2 space-y-2">{job.delivery_notes.map((note, i) => <p key={i}>{note}</p>)}</div>
                </details>}
              </CardContent>
            </Card>

            {usage && <Card className="gap-0 py-0">
              <CardContent className="p-4">
                <SectionLabel icon={<Clock className="h-3.5 w-3.5" />}>本轮研究用量</SectionLabel>
                <dl className="mt-3 space-y-2 text-xs">
                  <div className="flex justify-between gap-2"><dt className="text-muted-foreground">已记录费用</dt><dd className="font-medium tabular-nums">{usage.cost_usd == null ? "未知" : `$${usage.cost_usd}`}</dd></div>
                  {usage.elapsed_seconds != null && <div className="flex justify-between gap-2"><dt className="text-muted-foreground">运行时间</dt><dd className="tabular-nums">{usage.elapsed_seconds}s</dd></div>}
                  {!!usage.reserved_usd && <div className="flex justify-between gap-2"><dt className="text-muted-foreground">请求费用预留</dt><dd className="tabular-nums">${usage.reserved_usd}</dd></div>}
                </dl>
                {usage.cost_unknown && <p className="mt-2 text-xs leading-relaxed text-warning">部分请求费用未知，记录金额不是最终总额。</p>}
                <details className="mt-3 border-t pt-3 text-xs text-muted-foreground">
                  <summary className="cursor-pointer">操作与 Token 明细</summary>
                  <dl className="mt-2 space-y-2">
                    <div className="flex justify-between gap-2"><dt>Actions / Tools</dt><dd>{String(usage.actions ?? "—")} / {String(usage.tool_calls ?? "—")}</dd></div>
                    {usage.input_tokens != null && <div className="flex justify-between gap-2"><dt>输入 / 输出 Token</dt><dd>{usage.input_tokens} / {usage.output_tokens ?? 0}</dd></div>}
                  </dl>
                  {usage.stopped_reason && <p className="mt-2 break-words text-destructive">{String(usage.stopped_reason)}</p>}
                </details>
              </CardContent>
            </Card>}

            {showInput && job.status === "COMPLETED" && (
              <Accordion type="single" collapsible data-tour="ws-refine">
                <AccordionItem value="refine" className="rounded-xl border bg-card px-4">
                  <AccordionTrigger className="py-3.5 hover:no-underline">
                    <span className="flex items-center gap-2 text-sm font-medium"><Sparkles className="h-4 w-4 text-primary" />继续研究 · Refine</span>
                  </AccordionTrigger>
                  <AccordionContent className="space-y-3">
                    <p className="text-xs leading-relaxed text-muted-foreground">补充约束后会创建新修订，现有结果保留在历史中。</p>
                    <Textarea placeholder="Add a constraint, e.g. 只能使用允许商业使用的开源方案" value={inputText} onChange={(e) => setInputText(e.target.value)} rows={3} className="resize-none" />
                    <Button size="sm" onClick={submitInput} disabled={sending || !inputText.trim()} className="gap-2">
                      {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}Submit constraint
                    </Button>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            )}
          </div>
        </aside>

        <section className="min-w-0 xl:col-start-1 xl:row-start-1" aria-label="研究结果">
      {/* Tabbed workspace */}
      <Tabs value={tab} onValueChange={onTabChange} className="w-full animate-slide-up" data-tour="ws-tabs">
        <TabsList className="grid w-full grid-cols-5" data-tour="ws-tablist">
          {Object.entries(TAB_ICONS).map(([key, icon]) => (
            <TabsTrigger key={key} value={key} aria-label={key} className="gap-1 text-xs sm:gap-1.5 sm:text-sm">
              {icon}
              <span>{({ proposal: "方案", conditions: "条件", resources: "资源", match: "匹配", events: "事件" } as Record<string, string>)[key]}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="proposal" className="mt-4">
          {job.proposal ? <ProposalView key={job.proposal.id} p={job.proposal} conditions={job.conditions} onTrace={() => { setSelA(job.proposal?.assessment_ids?.[0] ?? null); onTabChange("match"); }} /> : (
            <EmptyTab label="No proposal yet" hint="Research still in progress or no credible path found." />
          )}
        </TabsContent>

        <TabsContent value="conditions" className="mt-4">
          <GoalReviewView key={`${job.id}:${job.revision}:${historyJob ? 'history' : 'current'}`} job={job} readOnly={!!historyJob} onSaved={load} onAssessment={(id) => { setSelA(id); onTabChange("match"); }} />
        </TabsContent>

        <TabsContent value="resources" className="mt-4 min-w-0 [overflow-wrap:anywhere]">
          {job.resources.length ? (
            <div className="grid min-w-0 grid-cols-1 gap-3">
              {job.resources.map((r) => (
                <Card key={r.id} className="min-w-0 gap-0 py-0 transition-shadow hover:shadow-sm">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="truncate text-sm font-semibold">{r.name}</h4>
                          <a href={r.canonical_source} target="_blank" rel="noreferrer" className="text-primary transition-opacity hover:opacity-70">
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        </div>
                        <ReadableText text={r.description} label="资源说明" className="mt-1.5 text-xs leading-relaxed text-muted-foreground" />
                        <div className="mt-2 flex items-center gap-2">
                          <Badge variant="outline" className="text-[10px]">{r.kind}</Badge>
                          <Badge variant="outline" className={cn("text-[10px]", r.license_claim === "UNKNOWN" ? "border-warning text-warning" : "")}>
                            {r.license_claim || "UNKNOWN"}
                          </Badge>
                        </div>
                        {job.source_reviews?.[r.id] && <details className="mt-3 border-t pt-3 text-xs">
                          <summary className="cursor-pointer text-muted-foreground">补充文档 · {job.source_reviews[r.id].documents.length} 份已读取</summary>
                          <p className="mt-2 leading-relaxed text-muted-foreground">记录实际读取的原文；能力、许可适用性与集成仍需逐项判断。</p>
                          <ul className="mt-2 space-y-2">{job.source_reviews[r.id].documents.map(d => <li key={d.url}><a href={d.url} target="_blank" rel="noreferrer" className="break-all text-primary hover:underline">{d.category} <ExternalLink className="inline h-3 w-3" /></a>{d.version && <span className="ml-2 font-mono text-[10px] text-muted-foreground">{d.version.slice(0, 12)}</span>}</li>)}</ul>
                          {job.source_reviews[r.id].notes.map((note, i) => <p key={i} className="mt-2 leading-relaxed text-warning">{note}</p>)}
                        </details>}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : <EmptyTab label="No resources discovered yet" />}
        </TabsContent>

        <TabsContent value="match" className="mt-4">
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

        <TabsContent value="events" className="mt-4">
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
        </section>
      </div>
    </div>
  );
}

/* ── Proposal View ─── */
function ProposalView({ p, conditions, onTrace }: { p: ProposalItem; conditions: Condition[]; onTrace: () => void }) {
  const valid = p.validity_status === "READY_FOR_REVIEW";
  const uncovered = conditions.filter((c) => p.uncovered_conditions?.includes(c.id));
  const costLabels: Record<string, string> = { estimate: "费用估计", basis: "估计依据", currency: "币种", amount: "金额" };

  return (
    <div className="space-y-4">
      <Card className="gap-0 overflow-hidden py-0">
        <CardHeader className="gap-3 border-b p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <SectionLabel icon={<Sparkles className="h-3.5 w-3.5 text-primary" />}>推荐方案</SectionLabel>
            <Badge className={cn("text-[10px]", valid ? "bg-success/15 text-success" : "bg-muted text-muted-foreground")}>
              {p.validity_status.replace(/_/g, " ")}
            </Badge>
          </div>
          <CardTitle className="text-lg leading-relaxed">{p.title}</CardTitle>
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground"><ShieldCheck className="h-3.5 w-3.5 shrink-0" />研究建议，待你选择；尚未执行。</p>
          {(p.condition_coverage || !!p.uncovered_conditions?.length) && <div className="flex flex-wrap gap-x-3 gap-y-1 rounded-lg bg-warning/5 px-3 py-2 text-xs leading-relaxed">
            {p.condition_coverage && <span className="text-muted-foreground">方案覆盖 <b className="text-foreground">{p.condition_coverage.length} / {conditions.length}</b> 项条件</span>}
            {!!p.uncovered_conditions?.length && <span className="text-warning">{p.uncovered_conditions.length} 项条件缺口待处理</span>}
          </div>}
        </CardHeader>
        <CardContent className="space-y-4 p-4 sm:p-5">
          <section>
            <SectionLabel icon={<FileDown className="h-3.5 w-3.5" />}>方案概述</SectionLabel>
            <ReadableText text={p.summary} label="完整方案概述" className="mt-2 text-sm leading-7 text-foreground/90" />
          </section>
          <section className="rounded-lg border border-primary/15 bg-primary/5 p-3.5">
            <SectionLabel icon={<Lightbulb className="h-3.5 w-3.5 text-primary" />}>推荐理由</SectionLabel>
            <ReadableText text={p.recommendation_reason || "未记录推荐理由"} label="完整推荐理由" className="mt-2 text-sm leading-relaxed text-muted-foreground" />
          </section>
          <div className="border-t pt-4">
            <Button variant="outline" size="sm" onClick={onTrace} className="gap-1.5"><Layers className="h-3.5 w-3.5" />查看匹配与来源证据<ChevronRight className="h-3.5 w-3.5" /></Button>
          </div>
        </CardContent>
      </Card>

      {(uncovered.length > 0 || p.risks.length > 0) && <Card className="gap-0 border-warning/25 py-0">
        <CardContent className="p-4 sm:p-5">
          <SectionLabel icon={<AlertTriangle className="h-3.5 w-3.5 text-warning" />}>决策前需要确认</SectionLabel>
          <p className="mt-2 text-xs leading-relaxed text-muted-foreground">这些缺口与风险仍需处理，不能视为已满足或已通过实测。</p>
          <Accordion type="multiple" defaultValue={["risks"]} className="mt-2">
            {uncovered.length > 0 && <AccordionItem value="uncovered">
              <AccordionTrigger className="py-3 text-sm">未覆盖的条件 · {uncovered.length}</AccordionTrigger>
              <AccordionContent><ul className="list-disc space-y-3 pl-4 text-sm leading-relaxed text-muted-foreground">{uncovered.map((c) => <li key={c.id}>{c.statement}</li>)}</ul></AccordionContent>
            </AccordionItem>}
            {p.risks.length > 0 && <AccordionItem value="risks" className="border-0">
              <AccordionTrigger className="py-3 text-sm">风险与限制 · {p.risks.length}</AccordionTrigger>
              <AccordionContent><ul className="list-disc space-y-3 pl-4 text-sm leading-relaxed text-muted-foreground">{p.risks.map((r, i) => <li key={i}>{highlightText(r)}</li>)}</ul></AccordionContent>
            </AccordionItem>}
          </Accordion>
        </CardContent>
      </Card>}

      {(!!p.integration_work?.length || !!p.new_work?.length) && <Card className="gap-0 py-0">
        <CardContent className="p-4 sm:p-5">
          <SectionLabel icon={<Layers className="h-3.5 w-3.5" />}>落地需要的工作</SectionLabel>
          <Accordion type="multiple" className="mt-2">
            {!!p.integration_work?.length && <AccordionItem value="integration">
              <AccordionTrigger className="py-3 text-sm">集成工作 · {p.integration_work.length}</AccordionTrigger>
              <AccordionContent><ul className="list-disc space-y-3 pl-4 text-sm leading-relaxed text-muted-foreground">{p.integration_work.map((item, i) => <li key={i}>{item}</li>)}</ul></AccordionContent>
            </AccordionItem>}
            {!!p.new_work?.length && <AccordionItem value="new-work" className="border-0">
              <AccordionTrigger className="py-3 text-sm">补充工作 · {p.new_work.length}</AccordionTrigger>
              <AccordionContent><ul className="list-disc space-y-3 pl-4 text-sm leading-relaxed text-muted-foreground">{p.new_work.map((item, i) => <li key={i}>{item}</li>)}</ul></AccordionContent>
            </AccordionItem>}
          </Accordion>
        </CardContent>
      </Card>}

      <Card className="gap-0 py-0">
        <CardContent className="p-4 sm:p-5">
          <SectionLabel icon={<DollarSign className="h-3.5 w-3.5" />}>方案实施成本</SectionLabel>
          <p className="mt-2 text-xs text-muted-foreground">下列为方案估计；本轮 AI 研究用量另列于背景区。</p>
          <dl className="mt-3 space-y-3 text-sm">
            {Object.keys(p.costs).length ? Object.entries(p.costs).map(([key, value]) => (
              <div key={key} className="grid gap-1 sm:grid-cols-[100px_minmax(0,1fr)]">
                <dt className="text-xs text-muted-foreground">{costLabels[key] ?? key}</dt>
                <dd className="break-words leading-relaxed">{value === "UNKNOWN" ? "未知，尚未核实" : typeof value === "string" || typeof value === "number" ? String(value) : JSON.stringify(value)}</dd>
              </div>
            )) : <p className="text-muted-foreground">暂无经核实的费用估计</p>}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}

function ReadableText({ text, label, className }: { text: string; label: string; className?: string }) {
  const [expanded, setExpanded] = useState(false);
  const paragraphs = useMemo(() => splitIntoParagraphs(text), [text]);
  const listItems = useMemo(() => detectListStructure(text), [text]);
  const long = text.length > 260;
  return (
    <div>
      <div className={cn(className, long && !expanded && "line-clamp-5")}>
        {listItems ? <ul className="list-disc space-y-2 pl-4">{listItems.map((item, i) => <li key={i}>{highlightText(item)}</li>)}</ul>
          : paragraphs.map((para, i) => <p key={i} className="mb-2 last:mb-0">{highlightText(para)}</p>)}
      </div>
      {long && <button onClick={() => setExpanded(!expanded)} aria-expanded={expanded} className="mt-2 flex items-center gap-1 text-xs font-medium text-primary hover:underline">
        {expanded ? "收起" : `展开${label}`}<ChevronDown className={cn("h-3 w-3 transition-transform", expanded && "rotate-180")} />
      </button>}
    </div>
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
