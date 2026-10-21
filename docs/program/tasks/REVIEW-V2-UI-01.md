# Task REVIEW-V2-UI-01 — the reviewer sees and uses the v2 finding fields the API already serves

task_id: REVIEW-V2-UI-01

## Outcome

On a finding that carries them, the review screen shows the proposed severity, lets the
reviewer choose the decided severity when accepting, shows the merged observations, the norm
citations and the required and stated values; a finding without those fields renders and
behaves exactly as before. The accept request carries `severity` only when the finding has a
proposed severity (the decision ledger demands it, `W56A-INT-DECIDED-SEVERITY-01.md`).

## Depends on

- `GATE-REPAIR-01` — completed, merged (`ba6af907`).

## Frozen inputs

- base: `origin/dev` at the freeze commit of this file (parent `ffdc32d1`, `integration/night-1020`);
- migration head `0029_routing_refusal_codes`; API 73/83/242; 27 error codes; contract `1.0.0`
  sealed: this task changes no contract and adds no migration;
- rulings: `R-135` (no complete gate in a lane), `R-126`, and the owner's direct instruction of
  2026-10-22 «гони до беты без вопросов»: a naming or policy choice that is not blocked by a
  recorded owner decision is taken with the default named below and reported, not asked.

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
- `web/src/widgets/decision-panel/**`
- `web/src/widgets/finding-list/**`
- `web/src/widgets/evidence-viewer/**`
- `web/src/entities/finding/**`
- `web/src/entities/expert-decision/**`
- `web/src/_pages/review/**`
- `web/tests/unit/review/**`, `web/tests/unit/decisions/**`, `web/tests/unit/run/**`,
  `web/tests/unit/widgets/**`, `web/tests/unit/entities/**`
- `docs/program/REVIEW-V2-UI-01.md`
- `docs/program/tasks/REVIEW-V2-UI-01.md`

## Lane resources

- container-free: this task starts no stand and runs no database suite (`R-126`); the integrator's
  complete gate runs the database suites on the merged candidate.
- reserved and unused here: foundation_instance `auditmanager-lane-c1`, postgres_port `57623`, s3_api_port `61426`

## Forbidden hotspots

Every `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, `web/package.json`,
`web/package-lock.json`, `web/FRONTEND_LOCK.json`, `web/src/shared/api/**` (the generated client is a
contract artefact), `web/src/shared/styles/**` and every global stylesheet, `web/src/_app/providers.tsx`,
`tests/**` outside `web/tests/unit/**`, `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`,
refs, tags and the stand. New styles go in a `*.module.css` inside the feature or widget that uses them.
The worktree `.local/worktrees/gate-night` and its `node_modules` belong to a running gate: the lane's
`web/node_modules` is a symlink to it that is used READ-ONLY by `npm --prefix web run <script>`; nothing
else is run or written there. A change that needs a path outside the allowed list is reported to the
integrator at once, not made.

## Non-goals

No API or contract change: `AppendDecisionRequest.severity`, `Finding.decided_severity`,
`merged_observations`, `norm_citations`, `required_value`, `stated_value` and
`FindingObservation.proposed_severity` are read from the generated client as they are. No
new dependency. No global style. The live journey is not run (`R-135`).

## Work

1. Read how `use-record-verdict.ts` builds `AppendDecisionRequest` and how the decision panel,
   finding list and evidence viewer receive a finding; use the existing
   `entities/finding/model/severity-labels.ts` (unused until now).
2. Add the severity select to the accept action only when the observation has a non-null
   `proposed_severity`; the reject path never sends it. Show `decided_severity` where the
   verdict is shown, and the merged-observation list, citations and values in the evidence view.
3. All user-visible text is Russian and passes the existing guards (`rendered-language`,
   `prepared-sections`); no raw enum value is shown to the user.
4. Tests failing first, then green: request shape with and without a proposed severity;
   the select is absent without one; labels for all five severities; the evidence rendering.
   Quote a mutation for each new branch.

## Deliverables

The changed web files, the tests and `docs/program/REVIEW-V2-UI-01.md`.

## Required tests

From the worktree: `npm --prefix web run typecheck`, `npm --prefix web run lint -- --quiet`, and
`npm --prefix web test -- --run <the named test directories and guards>`; not the whole suite
(`R-135`). Quote each command and exit status; redirect to a file and read `$?`.

## Integration contract

Merged as a real merge into `integration/night-1020` by the integrator; light acceptance only
(`AGENTS.md` §8): `git diff --check`, the named test files, `tests/contract` with the complete
gate's own three ignores. The slice is closed when its outcome is reachable and its negative case is
tested, with the quoted mutations shown failing.

## Failure/idempotency/security cases

A retry of an accept reuses its idempotency key (the existing rule stays); an accept of a
finding with a proposed severity is not sent without a decided severity.

## Rollback / feature flag

Revert the merge. No flag.
