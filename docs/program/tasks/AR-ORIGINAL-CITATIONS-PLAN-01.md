# Task AR-ORIGINAL-CITATIONS-PLAN-01 — freeze the AR prompt and DB citation implementation slices

task_id: AR-ORIGINAL-CITATIONS-PLAN-01

## Outcome

An implementation plan names the exact changes needed for the served AR analysis to use the reviewed original AR topics and to send canonical normative paragraphs from PostgreSQL to the selected model executor. The plan distinguishes request context from verified citations in a published finding and gives each code slice one owner and measurable acceptance.

## Depends on

- `W56A-LEGACY-SOURCE-01` — completed; the six original AR files and hashes are recorded in `docs/program/W56A-LEGACY-SOURCE-01.md`.

## Frozen inputs

- base commit: local `origin/dev` `7a2270fa` on 2026-10-22; planning worktree `integration/beta-main` has the same tree at start;
- API contract `1.0.0`, 81 paths / 93 operations / 272 schemas, 27 error codes; migration head `0030_executor_connections`;
- original checkout `/root/projects/PDF-proverka` at `16ba8e5d`; `prompts/disciplines/AR/role.md` SHA-256 `fda944f74c4a0bd7cd77339f2c2f8519f55d59e899be03da212f93d2ad432203`, `checklist.md` SHA-256 `eccb7879023a126427fd61a0ed36237eb42bbebd4bec63c4009004247d7f3179`;
- `R-135` code-first development cadence and the accepted `W57-PLAN.md` separation of retrieval, profile, citation grounding and publication.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

The two legacy hashes above are frozen inputs copied from the completed
`W56A-LEGACY-SOURCE-01` report. Their local recheck is recorded in the paired plan
report and is not a precondition on an exact line of the active tree.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/AR-ORIGINAL-CITATIONS-PLAN-01.md`
- `docs/program/AR-ORIGINAL-CITATIONS-PLAN-01.md`

## Forbidden hotspots

Every `src/**`, `web/**`, `contracts/**`, `db/migrations/**`, `infra/**`, root dependency or lock file, composition root, global styles, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, refs, tags and the stand.

## Non-goals

No runtime or prompt change in this planning slice. No normative conclusion from the original checklist's unverified numbers. No model call or deployment.

## Deliverables

The plan report and implementation task boundaries, including which prior W57a preparations can be reused, what database evidence is required, where the Run pins the retrieval set, how failed grounding withholds an observation, checks and ownership of shared hotspots.

## Required tests

- Verify original SHA-256 hashes and the six reviewed-source hashes in `analysis/profiles/ar_v2/content.py`.
- Inspect the served profile registry, Run executor, `norms/public.py`, retrieval-set preparations and the current migration schema.
- `git diff --check` and `python3 -m pytest -q tests/contract/program` on the documentation-only result.

## Integration contract

The integrator uses the report to freeze separate code tasks from a fresh `origin/dev` after the in-flight PDF, EXEC and edge branches are reconciled. Each task owns its own exact paths and frozen counts; no task gets a migration, contract or composition-root slot by implication from this plan.

## Failure/idempotency/security cases

The report must preserve the distinction between untrusted prompt context and canonical evidence. It must require a Run-pinned snapshot/set and fail closed when the database text or its Blob binding cannot be verified. Provider output never becomes an expert decision or alters raw deterministic evidence.

## Rollback / feature flag

Revert the two documentation files; no runtime behavior changes.
