import { useEffect, useState } from "react";
import { getAdoptionChecklist, saveAdoptionCheckItem, type AdoptionCheckItem, type AdoptionChecklistView } from "./api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle, CheckCircle2, ClipboardCheck, ExternalLink, Loader2, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface AdoptionChecklistProps {
  jobId: string;
  revision: number;
  status: string;
  readOnly: boolean;
  refreshKey: number;
}

const STATUS_LABEL: Record<AdoptionCheckItem["status"], string> = {
  PENDING: "待检查", RECORDED: "已记录", FOLLOW_UP: "需跟进",
};
const ASSESSMENT_LABEL: Record<string, string> = {
  VERIFIED: "已限定验证", SUPPORTED: "来源支持，待实测", PARTIAL: "部分满足",
  NOT_SATISFIED: "尚未满足", UNKNOWN: "未知", CONFLICTED: "证据冲突",
};
const TYPE_LABEL: Record<AdoptionCheckItem["item_type"], string> = {
  condition: "目标条件", integration: "集成工作", new_work: "补充工作", risk: "风险",
};

function StatusBadge({ status }: { status: AdoptionCheckItem["status"] }) {
  return <Badge variant="outline" className={cn("text-[10px]", status === "RECORDED" && "border-success/50 text-success", status === "FOLLOW_UP" && "border-warning text-warning")}>{STATUS_LABEL[status]}</Badge>;
}

export function AdoptionChecklist({ jobId, revision, status, readOnly, refreshKey }: AdoptionChecklistProps) {
  const [view, setView] = useState<AdoptionChecklistView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyItem, setBusyItem] = useState<string | null>(null);
  const editable = !readOnly && status === "COMPLETED";

  useEffect(() => {
    let mounted = true;
    getAdoptionChecklist(jobId, revision)
      .then((result) => { if (mounted) { setView(result); setError(null); } })
      .catch((reason) => { if (mounted) setError(String(reason)); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [jobId, revision, refreshKey]);

  const update = async (item: AdoptionCheckItem, next: { status: AdoptionCheckItem["status"]; notes: string }) => {
    setBusyItem(item.item_id);
    try {
      setView(await saveAdoptionCheckItem(jobId, item.item_id, {
        expected_revision: revision,
        expected_annotation_version: item.annotation_version,
        basis_hash: item.basis_hash,
        status: next.status,
        notes: next.notes,
      }));
      toast.success("检查进度已保存");
    } catch (reason) {
      setError(String(reason));
      toast.error(String(reason));
      try { setView(await getAdoptionChecklist(jobId, revision)); setError(null); } catch { /* Keep the original save error visible. */ }
    } finally { setBusyItem(null); }
  };

  return (
    <Card className="gap-0 py-0">
      <CardHeader className="border-b p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-sm"><ClipboardCheck className="h-4 w-4 text-primary" />采用前检查</CardTitle>
          {view && !view.selection_required && <span className="text-xs text-muted-foreground">修订 {view.revision} · {view.items.length} 项</span>}
        </div>
        {view?.proposal_title && <p className="mt-1 truncate text-xs text-muted-foreground">对应方案：{view.proposal_title}</p>}
      </CardHeader>
      <CardContent className="space-y-3 p-4 sm:p-5">
        {loading && <div className="flex items-center gap-2 py-2 text-xs text-muted-foreground"><Loader2 className="h-3.5 w-3.5 animate-spin" />整理检查事项…</div>}
        {error && <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">{error}</div>}
        {!loading && view?.selection_required && (
          <div className="rounded-lg border border-muted bg-muted/20 p-3 text-sm leading-relaxed">
            <p className="font-medium">{view.reason}</p>
            {view.read_only && <p className="mt-1 text-xs text-muted-foreground">历史修订清单只读；此前的记录仍按原修订保留。</p>}
          </div>
        )}
        {!loading && view && !view.selection_required && view.items.length === 0 && (
          <p className="text-sm text-muted-foreground">该方案没有可生成的条件、集成工作、补充工作或风险检查项。</p>
        )}
        {!loading && view && !view.selection_required && view.items.length > 0 && (
          <>
            <div className="flex items-start gap-2 rounded-md border border-warning/25 bg-warning/5 px-3 py-2.5 text-xs leading-relaxed text-muted-foreground">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
              清单记录检查准备与进度。来源支持不等于环境验收；保存备注不会新增证据或改变研究判断。
            </div>
            <ol className="space-y-3">
              {view.items.map((item, index) => (
                <li key={item.item_id}>
                  <ChecklistItemCard
                    item={item}
                    index={index + 1}
                    editable={editable}
                    readOnly={readOnly}
                    busy={busyItem === item.item_id}
                    onSave={(next) => update(item, next)}
                    key={`${item.item_id}:${item.annotation_version}:${item.basis_hash}`}
                  />
                </li>
              ))}
            </ol>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ChecklistItemCard({
  item, index, editable, readOnly, busy, onSave,
}: {
  item: AdoptionCheckItem;
  index: number;
  editable: boolean;
  readOnly: boolean;
  busy: boolean;
  onSave: (next: { status: AdoptionCheckItem["status"]; notes: string }) => void;
}) {
  const [nextStatus, setNextStatus] = useState<AdoptionCheckItem["status"]>(item.status);
  const [notes, setNotes] = useState(item.notes);
  const hasMethod = Boolean(item.verification_method);

  return (
    <Card className="gap-0 border-muted-foreground/15 bg-background py-0">
      <CardContent className="space-y-3 p-3.5 sm:p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="grid h-6 w-6 place-items-center rounded-full bg-primary/10 text-[11px] font-semibold text-primary">{index}</span>
            <Badge variant="secondary" className="text-[10px]">{TYPE_LABEL[item.item_type]}</Badge>
            {item.obligation && <Badge variant="outline" className="text-[10px]">{item.obligation === "REQUIRED" ? "必须" : "可选"} · {item.dimension === "QUALITY" ? "质量" : item.dimension === "FUNCTIONAL" ? "功能" : item.dimension === "COMPLIANCE" ? "合规" : "其他"}</Badge>}
            {item.assessment_status && <Badge variant="outline" className={cn("text-[10px]", ["UNKNOWN", "CONFLICTED", "NOT_SATISFIED"].includes(item.assessment_status) && "border-warning text-warning")}>{ASSESSMENT_LABEL[item.assessment_status]}</Badge>}
          </div>
          <StatusBadge status={item.status} />
        </div>
        <h3 className="break-words text-sm font-semibold leading-relaxed">{item.title}</h3>

        {item.assessments.map((assessment) => (
          <div key={assessment.id} className="space-y-1 rounded-md bg-muted/30 p-2.5 text-xs leading-relaxed">
            <p>{assessment.explanation}</p>
            {!!assessment.gaps?.length && <ul className="list-disc space-y-1 pl-4 text-warning">{assessment.gaps.map((gap, i) => <li key={i}>{gap}</li>)}</ul>}
          </div>
        ))}
        {!!item.gaps.length && item.assessments.length === 0 && <ul className="list-disc space-y-1 pl-4 text-xs text-warning">{item.gaps.map((gap, i) => <li key={i}>{gap}</li>)}</ul>}

        <div className="grid gap-3 border-t pt-3 sm:grid-cols-2">
          <section className="min-w-0 space-y-1.5 text-xs">
            <h4 className="font-medium">验收方式</h4>
            {hasMethod ? <p className="break-words leading-relaxed text-muted-foreground">{item.verification_method}</p> : <p className="text-warning">待明确标准</p>}
          </section>
          <section className="min-w-0 space-y-1.5 text-xs">
            <h4 className="font-medium">下一步</h4>
            <p className="break-words leading-relaxed text-muted-foreground">{item.next_step}</p>
          </section>
        </div>

        {!!item.resources.length && <section className="border-t pt-3 text-xs">
          <h4 className="mb-1.5 font-medium">关联资源</h4>
          <ul className="flex flex-wrap gap-2">{item.resources.map((resource) => <li key={resource.id}>
            <a href={resource.canonical_source} target="_blank" rel="noreferrer" className="inline-flex max-w-full items-center gap-1 rounded-md border px-2 py-1 text-primary hover:underline">
              <span className="truncate">{resource.name}</span><ExternalLink className="h-3 w-3 shrink-0" />
            </a>
          </li>)}</ul>
        </section>}
        {!!item.evidence.length && <section className="border-t pt-3 text-xs">
          <h4 className="mb-1.5 font-medium">已有依据</h4>
          <ul className="space-y-1.5">{item.evidence.map((evidence) => <li key={evidence.id} className="min-w-0 leading-relaxed text-muted-foreground">
            <a href={evidence.source_ref} target="_blank" rel="noreferrer" className="break-all text-primary hover:underline">{evidence.locator || evidence.source_ref} <ExternalLink className="inline h-3 w-3" /></a>
            <span className="ml-1">{evidence.claim}</span>
          </li>)}</ul>
        </section>}

        {item.needs_review && item.previous_annotation && <div className="rounded-md border border-warning/30 bg-warning/5 p-2.5 text-xs leading-relaxed">
          <p className="font-medium text-warning">依据已有变化，旧记录待复核</p>
          <p className="mt-1 text-muted-foreground">旧状态：{STATUS_LABEL[item.previous_annotation.status]}{item.previous_annotation.notes ? ` · ${item.previous_annotation.notes}` : ""}</p>
        </div>}
        {editable ? (
          <div className="space-y-2 border-t pt-3">
            <label htmlFor={`check-status-${item.item_id}`} className="text-xs font-medium">检查进度</label>
            <select id={`check-status-${item.item_id}`} value={nextStatus} onChange={(event) => setNextStatus(event.target.value as AdoptionCheckItem["status"])} className="block w-full rounded-md border bg-background px-3 py-2 text-sm">
              {Object.entries(STATUS_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <label htmlFor={`check-notes-${item.item_id}`} className="text-xs font-medium">人工备注</label>
            <Textarea id={`check-notes-${item.item_id}`} value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={4000} rows={3} className="resize-y" placeholder="记录实际检查安排、观察结果或待跟进事项。备注不会改变研究证据状态。" />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[11px] text-muted-foreground">修订 {item.source_revision} · 注记 v{item.annotation_version}</span>
              <Button size="sm" onClick={() => onSave({ status: nextStatus, notes })} disabled={busy}>
                {busy ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="mr-1 h-3.5 w-3.5" />}
                保存检查记录
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-1 border-t pt-3 text-xs">
            <p className="flex items-center gap-1.5 font-medium"><RotateCcw className="h-3.5 w-3.5 text-muted-foreground" />{readOnly ? "历史记录只读" : "研究完成后可记录检查进度"}</p>
            {item.notes && <p className="whitespace-pre-wrap leading-relaxed text-muted-foreground">{item.notes}</p>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
