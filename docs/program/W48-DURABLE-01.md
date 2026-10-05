# W48-DURABLE-01 — durable provider and analysis-blob effects

## Result

**DONE for the owned implementation slot.** The task closes the implementation gaps behind W48
blockers `A-01` and `A-02` without changing the frozen API/domain/error contracts:

- a committed `Job`, current `Attempt`, `Lease` and opaque execution-token authority now exist
  before a production run can perform an external effect;
- every live provider call commits a stable redacted intent before dispatch, checkpoints a
  response before parsing, and leaves an explicit unresolved outcome after an ambiguous failure;
- every analysis artifact is staged and verified, recorded as an attempt-scoped publication
  intent, and only then published; stage result, blob availability and intent binding commit in
  one fenced transaction;
- reconciliation enumerates unresolved provider calls, unbound publications and missing bound
  objects by database breadcrumb and point inspection, without bucket listing or deletion.

The migration head is now `0014_durable_analysis_effects`. This task has no authority over a
remote ref, tag or deployment, and none was changed.

## Database and runtime shape

Migration `20261002_0014_durable_analysis_effects.py` creates five relations:

1. `job` — one durable execution aggregate per run and its current attempt;
2. `attempt` — immutable attempt identity plus secret-class execution token and lifecycle;
3. `lease` — the current attempt's fenced execution authority;
4. `provider_call_effect` — redacted provider intent and response/outcome checkpoints;
5. `analysis_artifact_publication` — attempt-scoped publication intent and eventual binding.

Composite foreign keys prevent cross-wiring a run, job and attempt. Closed state-shape checks,
token/ULID checks, uniqueness constraints and transition triggers reject invalid or backward
state changes. The downgrade is reversible only while these new relations are empty; it refuses
to discard live effect evidence.

`JobRepository` is the sole writer for the new execution/effect tables. PostgreSQL generates the
token and returns it to the caller, so the token is not a SQL bind value. Guarded writes lock the
Job, verify the exact current `(run_id, job_id, attempt_id, execution_token)` tuple, and use
constant-time token comparison. Exceptions and representations do not contain the token.

The provider stage now requires a durable journal for live mode. It commits intent before
`adapter.complete()`, records the response checkpoint before parsing, and writes the existing
immutable `model_call` as part of effect completion. A transport failure after dispatch records
`outcome_unknown`; the same live call is not retried automatically. Recorded provider retries
remain within one durable Attempt.

`DurablePublicationStore` wraps the existing BlobStore sequence as
`stage -> verify -> metadata + intent -> publish`. The executor binds every returned artifact
intent to its stage result and advances blob metadata to `available` in the same current-Attempt
transaction. Temporary objects are discarded on ordinary failures; canonical evidence is never
silently deleted.

## Changed files

### Migration and runtime

- `db/migrations/versions/20261002_0014_durable_analysis_effects.py`
- `src/auditmanager/jobs/__init__.py`
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/jobs/README.md`
- `src/auditmanager/shared/identity/ids.py`
- `src/auditmanager/analysis/text/__init__.py`
- `src/auditmanager/analysis/text/stage.py`
- `src/auditmanager/storage/__init__.py`
- `src/auditmanager/storage/durable_publication.py`
- `src/auditmanager/runs/__init__.py`
- `src/auditmanager/runs/carrier.py`
- `src/auditmanager/runs/executor.py`
- `src/auditmanager/runs/reconciliation.py`
- `src/auditmanager/runs/repository.py` — durability ownership documentation only
- `src/auditmanager/runs/retry.py`
- `src/auditmanager/runs/scope.py`
- `src/auditmanager/ingest/reconciliation.py`

### Tests and invariant seals

- `tests/integration/db/test_durable_analysis_effects.py`
- `tests/integration/db/test_migration_lifecycle.py`
- `tests/integration/db/test_schema_shape.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/integration/runs/test_durable_effect_boundaries.py`
- `tests/integration/runs/test_idempotency_and_topology.py`
- `tests/integration/composition/test_the_run_leaves_the_request_thread.py`
- `tests/integration/shared_kernel/test_topology_guard.py`
- `tests/integration/foundation/test_real_providers.py`
- `tests/integration/ingest/test_reconciliation.py`
- `tests/integration/ingest/test_reconciliation_rules_with_no_guard.py`
- `tests/integration/analysis_text/test_provider_modes.py`
- `tests/integration/analysis_text/test_proxy_truncation_reaches_partial.py`
- `tests/integration/p02_journey/journey.py`
- `tests/contract/domain_p02/test_identifier_catalog.py`
- `tests/contract/domain_p02/test_seam_register.py`
- `tests/contract/api_v1/test_doc_prose_facts.py`

### Programme documentation

- `docs/program/CONTRACT_PIN_REGISTRY.md` — migration-head pin only
- `docs/program/CURRENT_STATE.md` — migration-head claim only
- `docs/manual-tests/PC-01_prototype.md` — migration-head claim only
- `docs/program/P02_SEAMS.md`
- `docs/program/PROTOTYPE_EXECUTION_PLAN.md`
- `docs/program/PROTOTYPE_PROFILE.md`
- `docs/program/tasks/W48-DURABLE-01.md`
- `docs/program/W48-DURABLE-01.md`

## Verification evidence

Focused checks completed on the implementation worktree:

```text
analysis-text, identifier/seam and prose suites:       206 passed
DB lifecycle, exact schema and migration suites:        22 passed
durable faults plus run/ingest reconciliation:           35 passed
complete runs integration suite:                        108 passed
ingest reconciliation suites:                            20 passed
analysis, P02 and exports combined scope:                348 passed
P02 journey after its totality correction:                59 passed
post-gate targeted regression scope:                      24 passed, 244 subtests
git diff --check:                                         PASS
```

The first complete `make gate` attempt reached the canonical battery. Foundation passed
`35 tests`; the battery produced `2696 passed, 5 skipped, 297 subtests` and nine failures. The
failures exposed candidate-state problems rather than accepted exceptions: the deliberately
dirty worktree, stale topology/crash expectations, the new schema-inventory seal, a missing
local norms-corpus link, and temporary objects left by fault injection. The expectations and
seal were corrected, the local corpus source was connected, the four temporary test objects were
removed, and ordinary artifact faults now exercise cleanup rather than simulating an uncatchable
process exit. The 24-test regression scope above covers every corrected failure except the
clean-tree assertion.

Clean implementation candidate `afc6fcb` then completed the full canonical command:

```text
make gate
foundation: 35 passed
backend battery: 2705 passed, 5 skipped, 297 subtests passed
frontend: lint PASS; typecheck PASS; 82 files / 1176 tests passed
whitespace: PASS
GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass
```

The only warnings were one upstream Starlette deprecation and three pre-existing SQLAlchemy
transaction-cleanup warnings. No test was failed or deselected beyond the gate's five recorded
skips. The completion-report commit is followed by the same full gate on the final clean task
tree; a green report does not substitute for that final execution.

## Contracts and limitations

No external contract bytes, API schemas, generated clients or error-catalog entries changed.
The frozen API remains 17 paths / 20 operations / 61 schemas and the frozen error catalog remains
22 entries. This task instantiates the already-frozen Job/Attempt/Lease and attempt-authority
semantics; it changes the internal database head from `0013_norm_embeddings` to
`0014_durable_analysis_effects`.

Known limitations are deliberate task non-goals:

1. there is no distributed scheduler, remote worker, automatic resume or multi-host lease
   protocol;
2. an ambiguous provider outcome is auditable and non-retryable, but cannot be proven
   exactly-once unless the provider offers an idempotency guarantee;
3. reconciliation reports orphan/unbound evidence but does not adopt or delete it;
4. Job, Attempt, Lease and effect journals have no new public API representation;
5. `A-03` cross-context import debt is not changed by this slot.

## Integration and rollback

An independent durable-effects judge should inspect the exact candidate commit, rerun the fault
suite and complete gate, and only then inform a later W48 integration decision. This task must not
create `alpha-w48`, publish `origin/dev`, move `origin/main` or invoke deployment. A later
integration task must separately own the target ref and comply with
`docs/program/MAIN_AUTODEPLOY_POLICY.md` before any `origin/main` action.

Before consumer data exists, rollback is an empty-table migration downgrade followed by a revert
of this task. After any durable effect row exists, downgrade is intentionally refused; rollback
requires restore or a forward repair so audit evidence is not discarded.

## Forbidden-hotspot proof

Relative to the dispatch base, tracked changes are confined to `W48-DURABLE-01`'s declared
`allowed_paths`. No file under `contracts/**`, no prior migration, dependency/lock file,
composition root, API router, authentication code, workflow, global style, deployment state,
credential, immutable audit/judge report or unrelated task brief changed. No tag or remote ref
was created or moved. The local `.venv` convenience symlink and local norms-corpus symlink are
untracked/ignored operator state and are excluded from every commit.

## 2026-10-05 DJ-R2/DJ-R8 scope-compliance addendum

The final paragraph above is not a truthful dispatched-scope proof and is superseded by this
addendum. `W48-DURABLE-JUDGE-2` compared the implementation delta with the two task files as
they existed at dispatch, rather than with later edits to those task files. That audit found
20 product, programme-prose or test paths outside the union of the exact dispatched grants:

```text
docs/manual-tests/PC-01_prototype.md
docs/program/CONTRACT_PIN_REGISTRY.md
docs/program/CURRENT_STATE.md
docs/program/P02_SEAMS.md
docs/program/PROTOTYPE_EXECUTION_PLAN.md
docs/program/PROTOTYPE_PROFILE.md
src/auditmanager/analysis/text/__init__.py
src/auditmanager/runs/__init__.py
src/auditmanager/runs/repository.py
src/auditmanager/shared/identity/ids.py
src/auditmanager/storage/README.md
src/auditmanager/storage/port.py
src/auditmanager/storage/s3.py
tests/contract/api_v1/test_doc_prose_facts.py
tests/contract/domain_p02/test_identifier_catalog.py
tests/contract/domain_p02/test_seam_register.py
tests/integration/composition/test_the_run_leaves_the_request_thread.py
tests/integration/foundation/test_real_providers.py
tests/integration/shared_kernel/test_topology_guard.py
tests/integration/storage/test_publication.py
```

The original implementation task file also changed seven times after dispatch and the repair
task file changed three times after its dispatch. Those in-lane changes cannot retroactively
grant ownership, so neither the file list above nor any later task-file edit is treated as
executor authorization. The paths may contain necessary and technically correct consequences
of the migration and public-port work, but necessity is not a substitute for a dispatched
grant. The W48 integrator must explicitly accept the exact inherited bytes or exclude them from
the candidate; this executor addendum does not make that integration decision.

This correction changes the historical scope/accounting claim only. It does not alter the
recorded implementation or gate measurements, does not rewrite either frozen task file, and
does not assert that the 20 inherited paths are defective. The repair in
`W48-DURABLE-FIX-2` is evaluated solely against its own pre-dispatched allowed paths.
