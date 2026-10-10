import { useEffect, useState } from "react";
import { createJob, startJob, listJobs, type JobListItem, type JobStatus } from "./api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowRight, Compass, FileText, Loader2, Search, Sparkles, Clock, AlertCircle, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { runHomeTour } from "./tour";

const STATUS_CONFIG: Record<JobStatus, { tone: string; icon: React.ReactNode; label: string }> = {
  CREATED: { tone: "bg-muted text-muted-foreground", icon: <Clock className="h-3 w-3" />, label: "Created" },
  RESEARCHING: { tone: "bg-primary text-primary-foreground", icon: <Loader2 className="h-3 w-3 animate-spin" />, label: "Researching" },
  NEEDS_INPUT: { tone: "bg-warning text-background", icon: <AlertCircle className="h-3 w-3" />, label: "Needs Input" },
  PAUSED: { tone: "bg-warning text-background", icon: <Clock className="h-3 w-3" />, label: "Paused" },
  PARTIAL: { tone: "bg-warning text-background", icon: <AlertCircle className="h-3 w-3" />, label: "Partial" },
  FAILED: { tone: "bg-destructive text-destructive-foreground", icon: <XCircle className="h-3 w-3" />, label: "Failed" },
  COMPLETED: { tone: "bg-success text-background", icon: <CheckCircle2 className="h-3 w-3" />, label: "Completed" },
  CANCELLED: { tone: "bg-muted text-muted-foreground", icon: <XCircle className="h-3 w-3" />, label: "Cancelled" },
};

const EXAMPLES = [
  "我要一个像成熟商业产品一样好看的 Agent 管理网页，接入我现在运行的多个 Agent。",
  "制作一个成熟开源的 3D 游戏 Boss 战系统，包含 boss 动画、战斗场景和攻击/受击逻辑。",
  "做一个很好的产品",
];

const FLOW_STEPS = [
  { icon: <Sparkles className="h-5 w-5" />, label: "Describe a goal", desc: "One sentence is enough", color: "from-blue-500/20 to-blue-500/5" },
  { icon: <Search className="h-5 w-5" />, label: "Live research", desc: "Real resources + evidence", color: "from-primary/20 to-primary/5" },
  { icon: <FileText className="h-5 w-5" />, label: "Choose a path", desc: "Evidence-backed proposals", color: "from-success/20 to-success/5" },
];

const RANK: Record<JobStatus, number> = {
  NEEDS_INPUT: 0, PARTIAL: 1, FAILED: 1, RESEARCHING: 2, CREATED: 3, PAUSED: 4, COMPLETED: 5, CANCELLED: 6,
};
const attentionRank = (s: JobStatus) => RANK[s] ?? 9;

interface HomeProps {
  onOpen: (id: string) => void;
}

export function Home({ onOpen }: HomeProps) {
  const [text, setText] = useState("");
  const [jobs, setJobs] = useState<JobListItem[] | null>(null);
  const [busy, setBusy] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const refresh = () => listJobs().then((items) => { setJobs(items); setError(null); }).catch((e) => { setJobs([]); setError(String(e)); });
  useEffect(() => { refresh(); }, []);

  const submit = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const r = await createJob(text);
      try {
        await startJob(r.id);
      } catch (e) {
        toast.error("Job saved; research could not start", { description: String(e) });
        await refresh();
        onOpen(r.id);
        return;
      }
      toast.success("Research job created", { description: "Opening the workspace…" });
      setText("");
      await refresh();
      onOpen(r.id);
    } catch (e) {
      toast.error("Could not create job", { description: String(e) });
    } finally {
      setBusy(false);
    }
  };

  const hasAttentionJobs = jobs?.some((j) => j.status === "NEEDS_INPUT" || j.status === "PARTIAL" || j.status === "FAILED");

  return (
    <div className="mx-auto max-w-3xl px-5 py-8 md:py-12">
      {error && <div role="alert" className="mb-5 rounded-lg border border-destructive p-4 text-sm text-destructive">无法连接后端：{error}<Button variant="outline" size="sm" className="ml-3" onClick={refresh}>重试</Button></div>}
      {/* Hero section */}
      <div className="animate-slide-up mb-8">
        <div className="mb-3 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary/70 text-primary-foreground">
            <Sparkles className="h-4 w-4" />
          </div>
          <span className="text-xs font-medium uppercase tracking-wider text-primary">AI-Powered Research</span>
        </div>
        <h1 className="mb-3 text-3xl font-bold tracking-tight md:text-4xl">
          What outcome do you want?
        </h1>
        <p className="max-w-2xl text-base leading-relaxed text-muted-foreground">
          GoalSift searches for <b className="text-foreground">real, existing</b> resources,
          checks evidence-backed suitability, and proposes paths <b className="text-foreground">for you to choose</b>.
          Research does not execute proposed plans.
        </p>
      </div>

      {/* Flow visualization */}
      <div className="animate-slide-up stagger-1 mb-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {FLOW_STEPS.map((step, i) => (
          <div key={i} className="relative">
            <div className={cn(
              "flex items-center gap-3 rounded-xl border bg-gradient-to-br p-4 transition-all hover:shadow-sm",
              step.color,
            )}>
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-background/80 text-foreground shadow-sm">
                {step.icon}
              </div>
              <div className="min-w-0">
                <div className="text-sm font-semibold">{step.label}</div>
                <div className="text-xs text-muted-foreground">{step.desc}</div>
              </div>
            </div>
            {i < FLOW_STEPS.length - 1 && (
              <div className="absolute right-0 top-1/2 hidden h-px w-3 -translate-y-1/2 translate-x-full bg-border sm:block" />
            )}
          </div>
        ))}
      </div>

      {/* Goal input card */}
      <Card className="animate-slide-up stagger-2 mb-8 border-primary/20 shadow-sm" data-tour="home-goal">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="h-4 w-4 text-primary" /> Describe your goal
          </CardTitle>
          <CardDescription>Start here. One sentence is enough — you can refine or add constraints later.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="e.g. 我要一个像成熟商业产品一样好看的 Agent 管理网页，接入我现在运行的多个 Agent。"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={3}
            className="resize-none"
            autoFocus
          />
          <div data-tour="home-examples">
            <div className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Try an example</div>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => setText(ex)}
                  className="rounded-full border px-3 py-1.5 text-xs text-muted-foreground transition-all hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
                >
                  {ex.length > 30 ? ex.slice(0, 30) + "…" : ex}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3" data-tour="home-create">
            <Button onClick={submit} disabled={busy || !text.trim()} size="lg" className="shadow-sm">
              {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ArrowRight className="mr-2 h-4 w-4" />}
              Create &amp; start research
            </Button>
            <span className="text-xs text-muted-foreground">Progress is saved while research runs</span>
          </div>
        </CardContent>
      </Card>

      {/* Jobs section */}
      <div className="animate-slide-up stagger-3" data-tour="home-jobs">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-tight">Your research jobs</h2>
            <p className="text-xs text-muted-foreground">Click any job to open its workspace</p>
          </div>
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" onClick={runHomeTour}>
              <Compass className="mr-1 h-4 w-4" />Tour
            </Button>
            <Button variant="ghost" size="sm" onClick={refresh}>Refresh</Button>
          </div>
        </div>

        {/* Attention banner */}
        {hasAttentionJobs && (
          <div className="mb-4 flex items-center gap-3 rounded-lg border-l-4 border-warning bg-warning/10 px-4 py-3 text-sm">
            <AlertCircle className="h-4 w-4 shrink-0 text-warning" />
            <span className="text-muted-foreground">You have a job that needs your attention — answer its question or retry to continue.</span>
          </div>
        )}

        {jobs === null ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}
          </div>
        ) : jobs.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
                <ArrowRight className="h-5 w-5" />
              </div>
              <p className="text-sm font-medium">No jobs yet</p>
              <p className="mt-1 text-xs text-muted-foreground">Describe a goal above — GoalSift will do the research for you.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {[...jobs].sort((a, b) => attentionRank(a.status) - attentionRank(b.status)).map((j, i) => {
              const config = STATUS_CONFIG[j.status];
              const attention = j.status === "NEEDS_INPUT" || j.status === "PARTIAL" || j.status === "FAILED";
              return (
                <button
                  key={j.id}
                  onClick={() => onOpen(j.id)}
                  className={cn(
                    "animate-slide-up group flex w-full items-center gap-4 rounded-xl border bg-card px-4 py-4 text-left transition-all hover:shadow-md",
                    attention ? "border-warning/50 border-l-4" : "hover:border-primary/30",
                  )}
                  style={{ animationDelay: `${i * 0.05}s` }}
                >
                  <Badge className={cn("shrink-0 gap-1", config.tone)}>
                    {config.icon}
                    <span className="hidden sm:inline">{config.label}</span>
                  </Badge>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{j.original_request}</div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                      <span>
                        {j.status === "COMPLETED" ? "View proposals"
                          : j.status === "NEEDS_INPUT" ? "Answer question"
                          : j.status === "RESEARCHING" ? "Researching…"
                          : j.status === "PARTIAL" ? "Partial results"
                          : j.status === "FAILED" ? "See error"
                          : "Open"}
                      </span>
                      <span className="text-muted-foreground/50">·</span>
                      <span>rev {j.revision}</span>
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground transition-all group-hover:translate-x-1 group-hover:text-primary" />
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
