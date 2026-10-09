import { useState } from "react";
import { Home } from "./Home";
import { Workspace } from "./Workspace";
import { SettingsPage } from "./Settings";
import "./App.css";

type View = { name: "home" } | { name: "workspace"; id: string } | { name: "settings" };

export default function App() {
  const [view, setView] = useState<View>({ name: "home" });
  return (
    <div className="app">
      <header className="header">
        <h1 onClick={() => setView({ name: "home" })}>GoalSift</h1>
        <span className="subtitle">From Goals to Viable Paths · Phase A</span>
        <nav className="nav">
          <button className="ghost" onClick={() => setView({ name: "home" })}>Home</button>
          <button className="ghost" onClick={() => setView({ name: "settings" })}>Settings</button>
        </nav>
      </header>
      <main className="main">
        {view.name === "home" && <Home onOpen={(id) => setView({ name: "workspace", id })} />}
        {view.name === "workspace" && <Workspace jobId={view.id} onBack={() => setView({ name: "home" })} />}
        {view.name === "settings" && <SettingsPage />}
      </main>
      <footer className="footer">
        <span className="muted">Research is advice, not execution. Proposals need your decision.</span>
      </footer>
    </div>
  );
}
