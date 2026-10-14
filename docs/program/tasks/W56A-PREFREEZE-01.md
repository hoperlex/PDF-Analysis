# Task W56A-PREFREEZE-01 — read-only inventory of W56a freeze inputs

task_id: W56A-PREFREEZE-01

## Outcome

The W56a integrator receives an exact-base inventory of the contract pin sweep, the model
lock and proxy prerequisites, the D-133 state, the legacy АР source location, and the
remaining stop conditions. The inventory distinguishes verified inputs from missing ones;
it does not declare the wave frozen.

## Depends on

- `W55B-RULE-01` — completed.
- `W55B-FIX` — completed and merged into the exact base below.

`W55B-INT-CLOSE` is still pending, so this task reads only the current candidate. It follows
the owner's 2026-10-14 instruction to start available next-wave work during W55b acceptance.

## Frozen inputs

- base commit: `8c5a109bd98302b64fb47b364d4c639ff63c0eda` on `integration/w55b`.
- domain contract: candidate revision 12; `contracts/domain/v1/error-codes.json` SHA-256 `b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16`.
- API contract: 47 paths / 54 operations / 123 schemas; `contracts/api/v1/openapi.json` SHA-256 `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482`.
- analysis contract: `contracts/analysis/v1/stage-registry.json` SHA-256 `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5`.
- migration head: `0021_portal_bundles`.
- governing plan: `docs/program/dispatch/W56-PLAN.md` §A4 on the base; later `W56A-RULE-01` branch `227ac151` is an unmerged document candidate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

### P-01 — the candidate has not closed
- captured_at: 2026-10-14
- command: `git rev-parse integration/w55b; rg --files docs/program | rg 'W55B-INT-CLOSE|W56A-FREEZE-01'`
- captured_output:
  ```text
  8c5a109bd98302b64fb47b364d4c639ff63c0eda
  ```
- exit_status: 1 (the final `rg` found no matching file)
- interpretation: the freeze cannot be issued from this candidate. The inventory is advisory
  and must be refreshed on the eventual accepted W55b SHA.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W56A-PREFREEZE-01.md`
- `docs/program/W56A-PREFREEZE-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies/lockfiles, composition roots, global styles
- `AGENTS.md`, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, plans and port registry
- every W55b worktree/branch/ref, the stand, credentials and private portal exports

## Non-goals

- `W56A-FREEZE-01` itself; owner rulings; contract reseal; implementation; paid model calls;
  tests requiring PostgreSQL, MinIO, Docker or a live gateway.

## Deliverables

- The task file and `docs/program/W56A-PREFREEZE-01.md` with commands, output summaries,
  missing-input findings, and a specific handoff to the W56a freeze owner.

## Required tests

- command: `/root/projects/PDF-Analysis/.venv/bin/python tools/plan/pin_sweep.py reseal-surface migration table error-code`
- expected: exit 0 and a complete advisory path inventory, captured in the report.
- command: `git diff --check` and `git diff --name-only <base>..HEAD`
- expected: exit 0 and exactly the two allowed paths after commit.
- command: manual source-location and model-lock checks quoted in the report.
- expected: each fact has a command and is labelled verified, absent or provisional.

## Integration contract

The freeze owner uses this report as a checklist, reruns every state-dependent command on
the accepted W55b SHA, and resolves missing inputs before issuing `W56A-FREEZE-01`.
It grants no code lane and no migration number by itself.

## Failure/idempotency/security cases

- Missing legacy sources or a failed gateway probe are recorded as stops, never replaced by
  guessed content or model identity.
- No credential is opened or copied. The stand and owner portal export are not accessed.

## Rollback / feature flag

Delete or revert this document-only commit. No runtime behavior or data changes.

## Handoff

- changed files: see Allowed paths.
- commands/results: report §2.
- known limits: report §3.
- integration notes: report §4.
