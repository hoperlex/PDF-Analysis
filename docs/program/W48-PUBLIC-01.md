# W48-PUBLIC-01 — completion report

## Result

**DONE.** Every backend cross-context import on frozen base
`3d5f322408aec9c54f5638dddcd459f2463b64ce` now targets exactly
`auditmanager.<context>.public`. The frozen P-01 AST command moved from
`18 deep / 24 package-root` to **`0 deep / 0 package-root`** without changing a runtime
operation, contract, migration or stored value.

The implementation commit is `b224bc7ef31c500c25bad526ea8a3225547116ba`. This report is
committed afterwards and the full gate is repeated on that final report tip; the literal
`GATE OK` and exact final SHA belong to the executor handoff because a commit cannot contain
the result of a gate run on itself.

## Changed files

### Exact public surfaces

- `src/auditmanager/storage/public.py` — the twelve storage symbols consumed by P-01;
- `src/auditmanager/bootstrap/public.py` — `Application`, `AppSettings`,
  `ConfigurationError`, `build_application`;
- `src/auditmanager/documents/public.py` — the ten document symbols consumed by P-01;
- `src/auditmanager/findings/public.py` — the ten findings symbols consumed by P-01;
- `src/auditmanager/analysis/public.py` — retained its existing surface and added only the
  seventeen analysis symbols consumed by the P-01 importers;
- `src/auditmanager/ingest/public.py` — `CommandReplay`, `CommandRepository`,
  `CommandStarted`, `payload_fingerprint`;
- `src/auditmanager/jobs/public.py` — `AttemptAuthority`, `JobRepository`,
  `SettledProviderEffect`, `UnresolvedProviderEffect`;
- `src/auditmanager/runs/public.py` — `reconcile_at_startup`.

### Import lines only

The only edits to existing implementation modules are import targets in the 21 importers
enumerated by frozen premise P-01:

- `src/auditmanager/analysis/engine/runner.py`;
- `src/auditmanager/analysis/ports/artifacts.py`;
- `src/auditmanager/analysis/ports/stage.py`;
- `src/auditmanager/analysis/stages/page_geometry_extraction.py`;
- `src/auditmanager/api/app.py`;
- `src/auditmanager/api/composition.py`;
- `src/auditmanager/api/routers/errors.py`;
- `src/auditmanager/dashboard/repository.py`;
- `src/auditmanager/decisions/ledger.py`;
- `src/auditmanager/documents/models.py`;
- `src/auditmanager/documents/repository.py`;
- `src/auditmanager/ingest/commands.py`;
- `src/auditmanager/ingest/failures.py`;
- `src/auditmanager/ingest/reconciliation.py`;
- `src/auditmanager/ingest/service.py`;
- `src/auditmanager/jobs/repository.py`;
- `src/auditmanager/norms/__main__.py`;
- `src/auditmanager/runs/carrier.py`;
- `src/auditmanager/runs/commands.py`;
- `src/auditmanager/runs/executor.py`;
- `src/auditmanager/runs/reconciliation.py`.

### Guard and records

- `tests/contract/architecture/test_alr05_boundaries.py` — AST enforcement for absolute and
  relative imports, including imports guarded by `TYPE_CHECKING`;
- `docs/architecture/ARCHITECTURE_LINT_RULES.md` — one enforcement sentence naming the guard;
- `docs/program/W48-PUBLIC-01.md` — this report.

## Verification

The lane was `gate-w48public`: PostgreSQL `56490`, S3 `60090/60091`, reserved API `56491`
and reserved Next `56493`. The ignored real corpus was linked read-only from the main checkout.

- `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` — **PASS**;
- `npm --prefix web ci` — **PASS**, 184 packages;
- frozen P-01 AST command from the task — **`COUNTS 0 0`**;
- `.venv/bin/python -m pytest tests/contract/architecture/test_alr05_boundaries.py -q` —
  **1 passed**;
- import smoke over all eight public modules — **PASS**; the new `__all__` sets equal the
  consumed-symbol inventories and no import cycle occurred;
- `.venv/bin/python -m pytest tests/contract
  --ignore=tests/contract/test_cp00_candidate.py
  --ignore=tests/contract/test_cp00_final_state.py
  --ignore=tests/contract/test_validate_bootstrap.py -q` — **440 passed, 49 subtests passed**;
- `git diff --check 3d5f322408aec9c54f5638dddcd459f2463b64ce..b224bc7` — **PASS**.

The task's literal `.venv/bin/python -m pytest tests/contract -q` is reported honestly as
**inherited RED**, not as a pass: **66 failed, 602 passed, 126 errors, 452 subtests passed**.
The three programme-quarantined CP-00/bootstrap modules remain red, and the linked worktree
still presents `.git` as a file while legacy CP-00 tests call `shutil.copytree` on it as a
directory. The additional passing test relative to the preceding lane is this task's ALR-05
guard. No quarantine or legacy test was changed.

The first full `make gate` on clean implementation commit `b224bc7` was diagnostic RED after
the lane's S3 container restarted during the long battery: foundation was **35 passed**, then
the backend ended **1 failed, 2713 passed, 5 skipped, 15 errors, 297 subtests passed**, with
all sixteen red cases reporting `StorageUnavailableError`. The exact failed scope was re-run
against the restored healthy lane and passed **24/24** with three existing SQLAlchemy rollback
warnings. This transient run is retained as a failure and is not represented as gate evidence.

## Mutation evidence

Both mutations ran in separate session-named scratch copies. Each copy first passed the guard
unmodified (**1 passed**) and was removed afterwards.

1. Deep import: `auditmanager.documents.public` was changed to
   `auditmanager.documents.refusals` in the copy of `api/routers/errors.py`. The guard exited
   **1** and reported:

   ```text
   deep src/auditmanager/api/routers/errors.py:41 auditmanager.documents.refusals
   ```

2. Package-root import: the same target was changed to `auditmanager.documents`. The guard
   exited **1** and reported:

   ```text
   package-root src/auditmanager/api/routers/errors.py:41 auditmanager.documents
   ```

No tracked byte in the task worktree was used as a mutation target.

## Contracts and behaviour

No external or wire contract changed. The API remains 17 paths / 20 operations / 61 schemas,
the error catalog remains 22 entries, domain revision remains 8 and the migration head remains
`0014_durable_analysis_effects`. The new modules re-export existing objects by identity; they
define no adapter, fallback, repository abstraction or behaviour.

## Risks and known limitations

- These are internal bounded-context public modules, not a promise of third-party package API
  stability.
- `bootstrap` and `shared` importers retain the exceptions declared by ALR-05; imports *into*
  `shared` remain governed by ALR-07.
- The full literal contract directory still includes the inherited three-file quarantine
  described above. The canonical non-quarantined boundary and `make gate` are the release
  controls; neither was weakened.
- No waiver exists and `docs/architecture/EXCEPTIONS.md` was not touched.

## Integrator instruction

Merge the final `agent/w48-public-01` tip after the durable fix, guards and tails, and before
`W48-JUDGE-Z`. Re-run the ALR-05 AST walk and the merged-candidate gate. Do not copy the ignored
lane environment or corpus link. Rollback is a revert; no feature flag or data repair applies.

## Allowed-path and forbidden-hotspot proof

Before this report, `git diff --name-only
3d5f322408aec9c54f5638dddcd459f2463b64ce..b224bc7` listed **31 paths**: eight public modules,
21 captured P-01 importers, the guard and the one-sentence architecture note. Adding this report
makes 32, all explicitly granted.

The diff contains no `contracts/**`, migration, error catalog, root dependency/lock, generated
client, global style, task file, state/debt/ruling record, waiver, workflow/deploy file or Git
ref change. No merge, push, tag or deployment was performed.
