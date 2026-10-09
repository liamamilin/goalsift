# GoalSift — From Goals to Viable Paths

A **goal-driven AI solution-research application** (Phase A). A user states a desired
outcome; the app derives and challenges its conditions, discovers real existing
resources, assesses evidence-backed suitability, and proposes paths for **human
selection**. Phase A does **not** execute selected production plans.

Paradigm: **Define → Derive → Challenge → Discover → Match → Propose**.

## Status

Phase A · Milestone M0 (safe baseline) — see `M0_REPORT.md`.

## Specs

Authoritative specification documents (read in order before changing code):

1. `01_PRODUCT_SPEC.md`
2. `02_PARADIGM_SPEC.md`
3. `03_USER_WORKFLOW.md`
4. `04_AGENT_RUNTIME.md` — single authority for Job lifecycle
5. `05_DATA_AND_ARTIFACTS.md` — single authority for schemas & assessment statuses
6. `06_ARCHITECTURE.md` — provisional; verified in M1
7. `07_DEVELOPMENT_PLAN.md` — single authority for milestones & acceptance gates

`AGENTS.md` is the binding execution entrypoint.

## Quick start (M0 baseline)

```bash
# install dev deps
python3 -m pip install -e ".[dev]" 2>/dev/null || python3 -m pip install pytest

# run isolation + baseline tests
python3 -m pytest
```

## Configuration

Copy `.env.example` to `.env` and fill in real values. `.env` is gitignored.
M0 needs no credentials; M1 live tests require authorized LLM + search keys or
they are reported BLOCKED (never faked PASS).

## Layout

```
goalsift/            application package (grown per milestone)
  paths.py           isolated data-root resolution + path guard rails
tests/               isolation & baseline assertions
specs/  (root)       *.md specification documents
M0_REPORT.md         M0 milestone report
```
