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
  { icon: <Sparkles className="h-3.5 w-3.5" />, label: "Describe a goal" },
  { icon: <Search className="h-3.5 w-3.5" />, label: "Live research" },
  { icon: <FileText className="h-3.5 w-3.5" />, label: "Choose a path" },
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
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 md:py-8">
      {error && <div role="alert" className="mb-5 rounded-lg border border-destructive p-4 text-sm text-destructive">无法连接后端：{error}<Button variant="outline" size="sm" className="ml-3" onClick={refresh}>重试</Button></div>}
      <header className="mb-6">
        <div className="mb-2 flex items-center gap-2 text-xs font-medium text-primary"><Sparkles className="h-4 w-4" />AI-Powered Research</div>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">What outcome do you want?</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">从目标出发，研究真实资源与来源证据，提出可供你选择的路径。</p>
      </header>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <section className="min-w-0" aria-label="创建研究">
          <Card className="gap-0 border-primary/20 py-0" data-tour="home-goal">
            <CardHeader className="gap-2 p-4 pb-3 sm:p-5 sm:pb-3">
              <CardTitle className="flex items-center gap-2 text-base"><Sparkles className="h-4 w-4 text-primary" />Describe your goal</CardTitle>
              <CardDescription className="text-xs leading-relaxed">一句话就可以开始；已有资源、必须满足的条件和使用场景也可以一起说明。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 p-4 pt-0 sm:p-5 sm:pt-0">
              <Textarea placeholder="e.g. 我要一个像成熟商业产品一样好看的 Agent 管理网页，接入我现在运行的多个 Agent。" value={text} onChange={(e) => setText(e.target.value)} rows={5} className="resize-y text-sm leading-relaxed" autoFocus />
              <div data-tour="home-examples">
                <div className="mb-2 text-[11px] font-medium text-muted-foreground">从示例开始</div>
                <div className="flex flex-wrap gap-2">
                  {EXAMPLES.map((ex, i) => <button key={ex} onClick={() => setText(ex)} title={ex} className="rounded-md border px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-foreground">{["Agent 管理网页", "3D Boss 战系统", "探索产品方向"][i]}</button>)}
                </div>
              </div>
              <div className="space-y-2 border-t pt-4" data-tour="home-create">
                <Button onClick={submit} disabled={busy || !text.trim()} className="w-full gap-2">
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}Create &amp; start research
                </Button>
                <p className="text-center text-[11px] leading-relaxed text-muted-foreground">进度自动保存，研究可能请求澄清；提出的方案由你决定。</p>
              </div>
            </CardContent>
          </Card>
          <div className="mt-4 grid grid-cols-3 gap-2 text-[11px] text-muted-foreground sm:flex sm:flex-wrap sm:items-center sm:gap-x-3">
            {FLOW_STEPS.map((step, i) => <div key={step.label} className="flex flex-col items-center gap-1 sm:flex-row sm:gap-2">{i > 0 && <ArrowRight className="mr-1 hidden h-3 w-3 text-muted-foreground/40 sm:block" />}{step.icon}<span>{step.label}</span></div>)}
          </div>
        </section>

        <section className="min-w-0" data-tour="home-jobs" aria-label="已有研究">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2"><h2 className="text-base font-semibold">Your research jobs</h2>{jobs && <Badge variant="secondary" className="text-[10px]">{jobs.length}</Badge>}</div>
            <div className="flex gap-1"><Button variant="ghost" size="sm" onClick={runHomeTour} className="gap-1 text-xs"><Compass className="h-3.5 w-3.5" />Tour</Button><Button variant="ghost" size="sm" onClick={refresh} className="text-xs">Refresh</Button></div>
          </div>
          <p className="mb-4 text-xs text-muted-foreground">打开结果继续审阅；需要答复或处理的研究优先显示。</p>
          {hasAttentionJobs && <div className="mb-3 flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/5 p-3 text-xs leading-relaxed"><AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" /><span>有研究需要你答复问题或处理错误，打开对应任务即可继续。</span></div>}
          {jobs === null ? <div className="space-y-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-24 w-full rounded-lg" />)}</div>
            : jobs.length === 0 ? <Card className="gap-0 border-dashed py-0"><CardContent className="flex flex-col items-center justify-center px-4 py-12 text-center"><FileText className="mb-3 h-6 w-6 text-muted-foreground" /><p className="text-sm font-medium">No jobs yet</p><p className="mt-2 text-xs leading-relaxed text-muted-foreground">填写目标并开始研究，结果会保存在这里。</p></CardContent></Card>
            : <div className="space-y-2">{[...jobs].sort((a, b) => attentionRank(a.status) - attentionRank(b.status)).map((j) => {
              const config = STATUS_CONFIG[j.status];
              const attention = j.status === "NEEDS_INPUT" || j.status === "PARTIAL" || j.status === "FAILED";
              return <button key={j.id} onClick={() => onOpen(j.id)} className={cn("group w-full rounded-xl border bg-card p-3.5 text-left transition-colors hover:bg-accent/40", attention ? "border-warning/40" : "hover:border-primary/30")}>
                <div className="mb-2 flex items-center justify-between gap-2"><Badge className={cn("gap-1 text-[10px]", config.tone)}>{config.icon}{config.label}</Badge><span className="text-[11px] text-muted-foreground">Revision {j.revision}</span></div>
                <p className="line-clamp-2 text-sm font-medium leading-relaxed">{j.original_request}</p>
                <div className="mt-2 flex items-center justify-between gap-2 text-xs text-muted-foreground"><span>{j.status === "COMPLETED" ? "View proposals" : j.status === "NEEDS_INPUT" ? "Answer question" : j.status === "RESEARCHING" ? "Researching…" : j.status === "PARTIAL" ? "Partial results" : j.status === "FAILED" ? "See error" : "Open workspace"}</span><ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1 group-hover:text-primary" /></div>
              </button>;
            })}</div>}
        </section>
      </div>
    </div>
  );
}
