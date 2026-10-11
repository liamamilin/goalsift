import { useEffect, useState } from "react";
import { compareRevisions, type JobResult, type RevisionDiff, type RevisionItem } from "./api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function RevisionCompareView({job, revisions, historical}: {job: JobResult; revisions: RevisionItem[]; historical: boolean}) {
  const options = revisions.filter(r => r.revision < job.revision);
  const [base, setBase] = useState(options[0]?.revision ?? 0);
  const [diff, setDiff] = useState<RevisionDiff | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!base) return;
    let active = true;
    compareRevisions(job.id, base, historical ? job.revision : undefined).then(d => {if (active) {setDiff(d); setError("");}}).catch(e => {if (active) setError(String(e));});
    return () => {active = false;};
  }, [job.id, job.revision, job.status, job.budget_usage?.actions, job.evidence.length, job.assessments.length, base, historical, retry]);
  if (!options.length) return <p className="rounded-lg border p-5 text-sm text-muted-foreground">完成下一次修订后，就可以比较研究变化。</p>;
  const money = (usage: RevisionDiff["usage"]["after"]) => usage.cost_unknown || usage.cost_usd == null ? "未知" : `$${Number(usage.cost_usd).toFixed(6)}`;
  const d = diff?.base_revision === base ? diff : null;
  return <div className="min-w-0 space-y-4 [overflow-wrap:anywhere]">
    <Card className="gap-0 py-0"><CardContent className="space-y-3 p-4"><h3 className="text-sm font-semibold">修订变化</h3><div className="flex flex-wrap items-center gap-2 text-xs"><label>比较基准 <select aria-label="比较基准修订" className="ml-2 rounded-md border bg-background p-2" value={base} onChange={e => setBase(Number(e.target.value))}>{options.map(r => <option key={r.revision} value={r.revision}>修订 {r.revision}</option>)}</select></label><span>→ 修订 {job.revision}{historical ? "（历史）" : "（当前）"}</span></div><p className="text-xs leading-relaxed text-muted-foreground">比较已保存的条件、来源、评价和方案覆盖。费用分别属于两轮研究，覆盖变化可能来自条件或方案选择的变化。</p>{d?.is_partial && <p role="status" className="text-xs text-warning">本修订尚未完成，以下为已提交的阶段变化。</p>}</CardContent></Card>
    {error && <p role="alert" className="text-xs text-destructive">{error}<Button size="sm" variant="ghost" onClick={() => setRetry(retry+1)}>重试</Button></p>}
    {!d ? <p className="p-4 text-sm text-muted-foreground">正在读取变化…</p> : <>
      <div className="grid grid-cols-2 gap-3"><Stat label="方案覆盖" value={`${d.summary.coverage_before}/${d.summary.conditions_before} → ${d.summary.coverage_after}/${d.summary.conditions_after}`} /><Stat label="两轮已记录费用" value={`${money(d.usage.before)} → ${money(d.usage.after)}`} /><Stat label="来源变化" value={`${d.summary.new_sources} 新增 · ${d.summary.changed_sources} 内容或版本变化 · ${d.summary.reread_sources} 重读`} /><Stat label="评价变化" value={`${d.assessment_changes.length} 变化 · ${d.summary.reused_assessments} 沿用`} /></div>
      {(Number(d.usage.after.reserved_usd) > 0 || d.usage.after.cost_unknown) && <p className="text-xs text-warning">存在请求费用预留或未知费用，记录金额尚未结清。</p>}
      {!!d.scope && <p className="rounded-lg bg-muted/30 p-3 text-xs leading-relaxed">本轮补查 {d.scope.condition_ids.length} 项条件，费用上限 ${d.scope.budget_usd}。{d.scope.question && `调查问题：${d.scope.question}`}</p>}
      <Card className="gap-0 py-0"><CardContent className="space-y-3 p-4"><h4 className="text-sm font-medium">目标与条件</h4><p className="text-xs text-muted-foreground">{d.conditions.added.length} 新增 · {d.conditions.removed.length} 移出 · {d.conditions.changed.length} 修改 · {d.conditions.unchanged} 未变</p>{!!d.goal_changes.length && <p className="text-xs">目标信息变化：{d.goal_changes.map(k => ({purpose:"目标理解",constraints:"要求与前提",assumptions:"假设",requirements:"要求"})[k] || k).join("、")}</p>}{d.conditions.changed.map(c => <div key={c.after.id} className="space-y-2 border-t pt-3 text-xs"><p className="text-muted-foreground">之前：{c.before.statement} [{c.before.obligation} / {c.before.dimension}]</p><p>现在：{c.after.statement} [{c.after.obligation} / {c.after.dimension}] · {c.after.provenance === "USER_CONFIRMED" ? "用户已确认" : "系统推导"}</p>{c.before.verification_method !== c.after.verification_method && <p>验收：{c.before.verification_method || "待确认"} → {c.after.verification_method || "待确认"}</p>}</div>)}{d.conditions.added.map(c => <p key={c.id} className="text-xs text-success">新增：{c.statement}</p>)}{d.conditions.removed.map(c => <p key={c.id} className="text-xs text-muted-foreground">移出：{c.statement}</p>)}</CardContent></Card>
      {(d.newly_covered.length > 0 || d.newly_uncovered.length > 0) && <Card className="gap-0 py-0"><CardContent className="space-y-2 p-4"><h4 className="text-sm font-medium">方案覆盖变化</h4>{d.newly_covered.map(c => <p key={c} className="text-xs text-success">新增覆盖：{c}</p>)}{d.newly_uncovered.map(c => <p key={c} className="text-xs text-warning">本轮未覆盖：{c}</p>)}</CardContent></Card>}
      <Card className="gap-0 py-0"><CardContent className="space-y-3 p-4"><h4 className="text-sm font-medium">来源与证据</h4><p className="text-xs text-muted-foreground">新增 {d.summary.new_evidence} 条证据记录，包含读取收据与主张依据；记录增加不代表条件已经满足。</p>{d.documents.map(doc => <div key={doc.url} className="space-y-1 border-t pt-3 text-xs"><Badge variant="outline">{{new:"新增来源",changed:"内容或版本变化",reread:"重读，内容未变"}[doc.kind]}</Badge><a className="block text-primary hover:underline" href={doc.url} target="_blank" rel="noreferrer">{doc.category} · {doc.url}</a><p className="text-muted-foreground">版本 {doc.before_version || "未记录"} → {doc.version || "未记录"}</p></div>)}{!d.documents.length && <p className="text-xs text-muted-foreground">未新增或重读来源。</p>}</CardContent></Card>
      {!!d.resources.length && <details className="rounded-lg border p-4 text-xs"><summary className="cursor-pointer font-medium">候选变化 · {d.resources.length}</summary><div className="mt-3 space-y-3">{d.resources.map((r,i) => <p key={i}>{r.before?.name || "无"} → {r.after?.name || "已移出"}；许可 {r.before?.license_claim || "UNKNOWN"} → {r.after?.license_claim || "UNKNOWN"}</p>)}</div></details>}
      <Card className="gap-0 py-0"><CardContent className="space-y-3 p-4"><h4 className="text-sm font-medium">匹配变化 · {d.assessment_changes.length}</h4>{d.assessment_changes.map((a,i) => <details key={i} className="border-t pt-3 text-xs"><summary className="cursor-pointer leading-relaxed"><span className="font-medium">{a.resource}</span> · {a.condition}<span className="mt-1 block text-primary">{a.before.join(" / ") || "未评估"} → {a.after.join(" / ") || "未评估"}</span></summary><div className="mt-2 space-y-2 text-muted-foreground">{a.before_explanations.map((text,j) => <p key={`before-${j}`}>之前：{text}</p>)}{a.explanations.map((text,j) => <p key={`after-${j}`}>现在：{text}</p>)}{a.gaps.map((text,j) => <p key={j}>缺口：{text}</p>)}</div></details>)}{!d.assessment_changes.length && <p className="text-xs text-muted-foreground">匹配判断未发生变化。</p>}</CardContent></Card>
    </>}
  </div>;
}
function Stat({label,value}: {label:string; value:string}) {return <div className="rounded-lg border bg-card p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-2 text-sm font-medium leading-relaxed tabular-nums">{value}</p></div>;}
