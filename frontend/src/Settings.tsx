import { useEffect, useState } from "react";
import { getSettings, type Settings as SettingsT } from "./api";

export function SettingsPage() {
  const [s, setS] = useState<SettingsT | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { getSettings().then(setS).catch((e) => setErr(String(e))); }, []);
  if (err) return <div className="error">{err}</div>;
  if (!s) return <p className="muted">Loading…</p>;
  return (
    <div className="settings">
      <h2>Settings</h2>
      <section>
        <h3>Model & search</h3>
        <table className="kv">
          <tbody>
            <tr><td>LLM provider</td><td>{s.llm.provider}</td></tr>
            <tr><td>LLM model</td><td>{s.llm.model}</td></tr>
            <tr><td>LLM key</td><td><code className={s.llm.configured ? "ok" : "bad"}>{s.llm.key_preview}</code></td></tr>
            <tr><td>Search provider</td><td>{s.search.provider}</td></tr>
            <tr><td>Search key</td><td><code className={s.search.configured ? "ok" : "bad"}>{s.search.key_preview}</code></td></tr>
          </tbody>
        </table>
      </section>
      <section>
        <h3>Budget (hard limits, backend-enforced)</h3>
        <table className="kv">
          <tbody>
            <tr><td>Max actions / run</td><td>{s.budget.max_actions}</td></tr>
            <tr><td>Max tool calls / run</td><td>{s.budget.max_tool_calls}</td></tr>
            <tr><td>Max runtime (s)</td><td>{s.budget.max_runtime_seconds}</td></tr>
            <tr><td>Spend cap (USD)</td><td>{s.budget.budget_usd}</td></tr>
          </tbody>
        </table>
      </section>
      <section>
        <h3>Security</h3>
        <p>Binding: <code>{s.binding}</code></p>
        <p className="muted">{s.note}</p>
        <ul className="muted">
          <li>SSRF guard blocks loopback / private / cloud-metadata URLs.</li>
          <li>External web content is treated as untrusted data, never system instructions.</li>
          <li>API keys are read server-side from <code>.env</code>; never sent to the browser or logs.</li>
          <li>Research writes only to the app's isolated data directory.</li>
        </ul>
      </section>
    </div>
  );
}
