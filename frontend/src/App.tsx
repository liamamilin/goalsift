import { useState } from "react";
import { Home } from "./Home";
import { Workspace } from "./Workspace";
import "./App.css";

export default function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  return (
    <div className="app">
      <header className="header">
        <h1 onClick={() => setJobId(null)}>GoalSift</h1>
        <span className="subtitle">From Goals to Viable Paths · Phase A</span>
      </header>
      <main className="main">
        {jobId ? <Workspace jobId={jobId} onBack={() => setJobId(null)} /> : <Home onOpen={setJobId} />}
      </main>
      <footer className="footer">
        <span className="muted">Research is advice, not execution. Proposals need your decision.</span>
      </footer>
    </div>
  );
}
