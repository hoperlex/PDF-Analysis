# Task WEB-HOOKS-PER-FINDING-01 — a verdict or comment failure belongs to the finding it was raised for

task_id: WEB-HOOKS-PER-FINDING-01

## Outcome

On the review screen, a press on finding A followed by a switch to finding B no longer shows A's failure, A's pending state or A's
disabled buttons on B: the verdict hook and the comment hook report `error` and `isPending` for the selected finding only (the way
`WEB-REVIEW-FOLLOWUPS-01` already filed `result` and the comment refusal per finding). The `rendered-language` guard also renders the
decision history and the knowledge base with a severity, so the new wording is pinned by the guard and not only by the slice's own
test. Debt `D-201`.

## Depends on

- `WEB-REVIEW-FOLLOWUPS-01` — completed on `agent/web-review-followups-01` and merged into the integration branch this slice starts from.

## Frozen inputs

- base: the integration branch `integration/beta-main` tip at the freeze commit of this file (it contains `integration/beta-1`, lane D and
  lane E; not yet in `origin/dev`);
- migration head `0029_routing_refusal_codes`; API 73/83/242; contract `1.0.0`; this task changes no contract and adds no migration;
- rulings: `R-135`, `R-144d` (no containers and no test batteries on this host while another session's complete gate runs; only
  container-free checks), and the owner's standing order of 2026-10-22 «гони до беты без вопросов».

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

- `web/src/features/record-verdict/**`
- `web/src/features/append-comment/**`
- `web/src/_pages/review/**`
- `web/src/widgets/decision-panel/**`
- `web/tests/unit/{decisions,review}/**`
- `web/tests/guards/**`
- `docs/program/WEB-HOOKS-PER-FINDING-01.md`
- `docs/program/tasks/WEB-HOOKS-PER-FINDING-01.md`

## Lane resources

- container-free: this slice starts no stand and runs no database suite; reserved and unused: foundation_instance
  `auditmanager-lane-h`, postgres_port `57680`, s3_api_port `61480`

## Forbidden hotspots

Every `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency and lock files, `web/src/shared/**`,
`web/src/_app/providers.tsx`, global styles, `tests/**` outside `web/tests/**`, `docs/program/CURRENT_STATE.md`,
`docs/program/DEBT_REGISTER.md`, refs, tags and the stand. The worktree `.local/worktrees/gate-night` belongs to a running gate: never
run anything there or write to it (a `web/node_modules` symlink into it is read-only use through `npm --prefix web run ...` with
`--no-cache`).

## Non-goals

No API change; no new visible wording beyond what the guards already require; no live journey, no browser, no whole vitest suite.

## Work

1. Reproduce first: a test that presses a verdict (or a comment) on finding A, makes it fail, switches to B, and expects B to show no
   failure and enabled buttons; red on the base.
2. Key `error` and `isPending` of `useRecordVerdict` and `useAppendComment` by the finding the request was raised for (the way
   `result` and the refusal already are), without changing the idempotency-key rule.
3. Extend `web/tests/guards/**` `rendered-language` so the history and the knowledge base are rendered with a severity, in the same
   way as the other screens it covers; the guard fails on a Latin word or a raw enum value (quote a mutation).
4. A quoted mutation per new branch; Russian copy only.

## Deliverables

The changed hooks and page wiring, the tests, the extended guard, and `docs/program/WEB-HOOKS-PER-FINDING-01.md`.

## Required tests

`npm --prefix web run typecheck`, `npm --prefix web run lint -- --quiet`, and `npm --prefix web test -- --run --no-cache tests/unit/review
tests/unit/decisions tests/unit/widgets tests/unit/entities tests/unit/styles tests/unit/run` plus the guards `rendered-language`,
`prepared-sections`, `presentation-language`, `gender-agreement`, `dashboard-invalidation`, `lazy-boundary`; one at a time under
`nice -n 10`, each redirected to a file with `$?` read from it.

## Integration contract

Merged by the integrator (not by the executor) as a real merge; light acceptance (`AGENTS.md` §8). Commit after every solid step; hand
back with a SendMessage to "main" (the report is the last commit).

## Failure/idempotency/security cases

A retry keeps its idempotency key; a failure of A is still shown on A when the expert returns to it.

## Rollback / feature flag

Revert the merge. No flag.
