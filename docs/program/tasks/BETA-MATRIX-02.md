# Task BETA-MATRIX-02 — the static coverage matrix B1-B12 refreshed to the current tree

task_id: BETA-MATRIX-02

## Outcome

`docs/program/BETA-MATRIX-02.md` restates the static B1-B12 matrix against the tree `origin/dev` now, with every cited path and
test name read on that tree, replacing the stale claims of `BETA-MATRIX-01.md` that a survey found (B9 and B12 are no longer
`NEEDS-CODE`; versions, heads and counts moved). It sets no PASS: it separates what code and tests prove from what needs a
stand, an expert, real documents, a policy or a publication.

## Depends on

- `BETA-MATRIX-01` — completed (the document this one refreshes).

## Frozen inputs

- base: `origin/dev` at the freeze commit of this file (parent `51b1ed43`);
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

- `docs/program/BETA-MATRIX-02.md` (new)
- `docs/program/tasks/BETA-MATRIX-02.md`

## Lane resources

- container-free until the integrator says the host gate has ended; reserved and unused: foundation_instance `auditmanager-lane-f`,
  postgres_port `57662`, s3_api_port `61464`

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

Documentation only: no code, no test, no register or CURRENT_STATE edit (they are the integrator's). No run of any suite: paths
and names are verified by reading and `grep`/`ls`, and anything not seen is marked UNVERIFIED.

## Work

1. Read `docs/program/BETA-MATRIX-01.md`, `docs/program/dispatch/CODE-FIRST-TO-BETA.md` section 3 and `docs/program/CURRENT_STATE.md`.
2. Measure on the tree, quoting the command: API surface and error-code count (`tests/support/expected_facts.json`), migration head,
   `VERSION`, `contracts/api/v1/openapi.json` info.version and `contracts/domain/v1/error-codes.json` status/revision, the PC-01
   journey manifest's step count, release notes files, section profiles and recordings present.
3. Per criterion B1-B12 give the verdict class used by `BETA-MATRIX-01` (READY-TO-ACCEPT-ON-STAND, NEEDS-CODE, DEFERRED-BY-OWNER),
   the code and tests that exist (path and test names), and what is missing and why. B9: sealed `1.0.0`? B12: which menu
   destinations have a journey step; list any without.
4. A section 'What changed since BETA-MATRIX-01' listing each stale claim with its old and new value.
5. A final table of what the owner/stand must still do (copy from BETA-MATRIX-01 and update, e.g. `0.5.1` history row, tag `v0.7.0`).

## Deliverables

`docs/program/BETA-MATRIX-02.md`, one commit.

## Required tests

`git diff --check`; `python3 -m pytest -q tests/contract/program` (container-free, under `nice -n 10`).

## Integration contract

Merged by the integrator (not by the executor) as a real merge into the integration branch; light acceptance only (`AGENTS.md` §8):
`git diff --check`, the named tests, `tests/contract` with the complete gate's own three ignores. Commit after every solid step; hand
back with a SendMessage to "main" (the report is the last commit).

## Failure/idempotency/security cases

A claim you cannot verify on the tree is written UNVERIFIED, never copied forward.

## Rollback / feature flag

Revert the merge. No flag.
