# W54-CUSTODY-01 — hand-back report

- Task: `docs/program/tasks/W54-CUSTODY-01.md`; grant: `dispatch/W54-PLAN.md` §4 Stage B item 1
  (in `jobs/repository.py` only the D-142 settlement, in `qa_w53/test_queue_and_effect_journal.py`
  only settlement assertions), plus this file.
- Branch `agent/w54-custody-01`, worktree `.local/worktrees/w54-custody`, base `196a8d6`
  (`integration/w54`, Stage A merged). Implementation commit `20c8f91`; this report is the next commit.
- Checks follow `R-102` (light acceptance). **No container was started.** Every database- or
  S3-backed test is written and listed in §5 for the owner's window.

## 1. Changed files

`git diff --name-only 196a8d6..HEAD` lists 27 paths plus this report:

- **New custody context** — `src/auditmanager/norms/custody/{__init__,errors,model,repository,roles,service}.py`
  and `src/auditmanager/norms/public.py` (the context's cross-context surface; `norms/__init__.py` untouched).
- **Storage** — `storage/blob_repository.py` (D-146), `storage/s3.py` (R-76 reuse checks),
  `storage/public.py` (exports custody needs), `storage/models.py` and `storage/errors.py`
  (docstrings only), `storage/README.md`.
- **Ingest** — `ingest/reconciliation.py` (custody and settled intents attribute their blobs;
  `reject_unpublished` custody refusal).
- **Jobs** — `jobs/repository.py`: one SQL constant `_SETTLE_TERMINAL_ARTIFACT_PUBLICATIONS`, one
  method `settle_terminal_artifact_publications`, and one call to it at the end of
  `settle_terminal_provider_effects` (D-142). Nothing else in the file changed.
- **Deploy prose** — `infra/deploy/object_attrs.py` (docstring), `infra/deploy/reset.sh` (the
  role rationale comment and the sidecar refusal's last two message lines; every guard is
  unchanged), `tests/integration/composition/test_reset_script_refusals.py` (one docstring).
- **Tests** — new `tests/integration/norms/custody/{conftest,test_two_phase_custody,test_custody_offline}.py`,
  `tests/integration/ingest/test_reconciliation_custody_blobs.py`,
  `tests/integration/storage/test_publish_reuse_checks_offline.py`; extended
  `tests/integration/ingest/test_blob_metadata.py` (D-146),
  `tests/integration/runs/test_durable_effect_boundaries.py` (D-142, two tests appended after the
  C-12 test), `tests/integration/qa_w53/test_queue_and_effect_journal.py` (three small hunks in
  `test_terminal_effect_settlement_journals_abandonment` plus one import line),
  `tests/integration/storage/test_repeated_publication.py` (the role test inverted, one test added).

### What was built (plan §3.1)

- **Phase one, admission** — `admit(session, request, manifest=...)` appends one `pending`
  `norm_custody_admission` (`nad`) in the caller's transaction, with a `norm_custody.admitted`
  event. The target need not exist. It refuses **before any statement** if any of these holds:
  - the role, target identity, anchor kind, anchor, media type or content is malformed;
  - the slot is absent from the verified manifest, or the manifest declares other content.

  It refuses **before any write** if any of these holds:
  - a live admission holds the slot with other content: `idempotency_key_reuse`,
    `command_type norm_custody.admit`;
  - the Blob row is `rejected`: D-143, `state_transition_not_allowed`, and the message names D-143;
  - the Blob row has another media type: `conflict`, `conflict_reason media_type_conflict`.

  Same slot and same content replays and writes nothing. A concurrent winner of the partial
  unique index is re-read.
- **Phase one, dispatch** — `CustodyDispatcher(store, source=..., session_factory=...).dispatch(until_idle=True)`
  runs in three transactions per admission.
  1. Claim the admission (`FOR UPDATE SKIP LOCKED`), take the D-146 per-blob lock, check the Blob
     row, and record it `temporary`.
  2. Stage the bytes under the admission's own `nad` as upload token, read them back, and record
     them `verifying`.
  3. Publish canonically. Then, in one transaction, lock the admission, mark the Blob `available`,
     mark the admission `confirmed`, and write the `norm_custody.confirmed` event.

  An `available`, matching Blob is reused without uploading. The reuse comes only after the
  object's recorded SHA-256, size and media type are checked.

  The outcomes split two ways:
  - **Rejected admission.** A byte mismatch, a media-type conflict, an unverifiable or missing
    object, or a `rejected` Blob (D-143) rejects the *admission*. The Blob row is never
    rejected, and the slot is free for a corrected admission with a new `nad`.
  - **Failed try.** A store outage, a lost staged upload or an unreadable source counts one try,
    rescheduled at 30 s, 5 min, 30 min and 2 h. The fifth failed try leaves the admission
    `poisoned`.

  Any other exception counts one try and is re-raised. `requeue(session, ids)` returns a
  `poisoned` admission to `pending` with a fresh count.
- **Five interruption points** (checkpoint names): `admitted`, `blob_declared`,
  `temporary_staged`, `blob_verifying`, `object_published`. From each, a later dispatch converges
  to one Blob row, one canonical object, no temporary object and no binding.
- **Phase two** — `publish_bindings(session, role, targets)` runs in the target transaction. It
  refuses before any write if any of these holds:
  - a named target is absent now (invariant 4 at publication time);
  - a non-rejected admission of those targets is not `confirmed`;
  - a Blob is not `available` with the declared facts.

  Otherwise it inserts one binding per admission (`nbd`, `ON CONFLICT (admission) DO NOTHING`),
  each with a `norm_custody.bound` event. An exact replay reports `already_bound`.
  `trg_norm_custody_binding_guard` stays the database backstop.
- **Report / reconcile** — `report(session, role=None, targets=None)` is read-only and lists:
  - state counts;
  - poisoned and rejected admissions;
  - confirmed admissions that are still unbound;
  - the binding count and `binding_digest`, a SHA-256 over sorted lines of (role, target kind,
    target, `blob_id`, anchor kind, anchor), exported for BUNDLE;
  - every `rejected` Blob row with whether custody names it (D-143).

  `CustodyReconciler.reconcile()` point-inspects each confirmed admission's object. It reports
  `object_missing`, `object_unverifiable`, `object_metadata_differs` and `blob_row_not_available`
  as incidents and repairs nothing.
- **R-76 in storage** — `S3BlobStore.publish` no longer compares the role. Equal bytes under
  another role reuse the blob, and the object keeps the first publisher's `blob-role` as history.
  An existing object is refused rather than reused in three cases:
  - no recorded SHA-256: `BlobMetadataInvalidError`;
  - another recorded SHA-256 or size: `ChecksumMismatchError` or `SizeMismatchError`;
  - another media type: `BlobAttributeConflictError`.
- **D-146** — every `BlobMetadataRepository` write takes
  `pg_advisory_xact_lock(hashtextextended('auditmanager.blob|' || blob_id, 0))` through the public
  `lock()`. `record_declared` inserts `ON CONFLICT (blob_id) DO NOTHING`, then re-reads and compares.
- **D-142** — `settle_terminal_provider_effects` also settles `prepared` artifact intents whose
  Attempt is terminal: they move `prepared → abandoned` with `abandoned_at`, under the same
  `older_than` and `batch_size`. It journals `artifact.abandoned` (aggregate `Attempt`, payload
  `attempt_id`, `stage_id`, `state`) and never touches the blob row. The ingest sweep treats any
  analysis intent (now including `abandoned`) and any custody admission as an owner.

### The eight cases and where each is proved

| Case | Test |
|---|---|
| admission before the target, binding with it | `norms/custody/test_two_phase_custody.py::test_admission_precedes_its_target_and_binds_in_the_targets_transaction` |
| an orphaned admission stays unbound | `…::test_an_orphaned_admission_stays_unbound_and_reported` (app refusal and the trigger's own refusal), `…::test_a_binding_is_refused_while_an_admission_of_the_target_is_not_confirmed` |
| double admission a no-op | `…::test_double_admission_dispatch_and_publication_are_no_ops` |
| equal bytes under two roles | `…::test_a_project_upload_reuses_bytes_custody_published_under_its_own_role`, `…::test_custody_reuses_bytes_a_project_upload_holds_without_rewriting_them` (out-of-band witness), `…::test_equal_bytes_at_two_anchors_share_one_blob`; `storage/test_repeated_publication.py::test_republishing_under_a_different_role_reuses_the_blob` |
| a media-type conflict | `…::test_a_media_type_conflict_is_refused_at_admission`, `…::test_a_media_type_conflict_found_at_dispatch_rejects_the_admission_not_the_blob` |
| two concurrent declarers (D-146) | `ingest/test_blob_metadata.py::test_two_concurrent_declarers_of_equal_bytes_serialise_and_both_succeed` (the wait is observed in `pg_stat_activity`), `…::test_a_declarer_that_skips_the_lock_still_cannot_collide` |
| D-142 settlement and event | `runs/test_durable_effect_boundaries.py::test_d142_a_crashed_publication_is_settled_and_the_report_is_clean_after_a_rerun`, `…::test_d142_settlement_leaves_a_live_attempts_intent_prepared`, `qa_w53/test_queue_and_effect_journal.py::test_terminal_effect_settlement_journals_abandonment` |
| D-143 report and refusal | `…::test_d143_bytes_of_a_rejected_blob_are_refused_at_admission_and_reported`, `…::test_d143_a_blob_rejected_after_admission_rejects_the_admission_at_dispatch` |

Further cases:

- The five interruption points are `…::test_a_process_lost_at_each_interruption_point_converges`,
  parametrised five ways.
- A byte mismatch rejects the admission only: `…::test_bytes_that_differ_from_the_admission_reject_the_admission_only`.
- Five tries, then poisoned, then requeue: `…::test_five_failed_tries_poison_an_admission_and_requeue_returns_it`,
  which asserts the 30/300/1800/7200 s schedule.
- Reconcile: `…::test_reconcile_reports_a_bound_admission_whose_object_vanished`.
- The ingest sweep and custody blobs: `ingest/test_reconciliation_custody_blobs.py`.
- An unverifiable object is refused: `storage/test_repeated_publication.py::test_an_existing_object_without_a_recorded_digest_is_refused_not_reused`.

## 2. Checks run, with commands and results

All on `20c8f91` with a clean tree, unless stated otherwise.

| Command | Result |
|---|---|
| `git diff --check 196a8d6..HEAD` | clean |
| `.venv/bin/python -m compileall -q src/auditmanager/{norms,storage,ingest,jobs} infra/deploy/object_attrs.py` and every changed test package | exit 0 |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | **554 passed**, 50 subtests (baseline at `196a8d6`: 554 passed). The ALR-05 guard `architecture/test_alr05_boundaries.py` passes: custody imports only `storage.public` and `shared`. While the tree was dirty, `test_alpha_acceptance_command.py` failed as SEAL documented; on the clean tree it passes. |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/architecture tests/integration/norms/custody/test_custody_offline.py tests/integration/storage/test_publish_reuse_checks_offline.py tests/integration/composition/test_reset_script_refusals.py` | **82 passed** (container-free) |
| Mutation: the role mirror test, with `anchor_kinds` widened to `{"pdf","crop","page"}` in `roles.py` | `test_the_role_table_mirrors_the_migrations_role_shape_check` **failed**; restored with `git checkout -- …roles.py` and the tree verified clean |
| Mutation: `src/auditmanager/storage/s3.py` replaced by `git show 196a8d6:…/s3.py`, then restored with `cmp` | 4 of 5 offline reuse tests **fail** on base: role reuse, no digest, other digest, other length. The media-type control passes on both. |
| `shellcheck infra/deploy/reset.sh` | the findings are identical to base `196a8d6` (compared after stripping line numbers); none are new |
| ruff 0.17.0, an unpacked wheel in the session scratchpad (no venv change): `ruff check --isolated --select E4,E7,E9,F` on every changed Python file | `All checks passed!` |
| SQL syntax: every `text()` constant of `norms/custody/repository.py`, `jobs/repository.py`, `storage/blob_repository.py` and `ingest/reconciliation.py`, plus the dynamic target query, rendered with `$n` and parsed by pglast 8.5 (libpg_query) | **63/63 parse**. A deliberately broken statement fails, so the check can fail. This proves syntax only, not column names or semantics. |

**Not run (heavy, window only):** every test needing PostgreSQL or S3 (§5). I checked the column
names by hand against `0012`, `0014` and `0018`. Each new database test was written to fail on base
code, and the failing assertion is named in its docstring or its first assertion. This was
reasoned, **not measured**: the window run is the first measurement.

## 3. Contracts

**None changed.** There is no edit under `contracts/**` and no migration. The schema `0018` that
SEAL sealed was sufficient, with no gap found. Everything here uses existing catalog codes and
their safe detail keys only:

- `validation_failed`;
- `idempotency_key_reuse`;
- `conflict` with `conflict_reason`;
- `state_transition_not_allowed`;
- `storage_integrity_error`;
- `not_found`.

New in-code surfaces that are not wire contracts:

- the `auditmanager.norms.public` module;
- the `audit_event` types `norm_custody.{admitted,confirmed,rejected,try_failed,poisoned,requeued,bound}`
  (the copy-record fingerprint excludes this family, plan §3.5) and `artifact.abandoned`;
- `last_failure` classifiers: the store's error code, `storage_integrity_error`,
  `media_type_conflict`, `object_unverifiable`, `canonical_object_missing`,
  `blob_rejected_d143`, `blob_not_publishable`, `source_unavailable`, `internal_error`. Each
  is checked against `ck_norm_custody_admission_failure`.

`BlobAttributeConflictError`'s summary is unchanged. Only its docstring narrowed to media type.

## 4. Risks and known limitations

- **No database or S3 ran.** The suite in §5 is unexecuted. A semantic SQL error, such as a type
  inference on a NULL array parameter, would surface first in the window. Every array parameter is
  an explicit `CAST(... AS text[])`.
- **No custody CLI.** The operator verbs are a Python API. `W54-BUNDLE` owns
  `python -m auditmanager.norms.bundle` (TRANSPORT's fixed module command), so it wires `admit`,
  `dispatch --until-idle`, `report`, `reconcile`, `requeue` and `publish_bindings`, and implements
  `CustodyManifest` and `CustodySource` over the verified bundle.
- **The dispatcher holds no claim lease.** Two concurrent dispatchers may both stage one admission.
  They use the same upload token, publication is idempotent, and confirmation is guarded, so they
  converge. The losing one can record a `staged_upload_lost` try. The stand's import lock prevents
  parallel importers.
- **An `available` Blob whose canonical object is absent** rejects the admission with
  `canonical_object_missing` (fail closed). It is not re-published.
- **D-142 settles by Attempt state only.** A `prepared` intent of a terminal Attempt can never be
  bound, because `bind_artifacts` requires current authority. The settlement count is returned by
  `settle_terminal_artifact_publications` and journalled. It is not added to
  `runs.ReconciliationReport`, because `runs/reconciliation.py` is outside this grant.
- **The ingest sweep after D-142.** An unsettled Blob row named only by an `abandoned` intent is no
  longer listed as unattributed. It is attributed to that intent, and a rerun of the version
  publishes it. Until such a rerun, the row stays `temporary` or `verifying` without a report line.
- **Shared database.** Database cases in `runs` and `qa_w53` scope their assertions to their own
  runs because those modules share one database. `report().is_clean` is asserted per run, not
  globally.
- **Web journal labels.** `web/src/entities/execution/model/presentation.ts` has no label for
  `artifact.abandoned`. The journal shows the raw type until a web lane adds one.
- **Debt register (integrator-owned).** The code halves of D-142, D-143 and D-146 are closed, and
  each row's check command still applies. D-143 stays open until P2's copy record measures the
  stand's `rejected` count.

## 5. Integrator instructions

1. Read the diff and this report, then merge `agent/w54-custody-01` (Stage B first; plan §5).
2. To merge alongside `W54-WORKER-01`, take both sides of each shared file:
   - in `jobs/repository.py` this lane adds one SQL constant directly after
     `_SETTLE_TERMINAL_PROVIDER_EFFECTS`, three lines at the end of
     `settle_terminal_provider_effects`, and one method right after it;
   - in `qa_w53/test_queue_and_effect_journal.py` it adds one import line and two hunks inside
     `test_terminal_effect_settlement_journals_abandonment`.
3. **Heavy step, owner window only.** Measure first: `free` must show at least 6 GiB available and
   `df` must show the increment plus 3 GiB free. Bring up this lane's private stack (PostgreSQL
   **57120**, S3 **60720/60721**) with a lane `.env` under its own compose project, then
   `make migrate`. From the worktree:

   ```sh
   set -a; . ./.env; set +a
   P=".venv/bin/python -m pytest -q -p no:cacheprovider"
   $P tests/integration/db/test_norm_custody_migration.py          # SEAL's schema, prerequisite
   $P tests/integration/norms/custody                              # throwaway DB per session
   $P tests/integration/storage
   $P tests/integration/ingest                                     # throwaway DB per session
   $P tests/integration/runs/test_durable_effect_boundaries.py     # FRESHLY migrated database
   $P tests/integration/qa_w53/test_queue_and_effect_journal.py
   $P tests/integration/composition/test_reset_script_refusals.py  # container-free, already green
   ```

   The runs module is not re-runnable on one database (W53C-STORE-01 §4), so give it a freshly
   migrated one.

   For each new case, the base behaviour expected to fail is:
   - D-146 concurrent: a `UniqueViolation` in the second declarer;
   - the lock-skipping declarer: a `UniqueViolation`;
   - the role-reuse tests: `BlobAttributeConflictError`;
   - D-142: the intent stays `prepared`;
   - custody blobs: listed as unattributed and refused as `legacy_unattributed`.
4. Stop the lane stack by its own compose project and kill nothing by pattern.
5. For later lanes:
   - BUNDLE implements `CustodyManifest`/`CustodySource` and computes `binding_digest` from its
     manifest with the exported function;
   - REPAIR, SNAPSHOT, EMBED and BUNDLE append their export lines to `norms/public.py` in plan §6
     order;
   - W57a adds roles in `norms/custody/roles.py` together with its CHECK replacement. The mirror
     test reddens if only one side changes.

## 6. Containment

- `git diff --name-only 196a8d6..HEAD` lists the 27 paths of §1 plus this report. Every path is
  inside the §4 Stage B item 1 grant, and `tests/integration/ingest/test_reconciliation_custody_blobs.py`
  matches `test_reconciliation*`.
- Not touched:
  - `contracts/**` and `db/migrations/**`;
  - `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, `NORM_CORPUS_CUSTODY.md` (SEAL's);
  - `norms/__init__.py`;
  - root dependency and lock files, the composition root and `runs/reconciliation.py`;
  - refs, tags, the stand, `.local/norms/**` and other worktrees.
- No container was started. There was no push, merge, tag, stash or worktree creation, and no kill.
  `git status --porcelain -uall` is empty after this commit.
