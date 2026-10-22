# Task WEB-FOLLOWUPS-02 — the benign double POSTs of four features and the price-list upload failure wording

task_id: WEB-FOLLOWUPS-02

## Outcome

A second press while a request is in flight does not send a second POST on
`start-optimisation-pass`, `create-assignment`, `transition-assignment` and
`set-current-snapshot`; the price-list upload names a non-envelope 413 in Russian like the
document upload does, and refreshes what it changed (`D-195`, `D-184` web half).

## Depends on

- `GATE-REPAIR-01` — completed, merged (`ba6af907`).
- `REVIEW-V2-UI-01` is independent; the executor runs it first.

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

- `web/src/features/start-optimisation-pass/**`
- `web/src/features/create-assignment/**`
- `web/src/features/transition-assignment/**`
- `web/src/features/set-current-snapshot/**`
- `web/src/features/upload-price-list/**`
- `web/src/entities/document-version/model/upload-failure.ts`
- `web/tests/unit/optimisation/**`, `web/tests/unit/dispatcher/**`, `web/tests/unit/norms/**`,
  `web/tests/unit/upload/**`
- `docs/program/WEB-FOLLOWUPS-02.md`
- `docs/program/tasks/WEB-FOLLOWUPS-02.md`

## Lane resources

- container-free: this task starts no stand and runs no database suite (`R-126`); the integrator's
  complete gate runs the database suites on the merged candidate.
- reserved and unused here: foundation_instance `auditmanager-lane-c2`, postgres_port `57624`, s3_api_port `61428`

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

No API or contract change; the server already answers a replay or a refusal, this closes only
the client-side double submit. No new dependency. No change to the document upload form beyond
what the shared failure classifier needs.

## Work

1. Read how `web/src/features/upload-document` guards a submit in flight and give the four
   features the same guard in their hooks, keyed by the intent so a deliberate second action
   after the first settled still works.
2. `classifyUploadFailure` (`entities/document-version/model/upload-failure.ts`) is shared:
   extend it only as needed so the price-list upload says a non-envelope 413 in Russian;
   the document upload's tests stay green.
3. `use-upload-price-list.ts` invalidates the queries its result changes.
4. A failing-first vitest per guard and per wording, with a quoted mutation each.

## Deliverables

The changed web files, the tests and `docs/program/WEB-FOLLOWUPS-02.md`.

## Required tests

From the worktree: `npm --prefix web run typecheck`, `npm --prefix web run lint -- --quiet`, and
`npm --prefix web test -- --run web/tests/unit/optimisation web/tests/unit/dispatcher
web/tests/unit/norms web/tests/unit/upload`; each command with its exit status.

## Integration contract

Merged as a real merge into `integration/night-1020` by the integrator; light acceptance only
(`AGENTS.md` §8): `git diff --check`, the named test files, `tests/contract` with the complete
gate's own three ignores. The slice is closed when its outcome is reachable and its negative case is
tested, with the quoted mutations shown failing.

## Failure/idempotency/security cases

Two presses in flight send one POST; a press after the first settled sends a new one.

## Rollback / feature flag

Revert the merge. No flag.
