import { useEffect, useState } from "react";
import { Dialog } from "radix-ui";
import { Loader2, Search, X } from "lucide-react";
import { toast } from "sonner";
import { getSettings, investigate, type JobResult } from "./api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function TargetedResearchDialog({job, initialConditions, onClose, onSaved}: {
  job: JobResult; initialConditions: string[]; onClose: () => void; onSaved: () => Promise<void>;
}) {
  const [conditions, setConditions] = useState(initialConditions.slice(0, 8));
  const [resources, setResources] = useState<string[]>([]);
  const [budget, setBudget] = useState("0.10");
  const [maximum, setMaximum] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    getSettings().then(s => { if (!active) return; const value = Number(s.budget.budget_usd); const limit = Number.isFinite(value) && value > 0 ? Math.min(value, 1) : 1; setMaximum(limit); setBudget(String(Math.min(limit, 0.1))); }).catch(() => {if (active) setError("无法读取费用上限，请关闭后重试");});
    return () => {active = false;};
  }, []);
  const toggle = (values: string[], id: string) => values.includes(id) ? values.filter(x => x !== id) : [...values, id];
  const validBudget = Number(budget) > 0 && maximum !== null && Number(budget) <= maximum;
  const submit = async () => {
    setBusy(true); setError("");
    try { await investigate(job.id, {expected_revision: job.revision, condition_ids: conditions, resource_ids: resources, budget_usd: Number(budget), question}); await onSaved(); toast.success("补查已启动，原修订已保留"); onClose(); }
    catch (e) {setError(String(e));}
    finally {setBusy(false);}
  };
  return <Dialog.Root open onOpenChange={open => {if (!open && !busy) onClose();}}><Dialog.Portal>
    <Dialog.Overlay className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" />
    <Dialog.Content className="fixed inset-x-3 top-[5vh] z-50 mx-auto flex max-h-[90vh] max-w-xl flex-col rounded-xl border bg-card shadow-xl sm:inset-x-6">
      <div className="flex items-start justify-between gap-3 border-b p-4"><div><Dialog.Title className="text-base font-semibold">针对缺口补查</Dialog.Title><Dialog.Description className="mt-2 text-xs leading-relaxed text-muted-foreground">基于修订 {job.revision} 开始新修订，保留目标、条件和旧结果。新增资料会重新核查对应候选的其他条件。</Dialog.Description></div><Dialog.Close asChild><Button variant="ghost" size="icon" aria-label="关闭补查" disabled={busy}><X className="h-4 w-4" /></Button></Dialog.Close></div>
      <div className="min-h-0 space-y-5 overflow-y-auto p-4 [overflow-wrap:anywhere]">
        <fieldset disabled={busy}><legend className="mb-2 text-sm font-medium">调查哪些条件 <span className="text-xs text-muted-foreground">{conditions.length}/8</span></legend><div className="space-y-2">{job.conditions.map(c => <label key={c.id} className="flex cursor-pointer items-start gap-2 rounded-lg border p-2.5 text-xs leading-relaxed"><input type="checkbox" className="mt-1 shrink-0 accent-primary" checked={conditions.includes(c.id)} disabled={!conditions.includes(c.id) && conditions.length >= 8} onChange={() => setConditions(toggle(conditions,c.id))} /><span>{c.statement}</span></label>)}</div></fieldset>
        <fieldset disabled={busy}><legend className="mb-1 text-sm font-medium">限定候选 <span className="text-xs text-muted-foreground">可选，最多 2 个</span></legend><p className="mb-2 text-xs leading-relaxed text-muted-foreground">不选择时，也会搜索新的候选；选择后仅补查这些候选的资料。</p><div className="space-y-2">{job.resources.map(r => <label key={r.id} className="flex cursor-pointer items-start gap-2 rounded-lg bg-muted/30 p-2.5 text-xs"><input type="checkbox" className="mt-0.5 shrink-0 accent-primary" checked={resources.includes(r.id)} disabled={!resources.includes(r.id) && resources.length >= 2} onChange={() => setResources(toggle(resources,r.id))} /><span className="min-w-0">{r.name}</span></label>)}</div></fieldset>
        <label className="block space-y-2 text-sm font-medium">调查问题 <span className="text-xs font-normal text-muted-foreground">可选</span><Textarea aria-label="调查问题" placeholder="例如：是否提供已有 Agent 的启动、暂停接口？" value={question} onChange={e => setQuestion(e.target.value)} maxLength={600} disabled={busy} /></label>
        <label className="block space-y-2 text-sm font-medium">本次费用上限（美元）<input aria-label="本次费用上限（美元）" className="block w-full rounded-md border bg-background px-3 py-2 text-sm" type="number" min="0.001" step="0.001" max={maximum ?? undefined} value={budget} onChange={e => setBudget(e.target.value)} disabled={busy || maximum === null} /></label>
        <p className="text-xs leading-relaxed text-muted-foreground">费用包含模型与搜索调用，上限 {maximum === null ? "读取中…" : `$${maximum}`}。达到上限会停止新调用并保存部分结果，恢复时沿用同一上限。</p>
        {error && <p role="alert" className="text-xs text-destructive">{error}</p>}
      </div>
      <div className="flex flex-wrap justify-end gap-2 border-t p-4"><Button variant="outline" onClick={onClose} disabled={busy}>取消</Button><Button onClick={submit} disabled={busy || !conditions.length || !validBudget || job.status !== "COMPLETED"}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}开始补查 · 新修订</Button></div>
    </Dialog.Content>
  </Dialog.Portal></Dialog.Root>;
}
