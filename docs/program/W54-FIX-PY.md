# W54-FIX-PY — the bundle proves its rows came from the named drop and ledger

**Executor:** lane `agent/w54-fix-py`, worktree `.local/worktrees/w54-fix-py`.
**Base:** `92569d5` (`integration/w54`, the judges' record commit). **Date:** 2026-10-12.
**Task:** `docs/program/tasks/W54-FIX-PY.md`; findings `W54-JUDGE-Y` F1, F2, F3, F5 and
`W54-JUDGE-A` F2, F5.
**Checks:** light, container-free. No container, database, object store or network was used;
the real corpus was not read. Implementation commit `6881f1a`; this report is the next commit.

## 0. Findings, fixes and the test that fails without each

Every new test was run against a mutated copy of `src/` with only that fix removed (the
mutation named in the last column, `pytest -o pythonpath=<copy>/src`); each failed there and
passes on the lane tip.

| Finding | Fix | Proving tests | Mutation → result |
|---|---|---|---|
| Y-F1 (export) | `bundle/export.py::_require_identity`, called after every object is placed and before any row is written: `snapshot.derive` over the rows' documents with the drop's `results.md` bytes and save dates must give the row's `base_content_key`, window, `+<d>d` and document count (`base_key_differs`); `with_segmentation_profile(repaired_snapshot(base, ledger), profile)` — the base itself without a ledger — must equal `content_key` **and** `content_digest` (`content_key_differs`; a ledger over another base is `ledger_mismatch`); every ledger block's `crop_sha256` must be the bundled crop of that `(slug, block_id)` (`ledger_crop_absent`, `ledger_crop_differs`). A row save date other than its `results.md`'s is `drop_document_differs`. | `test_identity_offline.py`: `…rows_of_another_drops_text…` (the judge's drop-A-text / drop-B case), `…base_key_the_rows_do_not_derive…`, `…unrepaired_content_digest…`, `…rows_repaired_by_another_ledger…` (L2 with L1's counts), `…ledger_over_another_base…`, `…another_crop…`, `…crop_the_bundle_lacks…`, `…row_save_date…`; positive `…repaired_export…is_written` | call removed → 7 of 8 fail; save-date check removed → its test fails |
| Y-F1 (rows) | `repository.py::_require_key_terms`, the last step of `validate_snapshot_rows`: both keys parse as `<window>+<d>d[+<n>r[+<m>u]].<12 hex>[+seg-…]` and carry the row's window and `+<d>d`; the base key has no repair term; the content key carries `+<n>r` (and `+<m>u` iff `m > 0`) exactly when `repair_count`/`unreliable_count` are non-zero, with those values, and its 12 hex are `content_digest[:12]` (64 lowercase hex); base = content exactly when nothing changed. Refusals are `SnapshotRowsInvalid("key_terms: …")`, mapped by the importer to `bundle_rows_invalid`. | `test_snapshot_rows.py::test_a_key_whose_terms_are_not_the_rows_is_refused` (11 cases), `…unchanged_snapshot…is_its_base` | call removed → 12 of 13 fail (the 13th is the pre-existing positive case) |
| Y-F2 | `bundle/stand.py::import_bundle` step 1: `snapshot_facts(rows.snapshot) == manifest.snapshot`, else `manifest_snapshot_differs`, before the database. | `test_identity_offline.py::test_the_importer_refuses_manifest_snapshot_facts_the_rows_do_not_state[content_digest, base_content_key]` (re-signed forgeries; the stand object fails the test if reached) | check removed → 2 fail |
| Y-F3 | One parser, `corpus_source.read_drop_sums` → `DropSums(sha256, entries)`: `<64 lowercase hex> <space or *><path>`, leading `./` removed, blank lines ignored; uppercase, `\`-escaped lines, other separators, an empty listing and **a path named twice (after `./` removal)** are `drop_sums_malformed`; unreadable is `drop_sums_absent`. Used by repair step 0 (`__main__.verify_crops_against_sums`, now returning the parsed file) and the export (`export.read_drop_sums`, same signature as before). The journal header records `drop_sums_sha256` (`file_journal.LocalJournal.open`, required for a new journal); the ledger file carries it as a top-level `drop_sums_sha256` (`repair_journal/ledger_file.py`), written by `repair full` and `repair ledger`; the export requires it to equal the SHA-256 of `--drop-sums`, which is the manifest's `drop_sums_sha256` (`ledger_sums_differ`). | `repair/test_drop_sums.py` (15 cases: parser accept/refuse matrix, step 0 refusing a duplicate and an uppercase digest, header recorded and required, a writer bound to its sums, the run writing the field into header and ledger, `repair ledger` copying it); `test_identity_offline.py::…without_its_sums_digest…`, `…taken_over_other_sums…`, `…one_canonical_parser[uppercase, duplicate, duplicate-after-dot-slash]` | duplicate check removed → 5 fail; uppercase accepted → 3 fail; ledger-field checks removed → 1 + 1 fail; header field removed → 2 fail |
| Y-F5 | `runs/executor.py`: `_read_gate_inputs` reads the text layer and block index from the store (and builds the observation set) **before** `running → validating`; `_run_evidence_gate(session, run=…, inputs=…)` has no store and only grounds and publishes. D-141's commit after the text stage still precedes the read; the final transaction (terminate, `finish_execution`, the caller's commit) is unchanged. | `runs/test_d141_final_transaction_keeps_the_lease.py::test_static_…` (container-free: source order commit < read < advance < gate; the gate takes no `blob_store`); heavy `…::test_a_run_reads_no_artifact_after_the_validating_advance` (every `read_artifact` and every run transition recorded on a real run) | base `executor.py` restored → static test fails |
| A-F2 | `bundle/stand.py::reconcile_custody` runs `CustodyReconciler` (point `HEAD` of every confirmed admission) inside `report_bundle` whenever the stand has a store; each incident is printed and `custody_incidents` is a compared figure, so any incident is `EXIT_MISMATCH`. The import's step 5 is `report_bundle`, so it reconciles too; the importer now requires a store before step 2 (`blob_store_unavailable`, nothing written). `cli.py` gives `report` a store (`build_stand(True)`), so the shell's discard — exit 0 only — follows a report that has just inspected every confirmed object. | `test_custody_reconcile_offline.py`: `…fails_on_a_custody_incident`, `…no_incident_is_a_full_match`, `…without_a_store…not_reconciled`, `…report_command_opens_the_object_store`; heavy `test_bundle_postgres.py::test_postgres_a_missing_object_fails_the_report_and_the_import` | reconcile call removed → 2 fail; `report` built without a store → 1 fails |
| A-F5 | `cli.py`: `StorageError` (configuration via `StorageConfigurationError`, a missing bucket, an outage, an integrity failure) → `bundle: REFUSED [blob_store_unavailable]: <key-free message>`, `EXIT_REFUSED`. Database settings errors were already `DatabaseError` → `database_unavailable`. | `test_custody_reconcile_offline.py::test_a_storage_failure_is_a_named_refusal_not_a_mismatch[import/report × settings/outage]`, `…inside_the_reconciler_is_a_refusal` | branch removed → 5 fail |

**Backward reading (Y-F3), stated:** *refused, with a named reason.* A journal header without
`drop_sums_sha256` refuses a writer (`journal_sums_unrecorded`, nothing appended) and refuses
`repair ledger` (`journal_sums_unrecorded`, no ledger written); a ledger file without the field
is refused by the export (`ledger_sums_unrecorded`). Nothing is lost: `.local/norms/repairs/`
does not exist on this host and no paid run predates the durable journal. `LEDGER_VERSION`
stays `"2"` and `RepairLedger` is unchanged (`norms/repair.py` is outside the grant): the field
sits beside the ledger's own keys, which `RepairLedger.from_document` ignores.

## 1. Changed files (`git diff --name-only 92569d5..HEAD`)

```
docs/program/W54-FIX-PY.md
src/auditmanager/norms/__main__.py
src/auditmanager/norms/bundle/cli.py
src/auditmanager/norms/bundle/export.py
src/auditmanager/norms/bundle/stand.py
src/auditmanager/norms/corpus_source.py
src/auditmanager/norms/repair_journal/__init__.py
src/auditmanager/norms/repair_journal/file_journal.py
src/auditmanager/norms/repair_journal/ledger_file.py
src/auditmanager/norms/repository.py
src/auditmanager/runs/executor.py
tests/integration/norms/bundle/support.py
tests/integration/norms/bundle/test_bundle_postgres.py
tests/integration/norms/bundle/test_custody_reconcile_offline.py
tests/integration/norms/bundle/test_identity_offline.py
tests/integration/norms/repair/support.py
tests/integration/norms/repair/test_drop_sums.py
tests/integration/norms/repair/test_durable_repair.py
tests/integration/norms/repair/test_local_journal.py
tests/integration/norms/repair/test_proxy_transport.py
tests/integration/norms/test_snapshot_rows.py
tests/integration/runs/test_d141_final_transaction_keeps_the_lease.py
```

`support.py` (bundle) now derives real keys from the synthetic drop (`base_snapshot`,
`synthetic_rows(ledger=…)`): its old fixed key `undated+2d.0123456789ab` with digest `ab…`
is exactly what F1 refuses. The repair test sites pass `drop_sums_sha256=SUMS` to the journal.
`test_snapshot_rows.py`'s fixed key now carries the head of its `content_digest`
(`cccccccccccc`), and its hand-written digest line follows.

## 2. Checks run (lane tip, container-free)

| Command | Result |
|---|---|
| `git diff --check` | clean |
| `.venv/bin/python -m compileall -q src/auditmanager/norms src/auditmanager/runs tests/integration/norms tests/integration/runs` | ok |
| `.venv/bin/python -m pytest -q tests/integration/norms/bundle tests/integration/norms/repair -k "not postgres"` | 244 passed, 57 deselected |
| `.venv/bin/python -m pytest -q tests/integration/norms --ignore=tests/integration/norms/custody/test_two_phase_custody.py -k "not postgres"` | 500 passed, 1 skipped, 58 deselected |
| `.venv/bin/python -m pytest -q tests/integration/runs/test_d141_final_transaction_keeps_the_lease.py -k static` | 1 passed |
| `.venv/bin/python -m pytest -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | 558 passed, 50 subtests (on the committed tree; with the tree dirty `test_alpha_acceptance_command` refuses an uncommitted checkout, by design) |
| mutation runs of §0 | every listed mutant fails its tests |

`custody/test_two_phase_custody.py` is DB-backed (`DATABASE_URL is not set` without the stack)
and unchanged here; it is in the window list.

## 3. Contracts and formats

- `contracts/**`, migrations, root dependency/lock files: **untouched**.
- Manifest format `auditmanager-norm-bundle/1`: unchanged.
- Journal format `norm-repair-journal/1`: the header gains `drop_sums_sha256` (required for a
  new journal; an older header refuses, §0).
- Ledger file: top-level `drop_sums_sha256` beside `LEDGER_VERSION "2"`'s keys.
- `python -m auditmanager.norms.bundle report` now opens the object store and prints
  `custody_objects_checked`, `custody_incidents` (compared, expected 0) and
  `custody_redrive_due`; exit 1 also on a custody incident; exit 2 on any `StorageError`.
- New refusal reasons: `base_key_differs`, `content_key_differs`, `ledger_crop_absent`,
  `ledger_crop_differs`, `ledger_sums_unrecorded`, `ledger_sums_differ`,
  `manifest_snapshot_differs`; `SnapshotRowsInvalid("key_terms: …")`; repair
  `journal_sums_unrecorded`; existing `drop_sums_malformed`/`drop_sums_absent` now shared.

## 4. Risks and known limitations

1. **Two DB tests outside this grant will go red in the window** (`tests/integration/db/
   test_norms_corpus_migration.py`), because `validate_snapshot_rows` now refuses keys whose
   terms disagree with the row before the database sees them:
   - `test_import_conflicts_are_refused_and_write_nothing` case *"the same id under another key"* builds
     `other_key = …replace("+1r+1u.", "+1r+2u.")` with `unreliable_count` still 1: now
     `SnapshotRowsInvalid (key_terms)` instead of `SnapshotImportConflict "the id names key"`.
     A key consistent with the row is fully determined by it, so the case needs other row
     facts too (e.g. `unreliable_count=2` with one more unreliable block, or another
     `content_digest` with its hex in the key).
   - `test_an_import_the_database_refuses_midway_leaves_nothing_behind` crafts
     `+0r+1u` with `unreliable_count=0` to reach `ck_norms_snapshot_raw_key`; Python now
     subsumes that CHECK, so the case should expect `SnapshotRowsInvalid` (nothing written)
     or reach the database by another constraint. Grant one of these edits to whoever
     owns that file.
2. The reconciler's scope is all of custody, not this bundle: an incident on any confirmed
   object blocks every bundle's discard until it is resolved (deliberate: fail closed).
3. `report` now needs the object store; with S3 unconfigured or down it refuses (exit 2) and
   nothing is discarded. `import_bundle` also requires a store before step 2 even for a replay
   after discard (the command line always provides one).
4. F1 proves the keys (text digests, ledger, crops), not the paragraph *text*: the export does
   not re-segment the drop with the ledger and compare paragraphs. The rows' text is bound by
   the row digest the manifest carries, and the key now binds the drop and ledger they claim.
5. The heavy cases (bundle `postgres`, the new runs and missing-object cases) have not run;
   the loader-built rows are expected to pass F1 because `drawn_on(results.md)` is what the
   loader stores, but that is first measured in the window.
6. The new runs test shares its basename with `tests/integration/jobs/…_keeps_the_lease.py`
   (the granted path); `--import-mode=importlib` makes that harmless.

## 5. To the integrator

Merge `agent/w54-fix-py` after reading the diff. `infra/**` is untouched; the shell's discard
rule (`receive-bundle.sh verb_report`: report exit 0 and last import exit 0) needs no change,
because both exits now include the reconciler. Window commands (lane stack: PostgreSQL
`57170`, S3 `60770/60771`, `DATABASE_URL` and the S3 variables set; one test run per lane):

```
PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/norms/bundle
PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/norms/repair -k postgres
PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/norms/custody
PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/runs/test_d141_final_transaction_keeps_the_lease.py tests/integration/jobs/test_d141_final_transaction_keeps_the_lease.py
PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/runs tests/integration/jobs
PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/db/test_norms_corpus_migration.py   # expect the two cases of §4.1 red until edited
```

## 6. Containment

- Every path in §1 is inside the grant: `norms/bundle/**`, `norms/{repository,__main__,
  corpus_source}.py`, `norms/repair_journal/**`, `runs/executor.py` (Y-F5 only),
  `tests/integration/norms/{bundle,repair}/**`, `tests/integration/norms/test_snapshot_rows.py`,
  the granted runs test path and this report. `norms/custody/**` is not edited (the reconciler
  is only called, from `stand.py`).
- Not touched: `contracts/**`, `db/migrations/**`, root lock/dependency files, `infra/**`,
  `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, `.local/norms/corpus/**`, refs
  and tags. Only `agent/w54-fix-py` received commits; nothing was pushed, merged or tagged.
- `git status --porcelain -uall` is empty after the report commit.
