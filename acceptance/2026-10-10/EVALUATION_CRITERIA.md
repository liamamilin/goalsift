# 2026-10-10 acceptance criteria (recorded before scoring)

Three cases: Agent management web UI, Godot 4 3D Boss fight, vague product goal.
Compare each research input (including answered clarification/constraint) with one
DeepSeek Flash response without search. Baseline can ask for clarification. No
third-party code is executed. No preference for either approach is assumed.

Score each axis 0–2 (0 absent/incorrect, 1 partial, 2 explicit and inspectable):
1. Faithfulness to user requirements; assumptions separate.
2. Reuse of existing resources; integration and new work distinguished.
3. Source traceability: quotes actually collected, exact linked IDs/URLs.
4. Honest uncertainty: licenses, conflicts, visual quality and untested behavior.
5. Decision usefulness: uncovered conditions, concrete tradeoffs/acceptance work.

Report model/tool call counts, elapsed research time and conservative fees
separately. A baseline link is a suggestion unless actually fetched. Score the
ambiguous initial input for appropriate clarification; score the clarified
research for suitability. Compare like input with like input. Small sample,
manual assessment, no statistical superiority claim.

Required runtime/browser observations: create/start, clarify/continue,
pause/no-new-actions/resume, cancel/no-late-commits, historical revision,
MD/JSON downloads, evidence detail, narrow viewport, restart persistence.
Automatic negative tests cover fabricated references/quotes, doc-only VERIFIED,
missing license, conflict, duplicate owner, rollback, budget, private URLs,
configuration, and isolation. Live cases must use real model/search/source reads;
fixtures cannot count as live integration.
