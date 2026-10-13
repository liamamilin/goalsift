import { useEffect, useState } from "react";
import { getProposalDecision, saveProposalDecision, type ProposalDecisionView, type ProposalItem } from "./api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle2, Clock, Loader2, RotateCcw, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

interface ProposalDecisionProps {
  jobId: string;
  revision: number;
  status: string;
  proposal: ProposalItem | null;
  readOnly: boolean;
  onChanged?: () => void;
}

export function ProposalDecision({ jobId, revision, status, proposal, readOnly, onChanged }: ProposalDecisionProps) {
  const [view, setView] = useState<ProposalDecisionView | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [reason, setReason] = useState("");
  const canEdit = !readOnly && status === "COMPLETED";
  const decision = view?.decision;
  const active = decision?.active === true;
  const hasCurrentDecision = Boolean(decision && decision.source_revision === revision && active);

  useEffect(() => {
    let mounted = true;
    getProposalDecision(jobId, revision)
      .then((result) => { if (mounted) setView(result); })
      .catch((error) => { if (mounted) toast.error(String(error)); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [jobId, revision]);

  const openEditor = (initial: string) => { setReason(initial); setEditing(true); };
  const save = async () => {
    if (!view) return;
    setBusy(true);
    try {
      const updated = await saveProposalDecision(jobId, {
        expected_revision: revision,
        expected_annotation_version: view.annotation_version,
        action: hasCurrentDecision ? "UPDATE_REASON" : "SELECT",
        ...(proposal ? { proposal_id: proposal.id } : {}),
        reason,
      });
      setView(updated);
      setEditing(false);
      onChanged?.();
      toast.success(hasCurrentDecision ? "选择理由已更新" : "已记录倾向方案");
    } catch (error) {
      toast.error(String(error));
      try { setView(await getProposalDecision(jobId, revision)); } catch { /* Keep the save error visible. */ }
    } finally { setBusy(false); }
  };

  const withdraw = async () => {
    if (!view) return;
    setBusy(true);
    try {
      setView(await saveProposalDecision(jobId, {
        expected_revision: revision,
        expected_annotation_version: view.annotation_version,
        action: "WITHDRAW",
      }));
      setEditing(false);
      onChanged?.();
      toast.success("已撤回方案倾向记录");
    } catch (error) {
      toast.error(String(error));
      try { setView(await getProposalDecision(jobId, revision)); } catch { /* Keep the save error visible. */ }
    } finally { setBusy(false); }
  };

  const stale = view?.previous_decision;
  const display = hasCurrentDecision || readOnly || decision?.action === "WITHDRAW" ? decision : null;

  return (
    <Card className="gap-0 border-primary/20 bg-primary/[0.025] py-0">
      <CardContent className="space-y-3 p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck className="h-4 w-4 text-primary" />你的方案决定
          </div>
          <span className="text-[11px] text-muted-foreground">仅记录倾向，不代表条件已满足或方案已执行</span>
        </div>

        {loading ? <div className="flex items-center gap-2 py-2 text-xs text-muted-foreground"><Loader2 className="h-3.5 w-3.5 animate-spin" />读取决定记录…</div> : (
          <>
            {stale?.active && stale.source_revision !== revision && !hasCurrentDecision && (
              <div className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-xs leading-relaxed">
                <div className="flex items-center gap-2 font-medium text-warning"><Clock className="h-3.5 w-3.5" />旧修订决定待重新确认</div>
                <p className="mt-1.5 text-foreground/80">修订 {stale.source_revision}：{stale.proposal?.title ?? "原方案快照暂不可用"}</p>
                {stale.reason && <p className="mt-1 text-muted-foreground">当时理由：{stale.reason}</p>}
              </div>
            )}

            {display && (
              <div className="flex flex-col gap-3 rounded-lg border bg-background/70 p-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={display.active ? "default" : "outline"} className="gap-1">
                      {display.active ? <CheckCircle2 className="h-3 w-3" /> : <RotateCcw className="h-3 w-3" />}
                      {display.active ? (readOnly ? "此修订倾向" : "当前倾向") : "已撤回"}
                    </Badge>
                    <span className="text-xs text-muted-foreground">记录于修订 {display.source_revision}</span>
                  </div>
                  {display.reason ? <p className="whitespace-pre-wrap text-sm leading-relaxed">{display.reason}</p> : <p className="text-xs text-muted-foreground">未填写选择理由</p>}
                </div>
                {canEdit && hasCurrentDecision && !editing && <div className="flex shrink-0 gap-2">
                  <Button size="sm" variant="outline" onClick={() => openEditor(display.reason)}>修改理由</Button>
                  <Button size="sm" variant="ghost" onClick={withdraw} disabled={busy}>撤回</Button>
                </div>}
              </div>
            )}

            {!display && !editing && !canEdit && !stale?.active && (
              <p className="text-xs leading-relaxed text-muted-foreground">{readOnly ? "此修订没有保存方案决定。" : "研究完成后可记录方案倾向。"}</p>
            )}
            {!display && !editing && !canEdit && stale?.active && (
              <p className="text-xs text-muted-foreground">请在新修订研究完成后检查当前方案，再明确记录是否延续。</p>
            )}
            {canEdit && !editing && !hasCurrentDecision && view?.proposal_available && proposal && (
              <Button size="sm" onClick={() => openEditor(stale?.reason ?? "")}>
                {stale?.active ? "重新确认当前方案" : decision?.action === "WITHDRAW" ? "重新记录倾向方案" : "记录倾向方案"}
              </Button>
            )}
            {canEdit && !editing && !view?.proposal_available && (
              <p className="text-xs text-muted-foreground">此修订没有可供审查的有效方案，暂时不能记录选择。</p>
            )}

            {editing && (
              <div className="space-y-2">
                <label htmlFor={`decision-reason-${jobId}`} className="text-xs font-medium">为什么倾向这个方案？（可选）</label>
                <Textarea id={`decision-reason-${jobId}`} value={reason} onChange={(event) => setReason(event.target.value)} maxLength={6000} rows={3} className="resize-y bg-background" placeholder="例如：更符合现有技术条件，且主要缺口可以在本地验证。" />
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[11px] text-muted-foreground">保存时会记录修订号和注记版本，可随时撤回。</span>
                  <div className="flex gap-2">
                    <Button size="sm" variant="ghost" onClick={() => setEditing(false)} disabled={busy}>取消</Button>
                    <Button size="sm" onClick={save} disabled={busy || !view}>{busy && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}{hasCurrentDecision ? "保存理由" : "保存倾向方案"}</Button>
                  </div>
                </div>
              </div>
            )}

            {!!view?.history.length && (
              <details className="border-t pt-2 text-xs">
                <summary className="cursor-pointer text-muted-foreground">决定记录 · {view.history.length}</summary>
                <ol className="mt-2 space-y-2">
                  {[...view.history].reverse().map((item) => (
                    <li key={item.decision_id} className="rounded-md bg-muted/40 px-3 py-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{item.action === "SELECT" ? "记录倾向" : item.action === "UPDATE_REASON" ? "修改理由" : "撤回"}</span>
                        <span className="text-muted-foreground">修订 {item.source_revision} · 注记 v{item.annotation_version}</span>
                        <time className="text-muted-foreground">{new Date(item.created_at).toLocaleString()}</time>
                      </div>
                      {item.reason && <p className="mt-1 whitespace-pre-wrap leading-relaxed text-muted-foreground">{item.reason}</p>}
                    </li>
                  ))}
                </ol>
              </details>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
