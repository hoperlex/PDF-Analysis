# Task WEB-REVIEW-FOLLOWUPS-01 — the review screen's v2 follow-ups: severity in the history, and four defects seen on the way

task_id: WEB-REVIEW-FOLLOWUPS-01

## Outcome

The decision history and the knowledge base show a decision's severity beside its verdict (the data is already served as
`DecisionEvent.severity`); a pending reject no longer reads «Принимаю…»; a verdict result never leaks to another finding
selection; the severity refusal sentence goes away once the expert picks a severity; and a comment refusal re-renders. Each
defect has a failing-first test.

## Depends on

- `REVIEW-V2-UI-01` and `WEB-FOLLOWUPS-02` — completed on `agent/lane-c-01`; this slice starts from `integration/beta-1`
  (`64203e91`), which contains them.

## Frozen inputs

- base: `integration/beta-1` at `64203e91` (dev `d410ac64` + lanes B and C + a fixture flip), not yet in `origin/dev`;
- migration head `0029_routing_refusal_codes`; API 73/83/242; 27 error codes; contract `1.0.0`; this task changes no contract and
  adds no migration;
- rulings: `R-135`, `R-144d` (while another session's complete gate runs on this host: no containers and no test batteries, only
  container-free checks), and the owner's standing order of 2026-10-22 «гони до беты без вопросов»: a choice that no recorded
  decision blocks is taken with the conservative default and reported under "Decisions taken", not asked.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `web/src/widgets/decision-history/**`
- `web/src/widgets/knowledge-base/**`
- `web/src/_pages/review/**`
- `web/src/features/append-comment/**`
- `web/src/features/record-verdict/**`
- `web/src/widgets/decision-panel/**`
- `web/src/entities/finding/**`
- `web/src/entities/expert-decision/**`
- `web/tests/unit/{decisions,review,widgets,entities,styles,run}/**`
- `docs/program/WEB-REVIEW-FOLLOWUPS-01.md`
- `docs/program/tasks/WEB-REVIEW-FOLLOWUPS-01.md`

## Lane resources

- container-free until the integrator says the host gate has ended; reserved and unused: foundation_instance `auditmanager-lane-d`,
  postgres_port `57660`, s3_api_port `61460`

## Forbidden hotspots

Every `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, `pyproject.toml`, `uv.lock`, `web/package.json`,
`web/package-lock.json`, `web/FRONTEND_LOCK.json`, `src/auditmanager/bootstrap/**`, `src/auditmanager/runs/**`,
`src/auditmanager/workers/**`, `src/auditmanager/executors/**` (the executor-connections line, `EXEC-*`, owns those slots and
paths), `tests/support/**`, any `conftest.py`, `tests/e2e/**`, `web/src/shared/**`, `web/src/_app/providers.tsx`, global styles,
`docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, refs, tags and the stand. The worktree `.local/worktrees/gate-night`
belongs to a running gate: never run anything there or write to it (a `web/node_modules` symlink into it is read-only use through
`npm --prefix web run ...` with `--no-cache`). A change that needs a path outside the allowed list is reported to the integrator
(SendMessage to "main") instead of made.

## Non-goals

No API or contract change; `SeverityBadge` and `SEVERITY_LABELS` are exported from `@/entities/finding` and are reused.
No live journey, no browser, no whole vitest suite (named test directories and the guards only).

## Work

1. `web/src/widgets/decision-history/ui/decision-history.tsx` (~L125-128) and `web/src/widgets/knowledge-base/ui/knowledge-base.tsx`
   print the verdict without `DecisionEvent.severity`: show it with the existing badge when present, nothing when absent;
   legacy markup stays byte-identical for events without a severity.
2. `_pages/review/ui/review-page.tsx`: `pendingIntent` is `'accept'` for any pending verdict: derive it from the pending request
   (accept or reject) so a pending reject says the reject wording.
3. `verdict.result` can leak across finding selection: key or reset it by the selected finding.
4. The severity refusal sentence stays on screen after the expert picks a severity, until the next press: clear it on choice.
5. `features/append-comment` keeps its refusal in a ref (suspected no re-render): confirm with a test and fix.
6. A screen in `web/tests/unit/styles/screens.ts` that renders a v2 finding is optional: add it only if the contrast census
   stays green.
7. Each item: a failing-first vitest and a quoted mutation; Russian copy only, no raw enum value shown.

## Deliverables

The changed web files, the tests, and `docs/program/WEB-REVIEW-FOLLOWUPS-01.md` (decisions taken, commands with exit status, mutations, what was not run).

## Required tests

`npm --prefix web run typecheck`, `npm --prefix web run lint -- --quiet`, and `npm --prefix web test -- --run --no-cache
tests/unit/review tests/unit/decisions tests/unit/widgets tests/unit/entities tests/unit/styles tests/unit/run` plus the guards
`rendered-language`, `prepared-sections`, `presentation-language`, `gender-agreement`, `dashboard-invalidation`, `lazy-boundary`;
one at a time under `nice -n 10`, each redirected to a file with `$?` read from it.

## Integration contract

Merged by the integrator (not by the executor) as a real merge into the integration branch; light acceptance only (`AGENTS.md` §8):
`git diff --check`, the named tests, `tests/contract` with the complete gate's own three ignores. Commit after every solid step; hand
back with a SendMessage to "main" (the report is the last commit).

## Failure/idempotency/security cases

A rerun of a press keeps its idempotency key (the existing rule); nothing is sent when the expert has not chosen a severity.

## Rollback / feature flag

Revert the merge. No flag.
