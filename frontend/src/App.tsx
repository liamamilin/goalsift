import { useEffect, useState } from "react";
import { Home } from "./Home";
import { Workspace } from "./Workspace";
import { SettingsPage } from "./Settings";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import {
  Compass,
  LayoutDashboard,
  Settings as SettingsIcon,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

type View = { name: "home" } | { name: "workspace"; id: string } | { name: "settings" };

function readView(): View {
  const route = window.location.hash.slice(1);
  if (route === "/settings") return { name: "settings" };
  const match = /^\/jobs\/(job_[a-zA-Z0-9]+)$/.exec(route);
  return match ? { name: "workspace", id: match[1] } : { name: "home" };
}

export default function App() {
  const [view, updateView] = useState<View>(readView);
  const setView = (next: View) => {
    const route = next.name === "workspace" ? `/jobs/${next.id}` : next.name === "settings" ? "/settings" : "/";
    window.history.pushState(null, "", `#${route}`);
    updateView(next);
  };
  useEffect(() => {
    const onRoute = () => updateView(readView());
    window.addEventListener("hashchange", onRoute);
    window.addEventListener("popstate", onRoute);
    return () => {
      window.removeEventListener("hashchange", onRoute);
      window.removeEventListener("popstate", onRoute);
    };
  }, []);

  const isJobsActive = view.name === "home" || view.name === "workspace";
  const isSettingsActive = view.name === "settings";

  const navItem = (active: boolean, icon: React.ReactNode, label: string, onClick: () => void) => (
    <button
      onClick={onClick}
      className={cn(
        "group relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
        active
          ? "bg-primary text-primary-foreground shadow-sm"
          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
      )}
    >
      <span className={cn(
        "flex h-5 w-5 items-center justify-center transition-transform duration-200",
        !active && "group-hover:scale-110",
      )}>
        {icon}
      </span>
      {label}
      {active && (
        <span className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-primary-foreground/40" />
      )}
    </button>
  );

  return (
    <div className="dark flex h-screen w-full overflow-hidden bg-background text-foreground">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col border-r bg-card md:flex">
        {/* Brand */}
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/70 text-primary-foreground shadow-sm">
            <Compass className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-bold leading-tight tracking-tight">GoalSift</div>
            <div className="text-[11px] leading-tight text-muted-foreground">From Goals to Viable Paths</div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-2">
          {navItem(isJobsActive,
            <LayoutDashboard className="h-4 w-4" />, "Jobs", () => setView({ name: "home" }))}
          {navItem(isSettingsActive,
            <SettingsIcon className="h-4 w-4" />, "Settings", () => setView({ name: "settings" }))}
        </nav>

        {/* Footer */}
        <div className="border-t px-5 py-4">
          <div className="flex items-center gap-2 text-[11px] leading-relaxed text-muted-foreground">
            <Sparkles className="h-3 w-3 shrink-0 text-primary/60" />
            <span>Research is advice, not execution.<br />Proposals need your decision.</span>
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile header */}
        <header className="flex items-center gap-3 border-b bg-card/80 px-4 py-3 backdrop-blur-sm md:hidden">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary/70 text-primary-foreground">
            <Compass className="h-4 w-4" />
          </div>
          <span className="text-sm font-bold tracking-tight">GoalSift</span>
          <nav className="ml-auto flex gap-1 rounded-lg bg-muted/50 p-1">
            <button
              onClick={() => setView({ name: "home" })}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition-all",
                isJobsActive ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
              )}
            >
              Jobs
            </button>
            <button
              onClick={() => setView({ name: "settings" })}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition-all",
                isSettingsActive ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
              )}
            >
              Settings
            </button>
          </nav>
        </header>

        {/* Page content with fade transition */}
        <main className="flex-1 overflow-y-auto">
          <div className="animate-fade-in" key={view.name === "workspace" ? `ws-${view.id}` : view.name}>
            <TooltipProvider>
              {view.name === "home" && <Home onOpen={(id) => setView({ name: "workspace", id })} />}
              {view.name === "workspace" && <Workspace jobId={view.id} onBack={() => setView({ name: "home" })} />}
              {view.name === "settings" && <SettingsPage />}
            </TooltipProvider>
          </div>
        </main>
      </div>

      <Toaster richColors position="bottom-right" />
    </div>
  );
}
