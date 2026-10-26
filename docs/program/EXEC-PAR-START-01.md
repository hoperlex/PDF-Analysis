# EXEC-PAR-START-01 — a run names its executor

Lane branch `agent/exec-par-start-01`, based on `a3e83f39` (`plan/exec-parallel-runs`). Task:
[`tasks/EXEC-PAR-START-01.md`](tasks/EXEC-PAR-START-01.md). Decisions:
[`EXEC-PAR-DECISION-01.md`](EXEC-PAR-DECISION-01.md). The lane commits to its own branch only; nothing
was merged, pushed or tagged.

`startRun` accepts an optional `executor_connection_id`. Absent, the start is what it was. Present, the
run freezes **that connection's current revision** under the same usability test as a routed primary
(served by this release, probed `ok` on its current key, not archived), or the start is refused before
the key is claimed: no run, no command record, no event. A named connection never becomes the standby
or another connection. `reauditRun` keeps the original run's named connection. `RunStatus` gains a
read-only `executor`. No UI, no migration, no new error code, no new operation.

## Contract

| | before | after |
|---|---|---|
| shared contract version | `1.5.0` | **`1.6.0`** (additive; analysis, domain, events families, served constants, edge bodies, web client) |
| domain catalogue revision | 23 | **24** (no code, identity or machine added) |
| API surface | 92 paths / 104 operations / 300 schemas | **92 / 104 / 301** (one schema: `RunExecutor`) |
| error catalogue / migration head / `VERSION` | 27 / `0032_ar_v3_run_group` / `0.8.1` | unchanged |

* `StartRunRequest.executor_connection_id` — optional, **not nullable** (like `provider_mode`), by
  reference to `ExecutorConnectionId`. `null` and a wrong-shaped id are `422 validation_failed` with
  `details.field: executor_connection_id` (constraint `type` / `pattern`).
* `RunStatus.executor` — optional and nullable (`oneOf [RunExecutor, null]`), read-only.
  `RunExecutor` is closed and has exactly `connection_id`, `display_name`, `pin_id`; the three are the
  frozen revision's connection, that connection's current name and the revision's pinned model. No kind,
  address, key, probe, revision or token. For a run that froze no connection the key is **omitted**
  (as `terminal_at` is), so the status body of such a run -- every run on the `environment` source, and
  every characterization record -- is byte-for-byte unchanged. A run on the `database` source froze a
  revision and now reports it.
  The list item is the same schema (`RunStatusPage.items` is `RunStatus`).
* Refusals reuse existing codes: unknown or malformed id `validation_failed` (`field`, `constraint`
  `unknown_connection` / `pattern` / `kind_not_routable`); a connection that cannot serve now
  `503 dependency_unavailable` with `dependency: executor_connection`.

## Judgement calls the integrator should read

1. **The "reason word" is in the message, not in a detail key.** `dependency_unavailable` declares
   `safe_detail_keys: ["dependency"]` only, and `screen_details` raises on any other key. Adding a
   `reason` key is a change to the error catalogue (not "no new error code", and beyond this slice), so
   the word travels in the screened message — `the chosen executor connection cannot serve a run now
   (archived | kind_not_served | not_probed | no_revision)` — and `details` is `{dependency:
   executor_connection}`. If the screen should read the reason mechanically, that is a catalogue change
   for its owner.
2. **The repeat learns "was it explicit?" from the journal.** The run row holds only the frozen revision,
   which a routed run has too, and no migration is allowed. So a named start writes one
   `audit_run.executor_chosen` event (`connection_id`, `revision_id`; both already in the journal
   allowlist, so `jobs/events.py` is untouched) and `reaudit_run` reads it
   (`RunRepository.chosen_executor_connection`, indexed by `(aggregate_type, aggregate_id)`). The repeat
   writes the same event for the new run, so a repeat of a repeat keeps the executor. The repeat takes
   the connection's **current** revision (R-82: today's configuration), not the source's revision.
3. **Classification of the event.** The name sits under the existing PRODUCT prefix `audit_run.`, so
   `scripts/recovery/product_purge.py` already classifies it (its `event-types-classified` guard stops on
   an unclassified type, and this one is classified); the file is untouched. A unit test pins the event
   as PRODUCT and not KEEP. There is no other event registry in the tree; the only other list of event
   types is the web label map `web/src/entities/execution/model/presentation.ts` (forbidden here, owned by
   `EXEC-PAR-WEB-01`), which renders an unknown type as «Другое событие выполнения» — as it already does
   for `audit_run.standby_used`.
4. **A named executor with no freezer is refused.** On the `environment` source (`providers.freeze is
   None`) a named connection, or a repeat of a named run, is `dependency_unavailable`
   (`executor_connection`) instead of running on the process's own adapter. A *replay* of an accepted key
   is still answered, whatever this process serves.
5. **The freezer is checked, not trusted.** `_freeze_for` raises `ValueError` before anything is written
   if a freezer answers a connection other than the one asked for (a wiring fault, not a fallback).
6. **Fingerprint.** `start_run_fingerprint(..., executor_connection_id=None)` adds the key only when
   named; an absent choice reproduces the literal captured from the base tree
   (`62bde5d8d311…fb7f061`, re-computed from `a3e83f39:src/auditmanager/runs/commands.py`). The re-audit
   fingerprint is unchanged (source run + stored digest): the source determines the executor.
7. **Observation, not changed:** `RevisionSettings.allow_client_documents` is stored but read nowhere in
   `src/` (neither the route nor a named choice enforces it). Out of scope; noted for the owner.
8. **Bare-wiring caveat.** `reaudit_run` consults the journal inside its existing "new key" block, which
   is entered when a budget, a section table or a freezer is passed. The served path always passes the
   budget (`test_the_served_application_always_passes_a_budget`); only a test that passes none of the
   three skips the check.

## Changed files and why (paths beyond the task's core list marked ◆)

Commits (oldest first): `d81a14f3` OpenAPI content · `53a9b0f4` serving code and tests · `659fadab`
infra text only · `8c1d3863` seal · `a0c8306f` 422 mapping test · `949f8d41` revert of one unneeded
edit · plus the docs commit holding this note.

| Path | Reason |
|---|---|
| `contracts/api/v1/openapi.json` (+ `web/openapi/openapi.json` mirror) | the contract change; content commit `d81a14f3` is what `FRONTEND_LOCK.json` names |
| `contracts/{analysis,domain,events}/v1/**` (30 JSON files), `contracts/domain/v1/README.md`, `contracts/api/v1/README.md` | version stamp `1.5.0 → 1.6.0`, `supersedes 1.5.0`, catalogue revision 24 (`test_contract_seal`) |
| `src/auditmanager/executors/resolver.py`, `queries.py`, `public.py` | `freeze_connection(connection_id=)`, `chosen_unusable`, `executor_of_revision` / `RunExecutor` (runtime.py needed no change) |
| `src/auditmanager/runs/commands.py` | start/reaudit command, fingerprint, journal |
| ◆ `src/auditmanager/runs/provider.py`, `runs/repository.py` | run-start files under `runs/`: `FrozenRoute.chosen_connection_id`, `RouteFreezer` protocol; the choice-event reader |
| `src/auditmanager/bootstrap/providers.py` | the `freeze` seam only |
| ◆ `src/auditmanager/bootstrap/adapters.py` | `RunAdapter.start_run` passes the choice; `_run_status_view` fills `executor` (the only place that joins runs and executors). Not `composition.py` |
| `src/auditmanager/api/routers/runs.py`, ◆ `ports.py`, ◆ `api/schemas/models.py`, ◆ `api/schemas/runs.py` | the `api/**` files that map `StartRunRequest` and `RunStatus` |
| ◆ `src/auditmanager/api/routers/__init__.py`, `analysis/engine/result.py`, `api/schemas/models.py` (`ErrorEnvelope`) | `CONTRACT_VERSION` constants — red when reverted: `test_the_application_constants_are_the_sealed_version` |
| ◆ `src/auditmanager/api/app.py` (line 477), `api/routers/declarations.py` | schema count in prose — red when reverted: `test_the_api_prose_states_the_surface_this_document_declares`. (`app.py` line 172, "299 models" → "300", is read by no guard; kept so the sentence stays true) |
| ◆ `docs/program/ALPHA_ROADMAP.md` | live doc scanned for the surface triple — red when reverted: `test_the_scanned_docs_state_the_contract_surface_this_tree_has` |
| `infra/deploy/proxy/nginx.conf`, `tls-server.conf` | version literal only, alone in commit `659fadab` — red when reverted: `test_the_edge_answers_its_own_error_bodies_with_the_sealed_version` |
| ◆ `web/src/shared/api/credentialed-forward.ts` | its error body carries the version literal `test_contract_seal` reads |
| `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json` | regenerated by `node web/scripts/generate-api-client.mjs`; lock digests recomputed |
| ◆ `web/tests/**` (44 files) | error-envelope fixtures typed against the generated `ErrorEnvelope` (`contract_version: "1.6.0"`) and two forwarder assertions; mechanical `1.5.0 → 1.6.0`, 53 occurrences. **Not run** (no `node_modules`) |
| ◆ `tests/support/expected_facts.json`, `tests/contract/api_v1/test_contract_seal.py` | independent facts (`RunExecutor`, `1.6.0`), `SEALED/PREVIOUS`, revision 24, stale-version prefixes now include `1.5.0` |
| ◆ `tests/integration/api/conftest.py`, `tests/integration/runs/test_w55a_pin_offline.py` | fake `RunPort.start_run` gains the keyword; the fake run row gains the `connection_revision_id` a real `RunRow` always has |
| new tests | `tests/unit/executors/test_explicit_executor.py` (29), `tests/unit/runs/test_executor_choice.py` (19), `tests/unit/runs/test_run_status_executor.py` (3), `tests/contract/api_v1/test_run_executor_schema.py` (24), `tests/integration/executors/test_explicit_executor.py` (10, database) |
| `docs/program/tasks/EXEC-PAR-START-01.md`, this note | the task file's allowed-path list gains the derived paths above, with reasons |

Measured and **left out**: `runs/v3_cite_stage_contract.py` (its docstring says "stay at 1.5.0"; no guard
reads it — with it on `1.5.0` the whole `tests/contract` tree is green once `CURRENT_STATE` is moved — so
it was reverted in `949f8d41`; the sentence is now stale but harmless), `infra/deploy/README.md`,
`serve.py`, `authorization.ts`, `route.ts` (they state paths/operations, which did not change), and the
three historical comments naming "reseals to 1.5.0" in `tests/integration`.

## Commands and results

All run from the worktree, `nice -n 19`, one at a time. `df -h /`: 3.2 GiB free at start, 2.9 GiB at the
end (floor 1.5 GiB never approached).

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/executors tests/unit/runs` | **505 passed** (base 454; +51 new) |
| `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract --ignore=…cp00_candidate --ignore=…cp00_final_state --ignore=…validate_bootstrap` (literal task command) | **1178 passed, 1 failed** (baseline 1155; +24 new tests minus 1 expected red — see below) |
| same, with `docs/program/CURRENT_STATE.md` temporarily edited to 301 / `1.6.0` (then `git checkout`) | the prose test passes; the only failure is `test_alpha_acceptance_command` ("checkout contains uncommitted changes") — an artefact of the temporary edit; it passes on the clean tree (previous row) |
| `node web/scripts/generate-api-client.mjs --check` | **OK — 104 operations**, sha256 `664a9069…a25af`; `FRONTEND_LOCK.json` digests recomputed, all match |
| `git diff --check a3e83f39..HEAD` | exit 0 |
| count query of the task | `92 104 301`, `info.version` `1.6.0` |

**The one expected red** on the clean tree is `test_the_scanned_docs_state_the_contract_surface_this_tree_has`:
`docs/program/CURRENT_STATE.md` (forbidden hotspot, the integrator's) still says "92 / 104 / 300" and
"shared contract is `1.5.0`".

**Not run, with the reason:** the 10 database tests of `tests/integration/executors/test_explicit_executor.py`
and every other DB/S3-backed test (`DATABASE_URL` is not set for this lane; the suite "never skips" and
errors with that message — verified: 54 of 54 errors in the neighbouring `executors`/`runs` integration
files are exactly that message, 28 offline tests pass); all `web/tests` (no `node_modules`, `npm ci`
forbidden) including `frontend-lock.guard.test.ts`; a typecheck of the web tree. The integration file was
collected (10 tests) and follows the established harness, but it has **never executed**: treat it as
unverified until a database lane runs it.

## Mutation table (each guard shown red once, then restored byte-for-byte)

Restore was `git checkout -- <file>` on committed files; `git status --short` was empty after every row.

| Guard | One mutation | Red |
|---|---|---|
| usability test applies to a named connection | `_why_unusable` check removed | 10: all `cannot_serve_refuses…`, probe-of-earlier-revision, envelope tests |
| no fallback | unusable → `freeze_connection(route)` | 9 (same refusals no longer raise) |
| the route is not read | route resolved before the branch | 12 incl. `a_named_connection_never_reads_the_route` |
| current revision | oldest revision frozen | 2 (`…at_its_current_revision`, earlier-probe) |
| malformed id refused before any read | `parse` removed | 5 `a_malformed_id…` |
| kind serves the work | check removed | 1 `…kind_that_does_not_serve…` |
| unknown vs unusable | unknown → `chosen_unusable` | 5 |
| `explicit` flag | set `False` | 1 |
| seam: no keyword without a name | always passes `connection_id=` | 1 `…makes_the_call_it_always_made` |
| seam: chosen reported / not a standby | `chosen=None`; `primary_connection_id` leaked | 1 / 1 |
| pin reported, not the gateway model | `gateway_model` instead of `pin_id` | 1 |
| fingerprint carries the choice | key dropped | 3 |
| absent choice leaves the fingerprint | key always added | 4 (incl. the base literal) |
| start passes the choice to the ledger | argument dropped | 3 |
| choice journaled | call removed / `revision_id` dropped / reader looks for another type | 1 / 1 / 1 |
| event classified PRODUCT | renamed to `executor.*` (KEEP) | 2 |
| freezer asked for the named one | called without it | 5 |
| wiring-fault guard | removed | 1 |
| named + no freezer refused (start / repeat) | check removed | 1 / 1 |
| refusal before the key is claimed (start / repeat) | freeze moved after `begin` | 2 / 2 |
| repeat keeps the executor | journal read replaced by `None` | 3 |
| repeat journals the choice | call removed | 1 |
| status fills `executor` | assignment removed | 1 |
| absent executor omitted from body | always emits `null` | 2 |
| status uses the run's frozen revision | fixed other revision | 2 |
| nothing secret in the body | body gains `kind` | 1 |
| contract: closed `RunExecutor` | `additionalProperties: true` | 2 |
| contract: request field not nullable | made nullable | 2 |
| contract: `executor` optional | added to `required` | 3 |
| contract: no leak | `base_url` added | 4 |
| contract: null branch | removed | 2 |
| contract: three required | `pin_id` optional | 3 |
| contract: field declared | removed from `StartRunRequest` | 2 |
| model refuses a bad id | `str` instead of the id type | 2 |
| seal: family version | events schema on `1.5.0` | 1 `…only_the_sealed_version[events]` |
| seal: edge | nginx body on `1.5.0` | 1 |
| seal: constants | `CONTRACT_VERSION` on `1.5.0` | 1 |
| seal: catalogue revision | one catalogue on 23 | 1 |
| facts file | `RunExecutor` removed | 5 (conformance and prose-facts) |
| served = frozen | `RunStatus.executor` removed from the model | 1 `test_the_served_document_conforms_to_the_frozen_contract` |
| client = contract | `types.gen.ts` hand-edited | `generate-api-client --check` exit 1 |

## Risks and limits

* The integration file has not run (above). Its expectations are the ones the unit tests prove over
  fakes; what only PostgreSQL shows — the real ledger raising `idempotency_key_reuse`, the event insert,
  the status read over real rows — is unproven here.
* Web tests and the frontend lock guard were not run; the lock digests were recomputed with the same
  algorithm and checked by script, and the generator's own `--check` is green.
* Reason words are message text (judgement call 1).
* `executor.display_name` is the connection's *current* name, so a renamed connection shows its new name
  on old runs. It is a name an administrator chose, shown to every role that can read a run — and every
  role already reads `listExecutorConnections`.
* One query pair per run with a frozen revision on every status read (`get_revision`, `get_connection`);
  a list page of N runs adds up to 2N small reads.

## Integration note

1. Merge this branch, then move `docs/program/CURRENT_STATE.md` to **92 paths / 104 operations / 301
   schemas** and shared contract **`1.6.0`** (line 10; line 3 names `1.5.0` for the pack status read and
   can stay as history). Until then exactly one contract test is red, and it names that file.
2. The `infra/` commit `659fadab` is text only and may be refused only together with moving the same two
   version literals, because `test_contract_seal` reads them.
3. `EXEC-PAR-WEB-01` consumes the regenerated client: `startRun` input `executor_connection_id`,
   `RunStatus.executor` (`RunExecutor`), and the label for `audit_run.executor_chosen` in its own
   `presentation.ts`. `EXEC-PAR-QUEUE-01` may read the run's connection from `audit_run.connection_revision_id`
   (every run on the database source has it) and need not read the event.
4. Re-run on a database lane: `tests/integration/executors/test_explicit_executor.py`,
   `tests/integration/executors/test_http_run_path.py`, `tests/integration/runs/`,
   `tests/integration/api/` (served-application cases, `test_role_register.py`), `tests/integration/composition/`.
5. Rollback: omit the field (behaviour unchanged) or revert the lane's commits; there is no data
   migration, and old `audit_run.executor_chosen` events are product events the purge already removes.
