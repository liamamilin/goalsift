import { useState } from "react";
import { toast } from "sonner";
import { Check, Pencil, RotateCcw, Trash2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { reviewGoal, type Condition, type ConditionEdit, type JobResult } from "./api";

export function GoalReviewView({job, readOnly, onSaved, onAssessment}: {
  job: JobResult; readOnly: boolean; onSaved: () => Promise<void>; onAssessment: (id: string) => void;
}) {
  const [edits, setEdits] = useState<Record<string, ConditionEdit>>({});
  const [assumptions, setAssumptions] = useState<Record<number, "confirm" | "remove">>({});
  const [purpose, setPurpose] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const editable = !readOnly && job.status === "COMPLETED" && !busy;
  const count = Object.keys(edits).length + Object.keys(assumptions).length + Number(purpose !== undefined);
  const setEdit = (id: string, value?: ConditionEdit) => setEdits(prev => {
    const next = {...prev}; if (value) next[id] = value; else delete next[id]; return next;
  });
  const setAssumption = (index: number, action?: "confirm" | "remove") => setAssumptions(prev => {
    const next = {...prev}; if (action) next[index] = action; else delete next[index]; return next;
  });
  const submit = async () => {
    setBusy(true);
    try {
      await reviewGoal(job.id, {expected_revision: job.revision, conditions: Object.values(edits),
        assumptions: Object.entries(assumptions).map(([index, action]) => ({index: Number(index), action})), purpose});
      setEdits({}); setAssumptions({}); setPurpose(undefined);
      toast.success("调整已保存，正在研究新的修订");
      await onSaved();
    } catch (e) { toast.error(String(e)); }
    finally { setBusy(false); }
  };

  return <div className="space-y-4">
    <Card className="gap-0 py-0"><CardContent className="space-y-4 p-4">
      <div><h3 className="text-sm font-semibold">目标与条件复核</h3><p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">确认表示这是你的要求；资源是否满足，仍由匹配与证据判断。调整后会保留旧结果，开始新修订并计入研究用量。</p></div>
      {readOnly && <p className="text-xs text-warning">历史修订只读。切换到当前修订后可调整。</p>}
      {!readOnly && job.status !== "COMPLETED" && <p className="text-xs text-muted-foreground">研究完成后可确认或调整条件。</p>}
      <details className="text-xs"><summary className="cursor-pointer text-muted-foreground">用户原话 · 不会被覆盖</summary><p className="mt-2 whitespace-pre-wrap leading-relaxed">{job.original_request}</p></details>
      <div>
        <div className="flex items-center justify-between gap-2"><span className="text-xs font-medium text-muted-foreground">目标理解</span>{editable && purpose === undefined && <Button variant="ghost" size="sm" onClick={() => setPurpose(job.goal?.purpose || job.original_request)}><Pencil className="h-3 w-3" />调整</Button>}</div>
        {purpose === undefined ? <p className="mt-1 text-sm leading-relaxed">{job.goal?.purpose || "尚未形成目标理解"}</p> : <div className="mt-2 space-y-2"><Textarea aria-label="目标理解" value={purpose} onChange={e => setPurpose(e.target.value)} maxLength={2000} disabled={!editable} /><Button variant="ghost" size="sm" onClick={() => setPurpose(undefined)} disabled={!editable}>撤销目标调整</Button></div>}
      </div>
      {!!job.goal?.constraints?.length && <details className="text-xs"><summary className="cursor-pointer text-muted-foreground">用户要求与前提</summary><ul className="mt-2 space-y-2">{job.goal.constraints.map((c, i) => <li key={i} className="leading-relaxed"><Badge variant="outline" className="mr-2 text-[10px]">{c.provenance === "USER_CONFIRMED" ? "用户已确认" : c.provenance === "USER_STATED" ? "用户原话" : "系统推断 · 待确认"}</Badge>{c.text}</li>)}</ul></details>}
      {!!job.goal?.assumptions?.length && <details className="space-y-2"><summary className="cursor-pointer text-xs font-medium text-warning">未确认假设 · {job.goal.assumptions.length}</summary>{job.goal.assumptions.map((a, i) => <div key={i} className="rounded-lg bg-muted/30 p-3 sm:flex sm:items-start sm:justify-between sm:gap-2"><p className="min-w-0 flex-1 text-xs leading-relaxed">{a.text}</p>{editable && <div className="mt-2 flex shrink-0 flex-wrap gap-1 sm:mt-0">{assumptions[i] ? <><Badge variant="outline">{assumptions[i] === "confirm" ? "待提交：确认前提" : "待提交：移除假设"}</Badge><Button variant="ghost" size="sm" onClick={() => setAssumption(i)}>撤销</Button></> : <><Button variant="ghost" size="sm" onClick={() => setAssumption(i, "confirm")}>确认前提</Button><Button variant="ghost" size="sm" onClick={() => setAssumption(i, "remove")}>移除假设</Button></>}</div>}</div>)}</details>}
      {!!job.goal?.condition_decisions?.some(d => d.action === "remove") && <details className="text-xs"><summary className="cursor-pointer text-muted-foreground">已移出目标的条件</summary><ul className="mt-2 space-y-2">{job.goal.condition_decisions.filter(d => d.action === "remove").map((d, i) => <li key={i}>r{d.revision} · {d.original_statement}</li>)}</ul></details>}
      {editable && job.conditions.some(c => c.provenance !== "USER_CONFIRMED") && <Button variant="outline" size="sm" onClick={() => setEdits(prev => {
        const next = {...prev}; job.conditions.filter(c => c.provenance !== "USER_CONFIRMED" && !next[c.id]).forEach(c => {next[c.id] = {condition_id: c.id, action: "confirm"};}); return next;
      })} disabled={job.conditions.every(c => c.provenance === "USER_CONFIRMED" || edits[c.id])}><Check className="h-3.5 w-3.5" />确认其余条件</Button>}
    </CardContent></Card>

    {count > 0 && <div className="sticky top-3 z-10 flex flex-col gap-3 rounded-lg border border-primary/25 bg-card/95 p-3 shadow-sm backdrop-blur sm:flex-row sm:items-center sm:justify-between"><span className="text-xs">{count} 项调整待提交。原修订 {job.revision} 会保留。</span><Button size="sm" onClick={submit} disabled={!editable || (purpose !== undefined && !purpose.trim()) || Object.values(edits).some(e => e.action === "update" && !e.statement?.trim())}>{busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}保存并继续研究</Button></div>}
    {job.conditions.map(c => {
      const edit = edits[c.id];
      const linked = job.assessments.filter(a => a.condition_id === c.id);
      return <Card key={c.id} className={cn("gap-0 py-0", edit && "border-primary/30")}><CardContent className="p-4">
        <div className="mb-2 flex flex-wrap gap-1.5"><Badge variant="outline" className="text-[10px]">{edit?.obligation || c.obligation}</Badge><Badge variant="outline" className="text-[10px]">{edit?.dimension || c.dimension}</Badge><Badge variant="outline" className={cn("text-[10px]", c.provenance === "USER_CONFIRMED" ? "text-success border-success/30" : "text-warning border-warning/30")}>{c.provenance === "USER_CONFIRMED" ? "用户已确认" : c.provenance === "USER_STATED" ? "用户原话" : "系统推导 · 待确认"}</Badge>{edit && <Badge className="text-[10px]">待提交：{edit.action === "remove" ? "移出目标" : edit.action === "update" ? "修改并确认" : "确认"}</Badge>}</div>
        {edit?.action === "update" ? <ConditionEditor condition={c} edit={edit} onChange={value => setEdit(c.id, value)} disabled={!editable} /> : <p className={cn("text-sm leading-relaxed", edit?.action === "remove" && "line-through text-muted-foreground")}>{c.statement}</p>}
        {editable && <div className="mt-3 flex flex-wrap gap-1">{edit ? <Button variant="ghost" size="sm" onClick={() => setEdit(c.id)}><RotateCcw className="h-3 w-3" />撤销</Button> : <>{c.provenance !== "USER_CONFIRMED" && <Button variant="outline" size="sm" onClick={() => setEdit(c.id, {condition_id: c.id, action: "confirm"})}><Check className="h-3 w-3" />确认条件</Button>}<Button variant="ghost" size="sm" onClick={() => setEdit(c.id, {condition_id: c.id, action: "update", statement: c.statement, obligation: c.obligation, dimension: c.dimension, verification_method: c.verification_method || ""})}><Pencil className="h-3 w-3" />修改</Button><Button variant="ghost" size="sm" onClick={() => setEdit(c.id, {condition_id: c.id, action: "remove"})}><Trash2 className="h-3 w-3" />移出目标</Button></>}</div>}
        <details className="mt-3 text-xs leading-relaxed text-muted-foreground"><summary className="cursor-pointer">推导依据与验收方式</summary><p className="mt-2 break-words">依据：{c.origin || "未记录"}</p><p className="mt-2">验收：{c.verification_method || "待确认"}</p></details>
        {!!linked.length && <details className="mt-3 border-t pt-3"><summary className="cursor-pointer text-xs text-muted-foreground">查看 {linked.length} 项资源评估</summary><div className="mt-2 space-y-1">{linked.map(a => <button key={a.id} onClick={() => onAssessment(a.id)} className="flex w-full items-start gap-2 rounded-lg p-2 text-left hover:bg-accent"><Badge variant="outline" className="shrink-0 text-[10px]">{a.status}</Badge><span className="line-clamp-2 text-xs text-muted-foreground">{a.explanation}</span></button>)}</div></details>}
      </CardContent></Card>;
    })}
  </div>;
}

function ConditionEditor({condition, edit, onChange, disabled}: {condition: Condition; edit: ConditionEdit; onChange: (e: ConditionEdit) => void; disabled: boolean}) {
  const selectClass = "w-full min-w-0 rounded-md border bg-background px-2 py-2 text-xs";
  return <div className="space-y-3">
    <label className="block text-xs text-muted-foreground">成立条件<Textarea aria-label={`成立条件：${condition.statement.slice(0, 50)}`} className="mt-1" value={edit.statement || ""} onChange={e => onChange({...edit, statement: e.target.value})} maxLength={2000} disabled={disabled} /></label>
    <div className="grid grid-cols-2 gap-3"><label className="text-xs text-muted-foreground">必要程度<select className={selectClass} aria-label={`必要程度：${condition.statement.slice(0, 50)}`} value={edit.obligation} onChange={e => onChange({...edit, obligation: e.target.value as Condition["obligation"]})} disabled={disabled}><option value="REQUIRED">必需</option><option value="OPTIONAL">可选</option></select></label><label className="text-xs text-muted-foreground">条件维度<select className={selectClass} aria-label={`条件维度：${condition.statement.slice(0, 50)}`} value={edit.dimension} onChange={e => onChange({...edit, dimension: e.target.value as Condition["dimension"]})} disabled={disabled}><option value="FUNCTIONAL">功能</option><option value="QUALITY">质量</option><option value="COMPLIANCE">合规</option><option value="OTHER">其他</option></select></label></div>
    <label className="block text-xs text-muted-foreground">验收方式<Textarea aria-label={`验收方式：${condition.statement.slice(0, 50)}`} className="mt-1" value={edit.verification_method || ""} onChange={e => onChange({...edit, verification_method: e.target.value})} maxLength={2000} disabled={disabled} /></label>
  </div>;
}
