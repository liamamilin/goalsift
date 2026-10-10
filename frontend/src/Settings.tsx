import { useEffect, useState } from "react";
import { getSettings, type Settings as SettingsT } from "./api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle2, Cpu, DollarSign, ShieldCheck, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const Row = ({ k, v }: { k: string; v: React.ReactNode }) => (
    <div className="flex items-center justify-between border-b border-border/50 py-3 text-sm last:border-0">
      <span className="text-muted-foreground">{k}</span>
      <span className="font-medium">{v}</span>
    </div>
  );


export function SettingsPage() {
  const [s, setS] = useState<SettingsT | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { getSettings().then(setS).catch((e) => setErr(String(e))); }, []);

  if (err) return <div className="p-6 text-sm text-destructive">{err}</div>;
  if (!s) return (
    <div className="mx-auto max-w-2xl space-y-4 px-5 py-8">
      <Skeleton className="h-8 w-48" />
      {[0, 1, 2].map((i) => <Skeleton key={i} className="h-40 w-full rounded-xl" />)}
    </div>
  );

  const keyBadge = (configured: boolean, preview: string) => (
    <Badge variant="outline" className={cn("gap-1.5", configured ? "border-success text-success" : "border-destructive text-destructive")}>
      {configured ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
      {preview}
    </Badge>
  );

  return (
    <div className="mx-auto max-w-2xl px-5 py-8">
      {/* Header */}
      <div className="animate-slide-up mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="mt-1.5 text-sm text-muted-foreground">Model, search, budget and security configuration.</p>
      </div>

      <div className="space-y-5">
        {/* Model & Search */}
        <Card className="animate-slide-up stagger-1">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Cpu className="h-4 w-4" />
              </div>
              <div>
                <CardTitle className="text-base">Model &amp; search</CardTitle>
                <CardDescription>Keys are read server-side from .env; never sent to the browser or logs.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Row k="LLM provider" v={s.llm.provider} />
            <Row k="LLM model" v={s.llm.model} />
            <Row k="LLM key" v={keyBadge(s.llm.configured, s.llm.key_preview)} />
            <Row k="Search provider" v={s.search.provider} />
            <Row k="Search key" v={keyBadge(s.search.configured, s.search.key_preview)} />
          </CardContent>
        </Card>

        {/* Budget */}
        <Card className="animate-slide-up stagger-2">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-warning/10 text-warning">
                <DollarSign className="h-4 w-4" />
              </div>
              <div>
                <CardTitle className="text-base">Budget</CardTitle>
                <CardDescription>Hard limits, backend-enforced.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Row k="Max actions / revision" v={s.budget.max_actions} />
            <Row k="Max tool calls / revision" v={s.budget.max_tool_calls} />
            <Row k="Max runtime (s)" v={s.budget.max_runtime_seconds} />
            <Row k="Spend cap (USD)" v={s.budget.budget_usd} />
          </CardContent>
        </Card>

        {/* Security */}
        <Card className="animate-slide-up stagger-3">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-success/10 text-success">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div>
                <CardTitle className="text-base">Security</CardTitle>
                <CardDescription>Built-in protections for safe operation.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <Row k="Binding" v={<code className="rounded bg-muted px-2 py-0.5 text-xs">{s.binding}</code>} />
            <ul className="space-y-2 pt-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                <span>SSRF guard blocks loopback / private / cloud-metadata URLs.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                <span>External web content is untrusted data, never system instructions.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                <span>API keys never reach the browser or logs.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                <span>Research writes only to the app's isolated data directory.</span>
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
