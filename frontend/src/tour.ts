/**
 * Guided tours via Driver.js (lightweight, zero-dep, framework-agnostic).
 * Replaces hand-rolled "what next" cards with a real spotlight + popover tour
 * that points at the actual element and says "do this here".
 */
import { driver, type Driver } from "driver.js";
import "driver.js/dist/driver.css";
import type { JobStatus } from "./api";

const DONE_KEY = "goalsift.tour.seen";
let activeTour: Driver | undefined;

export function stopTour() {
  activeTour?.destroy();
  activeTour = undefined;
}

export function hasSeenTour(): boolean {
  return localStorage.getItem(DONE_KEY) === "1";
}
function markSeen() {
  localStorage.setItem(DONE_KEY, "1");
}

/** Home page tour: the input + create flow. */
export function runHomeTour(): Driver {
  stopTour();
  const d = driver({
    showProgress: true,
    nextBtnText: "Next →",
    prevBtnText: "← Back",
    doneBtnText: "Got it",
    steps: [
      {
        element: '[data-tour="home-goal"]',
        popover: { title: "1. Describe your goal", description: "Type the outcome you want here. One sentence is enough." },
      },
      {
        element: '[data-tour="home-examples"]',
        popover: { title: "Try an example", description: "Not sure what to write? Click one to fill the box." },
      },
      {
        element: '[data-tour="home-create"]',
        popover: { title: "2. Create & start", description: "GoalSift then researches real resources live, may ask you a key question, and proposes evidence-backed paths." },
      },
      {
        element: '[data-tour="home-jobs"]',
        popover: { title: "3. Your jobs", description: "Click any job to open its workspace. Badge colour tells you what to do next." },
      },
    ],
  });
  d.drive();
  activeTour = d;
  markSeen();
  return d;
}

/**
 * Workspace tour. Steps adapt to job status so the guidance always matches
 * what the user should actually do next.
 */
export function runWorkspaceTour(status: JobStatus, options: { readOnly?: boolean; onDestroyed?: () => void } = {}): Driver {
  stopTour();
  const steps = workspaceSteps(status).filter((step) => !options.readOnly ||
    !['[data-tour="ws-start"]', '[data-tour="ws-input"]', '[data-tour="ws-refine"]'].includes(step.element));
  const d = driver({
    showProgress: true,
    nextBtnText: "Next →",
    prevBtnText: "← Back",
    doneBtnText: "Done",
    onDestroyed: options.onDestroyed,
    steps,
  });
  d.drive();
  activeTour = d;
  markSeen();
  return d;
}

function workspaceSteps(status: JobStatus) {
  const statusSteps: Record<JobStatus, ReturnType<typeof baseSteps>> = {
    CREATED: [
      { element: '[data-tour="ws-status"]', popover: { title: "Just created", description: "This job hasn't run yet." } },
      { element: '[data-tour="ws-goal"]', popover: { title: "Your goal", description: "The original text is preserved; you'll refine it later if needed." } },
      { element: '[data-tour="ws-start"]', popover: { title: "Start here", description: "Press Start research. It derives conditions, searches real resources, and proposes paths within the configured budget." } },
    ],
    RESEARCHING: [
      { element: '[data-tour="ws-status"]', popover: { title: "Researching…", description: "GoalSift is working. You don't need to do anything right now." } },
      { element: '[data-tour="ws-tablist"]', popover: { title: "Watch live progress", description: "Click the Events tab to see real search/read activity as it happens." } },
    ],
    NEEDS_INPUT: [
      { element: '[data-tour="ws-status"]', popover: { title: "Needs your input", description: "GoalSift hit a question that changes the solution space." } },
      { element: '[data-tour="ws-input"]', popover: { title: "Answer here", description: "Reply, or state an assumption to continue under. Research resumes after you submit." } },
    ],
    COMPLETED: [
      { element: '[data-tour="ws-status"]', popover: { title: "Research complete", description: "Now you review. Here's the order to follow." } },
      { element: '[data-tour="ws-tablist"]', popover: { title: "1. Review the Proposal", description: "Start with the summary, recommendation reason, risks, and costs." } },
      { element: '[data-tour="ws-tablist"]', popover: { title: "2. Trace the evidence", description: "Open the Match tab — each assessment links to its condition, resource, and source evidence." } },
      { element: '[data-tour="ws-export"]', popover: { title: "3. Export to share", description: "Grab the Markdown or JSON here when you're ready." } },
      { element: '[data-tour="ws-refine"]', popover: { title: "Optional: Refine", description: "Add a constraint (e.g. 'commercial-use only') to re-research as a new revision. The old one stays traceable." } },
    ],
    PARTIAL: [
      { element: '[data-tour="ws-status"]', popover: { title: "Partial results", description: "Budget, tools, or sources ran out before completion." } },
      { element: '[data-tour="ws-start"]', popover: { title: "Resume or refine", description: "Resolve the budget or service limit, then press Resume to continue." } },
    ],
    PAUSED: [
      { element: '[data-tour="ws-start"]', popover: { title: "Paused", description: "Press Resume to continue the research." } },
    ],
    FAILED: [
      { element: '[data-tour="ws-tablist"]', popover: { title: "Something failed", description: "Open the Events tab to see the error, then press Resume to retry." } },
      { element: '[data-tour="ws-start"]', popover: { title: "Retry", description: "Press Resume to retry the failed research." } },
    ],
    CANCELLED: [
      { element: '[data-tour="ws-status"]', popover: { title: "Cancelled", description: "This job is done. Create a new one from the Jobs list to continue." } },
    ],
  };
  return statusSteps[status] ?? baseSteps();
}

function baseSteps() {
  return [
    { element: '[data-tour="ws-goal"]', popover: { title: "Goal", description: "Your original goal, preserved." } },
    { element: '[data-tour="ws-tablist"]', popover: { title: "Tabs", description: "Proposal, Conditions, Resources, Match (evidence), and Events." } },
  ];
}
