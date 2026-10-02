# W48-DURABLE-REPAIR — closure of the durable-effects judge escapes

## Result

**DONE for the owned repair slot.** Commit
`0e88589c2b8500c661929646d62bb5cf46b92b3a` closes all three findings in
`W48-DURABLE-JUDGE` without changing the frozen API, error catalog or migration-head identity:

- `DJ-01`: provider response, unknown-outcome and completion transitions now require the stored
  `(run_id, job_id, attempt_id)` to equal the validated current authority; completion also verifies
  that ownership before inserting the immutable model-call evidence;
- `DJ-02`: a validated blob declaration and Attempt-scoped publication intent with a
  database-generated opaque upload token commit before the first S3 write, so a process loss after
  upload remains enumerable and point-inspectable from a new transaction without bucket listing;
- `DJ-03`: the standalone analysis-text module is explicitly replay-only and refuses live mode
  before provider-adapter construction, while the durable Run executor remains the only live path.

This task creates a local repair candidate only. It has no authority over a tag, `origin/dev`,
`origin/main`, deployment or public acceptance, and none was changed.

## Database and runtime invariants

The still-unpublished `0014_durable_analysis_effects` migration was hardened in place under the
inherited migration slot. `model_call` now has a unique `(run_id, model_call_id)` key and
`provider_call_effect` binds `(run_id, final_model_call_id)` to that exact pair. A direct database
write can therefore no longer make one run's completed effect cite another run's model call.

Every provider-effect mutation combines the effect identity, exact run/job/attempt authority and
expected prior state in the write predicate. Completion locks and verifies the effect first, then
inserts the model call and advances the effect in the same transaction. A foreign but otherwise
current authority fails closed, leaves the target effect and model-call table unchanged, and does
not disclose an execution token.

Artifact publication now follows this durable order:

1. validate role, media type, length and SHA-256 and derive the content identity;
2. persist the temporary blob breadcrumb and current Attempt's publication intent, receiving an
   opaque database-generated upload token;
3. upload and verify the exact temporary object addressed by that token;
4. advance the blob checkpoint, publish the canonical object, then bind the publication to the
   stage result under the existing current-Attempt fence.

`Reconciler.report()` uses database identity to issue exact point inspections for temporary and
canonical objects. Its result exposes only presence booleans, never the opaque handle, and it does
not list, adopt or delete objects. A committed crash-boundary regression raises a process-exit
class exception after temporary verification, opens a fresh transaction, and proves that both the
temporary blob row and unbound publication remain discoverable with `temporary_present = true`.

## Changed files

### Migration and runtime

- `db/migrations/versions/20261002_0014_durable_analysis_effects.py`
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/storage/models.py`
- `src/auditmanager/storage/blob_repository.py`
- `src/auditmanager/storage/durable_publication.py`
- `src/auditmanager/storage/port.py`
- `src/auditmanager/storage/s3.py`
- `src/auditmanager/storage/__init__.py`
- `src/auditmanager/storage/README.md`
- `src/auditmanager/runs/executor.py`
- `src/auditmanager/ingest/reconciliation.py`
- `src/auditmanager/analysis/text/__main__.py`

### Tests and invariant seal

- `tests/integration/db/test_durable_analysis_effects.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/integration/runs/test_durable_effect_boundaries.py`
- `tests/integration/ingest/test_blob_metadata.py`
- `tests/integration/storage/test_publication.py`
- `tests/integration/foundation/test_real_providers.py`
- `tests/integration/analysis_text/test_provider_modes.py`

### Programme documentation

- `docs/program/tasks/W48-DURABLE-REPAIR.md`
- `docs/program/W48-DURABLE-REPAIR.md`

## Verification evidence

Focused verification completed before the canonical gate:

```text
analysis mode and governance:                            28 passed
provider modes and standalone CLI:                       15 passed
durable process boundaries:                              11 passed
blob metadata and reconciliation:                        39 passed
schema invariant inventory:                               2 passed
durable schema assertions:                                6 passed, 1 deselected
isolated migration downgrade/upgrade:                     1 passed, 6 deselected
provider/storage-port scope:                             23 passed
governance and documentation prose:                      50 passed
whole-tree port implementation completeness:             12 passed
repaired local-prerequisite regression scope:             69 passed
git diff --check:                                         PASS
```

The schema inventory was resealed from a fresh database at 305 columns, 331 constraints, 76
indexes and 31 triggers. The corresponding digests are recorded in the inventory test. Other
catalog-family totals and seals did not change.

Three full-gate attempts exposed checkout setup rather than product defects and are retained here
instead of being silently discarded:

1. the first stopped before tests because the initial local virtual-environment projection exposed
   only `bin/`, leaving `boto3` unavailable;
2. after correcting that projection, foundation passed 35 tests and the battery reached 2689
   passed, 5 skipped and 297 subtests, but reported 23 setup errors because `.venv/bootstrap` was
   absent and one failure because the ignored local norms-corpus link was absent; the exact
   affected scope passed 69 tests after restoring those checkout prerequisites;
3. the next complete backend run passed 2713 tests, 5 skips and 297 subtests, then gate correctly
   refused to borrow `node_modules` from another checkout. `npm --prefix web ci` installed the
   lockfile-declared dependency set locally; its first sandboxed invocation was blocked from
   executing the downloaded `esbuild` binary and the permitted invocation succeeded. Two later
   invocations were blocked before checks by the sandboxed snap/Docker launcher; no test ran in
   either invocation.

On the unchanged clean implementation commit, the canonical command then completed successfully:

```text
make gate
foundation: 35 passed
backend battery: 2713 passed, 5 skipped, 297 subtests passed
frontend: lint PASS; typecheck PASS; 82 files / 1176 tests passed
whitespace: PASS
GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass
```

The only backend warnings were one upstream Starlette deprecation and three existing SQLAlchemy
transaction-cleanup warnings. The completion-report commit is followed by the same full gate on
the final clean task tree; the implementation-commit result above is not used as a substitute for
that final execution.

## Contracts and limitations

No file under `contracts/**`, no generated client, public route/schema or error-catalog entry
changed. The frozen API remains 17 paths / 20 operations / 61 schemas, and the error catalog
remains 22 entries. The migration head remains `0014_durable_analysis_effects`; no revision was
added and no earlier migration was edited.

Known limitations remain explicit:

1. an organisationally independent durable-effects re-judge is still required; this repair does
   not accept its own candidate and does not close `W48-INT-CLOSE`;
2. provider intent and ambiguous-outcome evidence do not claim provider-side exactly-once
   execution;
3. reconciliation is read-only and performs no production orphan adoption or deletion;
4. the standalone runner provides recorded replay/capture inspection only; live dispatch belongs
   to the durable Run executor;
5. no deployment, public-host check or open-alpha acceptance is part of this repair slot.

## Integration and rollback

A separately assigned judge must inspect the final repair commit, reproduce `DJ-01` through
`DJ-03`, and run its own required evidence before any integration decision. This task must not
create `alpha-w48`, publish `origin/dev`, move `origin/main` or invoke deployment. Any later task
that owns `origin/main` must independently satisfy `docs/program/MAIN_AUTODEPLOY_POLICY.md`, since
that ref is an external deployment action.

Before consumer data exists, rollback is revert of this repair together with the original
unpublished durable candidate. Once durable-effect evidence exists, use forward repair or restore;
the guarded downgrade intentionally refuses to discard populated evidence tables.

## Forbidden-hotspot proof

Relative to base `b43185071af3b315df208245089e27f56fd91f64`, every tracked change is confined
to `W48-DURABLE-REPAIR`'s declared `allowed_paths`. No file under `contracts/**`, no earlier
migration, root/frontend dependency or lock file, composition root, `Makefile`, workflow,
deployment file, authentication code, global style, immutable judge report, `CURRENT_STATE.md`,
`DEBT_REGISTER.md` or unrelated task file changed. The local virtual environment, frontend
modules and norms-corpus link are ignored operator state and are excluded from every commit. No
tag or remote ref was created or moved.
