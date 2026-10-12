# W54-BUNDLE-01 — the promotion bundle: export, import, report, requeue

**Executor:** lane `agent/w54-bundle-01`, worktree `.local/worktrees/w54-bundle`.
**Base:** `f1c24b8` (`integration/w54`: Stage A, Stage B and STAND-COPY merged). **Date:** 2026-10-12.
**Task:** `docs/program/tasks/W54-BUNDLE-01.md`; grant `W54-PLAN.md` §4 Stage C plus this file;
`W54-FREEZE-01` amendments 1–2; contracts fixed by `W54-TRANSPORT-01` §3 and
`W54-STAND-COPY-01` §3; `R-88`, `R-104`, `R-109`, `R-110`.
**Checks:** `R-102` light acceptance, container-free. No container was started, no database ran,
the real corpus was not read. Implementation commit `0100a93`; this report is the next commit.

## 0. What was built, against the required items

| Required | Where, and the case that proves it |
|---|---|
| CLI `import|report <dir> --copy-record <path>`, `requeue <dir>` (TRANSPORT's fixed command), plus `export` and `verify` here | `norms/bundle/cli.py`, `__main__.py`; `test_bundle_transport_refusals.py::_fixed` unchanged and green |
| bundle digest = SHA-256 of the ASCII-path `SHA256SUMS`; name `<content_key>+<digest>` | `layout.py`; `test_layout.py` runs the Python patterns and `fc_check_bundle_tree` side by side (both accept the export, both refuse six kinds of damage) |
| the importer's acceptance rule (§1 below) | `copy_record.py`; `test_copy_record.py` (matrix), and parity with records the real `copy-serve.sh` writes (`…_the_waiver_copy_serve_writes_is_accepted…`, `…_the_attested_copy…`, `…_an_unattested_copy…`) |
| §3.5's order on a disposable stand | `stand.py::import_bundle`; heavy `test_bundle_postgres.py::test_postgres_the_import_runs_in_order_with_its_ids_and_leaves_the_fingerprint` (steps in order; `max(confirmed_at) ≤ snapshot.created_at ≤ min(bound_at)`; ids equal the promotion database's) |
| replay a no-op | heavy `…_an_exact_replay_is_a_no_op`, `…_a_replay_after_the_objects_were_discarded_is_a_no_op` (table counts unchanged) |
| conflicts refused | pre-checked before any write; heavy `…_conflicts_are_refused_and_write_nothing[key-under-another-id|id-under-another-key]` |
| an unconfirmed admission keeps the bundle | exit 75; heavy `…_an_unconfirmed_admission_keeps_the_bundle_and_a_rerun_finishes`, `…_poisoned_admissions_take_requeue_then_import` |
| `report` matches, a tampered row fails it | `stand.py::report_bundle`; heavy `…_report_fails_on_a_tampered_row_and_on_a_client_write` |
| an import alone leaves the fingerprint unchanged | by construction (§1); heavy order test compares the fingerprint before and after; every refusal case re-checks it |
| refusals: no record, stale, unattested, expired, drifted fingerprint, absent build, `rejected` manifest Blob | container-free before the database (`test_import_refusals_offline.py`, the database object fails the test if touched); heavy `…_refusals_write_nothing` (9 cases, nothing written, fingerprint unchanged) |
| the delete step | §2 below; `test_discard_after_report.py` |

## 1. The importer's accept/refuse rule, as implemented (`copy_record.py`)

Accepted under exactly:

* `kind "copy"`: `record_version 1`, `state "open"`, `purpose "import"`, an attestation whose
  `dump_sha256` equals `dump.sha256`, `now ≤ quiesced_at + 12 h`; or
* `kind "test_data_waiver"`: `record_version 1`, `state "open"`, `purpose "import"`, a waiver with
  `now ≤ expires_at`, `real_data_marker false`, `dump` and `attestation` null;

and in both cases `writers_present ⊆ writers_stopped`, `quiesced_at` set, the record's
`migration_head` equal to the database's current revision, the fingerprint algorithm
`stand-fingerprint-v1`, and the fingerprint recomputed now equal to the record's (checked on
every run, not only the first). Refusal words: `copy_record_absent` (also a directory, `D-37`),
`copy_record_unreadable`, `copy_record_version`, `copy_record_closed` (stale), `copy_record_stale`
(the stand migrated since), `copy_record_not_import`, `copy_record_not_quiesced`,
`copy_record_unattested`, `copy_record_expired`, `waiver_after_real_data`, `fingerprint_drifted`.
The marker *file* is not visible in the container; `receive-bundle.sh`'s `waiver-before-real-data`
guard checks it.

**The fingerprint.** `FINGERPRINT_SCRIPT` is byte for byte `copy-serve.sh`'s block (test), and
`StandFingerprint.from_lines` equals `fc_fingerprint_json` (test). The api image carries `src/`,
not `infra/`, hence the second carrier. **An import alone leaves it unchanged**: the importer
writes only `norm*` rows, `norm_custody.*` events and Blob rows an admission names — no new
exclusion was needed. One edge is refused instead: on the first run, a manifest Blob already held
by a client row that no admission names (`manifest_blob_held_outside_custody`), because admitting
it would move that row out of the fingerprint.

## 2. The delete step (plan §3.5 step 5) — decision

STAND-COPY's `discard <KEY>` verb cannot be added inside this grant: a new verb reddens
`test_every_verb_has_grammar_violation_cases` (it pins the five verbs) and a new guard reddens
`test_every_guard_has_a_case_here`, both in `test_bundle_transport_refusals.py`, which this lane
does not own. **Implemented instead, in `receive-bundle.sh`'s existing `report` verb** (I granted
myself only those lines, as the brief allows): the module's output is kept as
`logs/<KEY>.report`; when that report exits 0 **and** `logs/<KEY>.import.exit` holds 0, the verb
removes `bundles/<KEY>/objects/` only, under the import lock, and writes `logs/<KEY>.discarded`
(time, report SHA-256). No new verb, guard or grammar; exit status still passed on. The importer
accepts a bundle whose `objects/` is absent as a whole only when every admission is already
confirmed (a no-op replay); otherwise `objects_discarded`. The plan's literal order ("after
`report` matches, delete") holds.

## 3. Changed files (`git diff --name-only f1c24b8..HEAD`, 25 paths with this report)

* `src/auditmanager/norms/bundle/` (new): `errors.py`, `layout.py`, `manifest.py`, `contents.py`,
  `copy_record.py`, `export.py`, `stand.py`, `cli.py`, `__main__.py`, `__init__.py`.
* `src/auditmanager/norms/public.py` — export lines marked `# W54-BUNDLE-01`.
* `src/auditmanager/norms/README.md` — two module rows, the bundle section.
* `docs/program/DEPLOYMENT_RUNBOOK.md` — §11: the `report` row, new subsection "The importer and
  `report`", the "does not do" bullet.
* `infra/deploy/receive-bundle.sh` — `verb_report` and two header comment lines (§2).
* `tests/integration/norms/bundle/` (new): `support.py`, `conftest.py`, `test_layout.py` (14),
  `test_manifest.py` (21), `test_contents.py` (11), `test_copy_record.py` (25),
  `test_export_offline.py` (13), `test_import_refusals_offline.py` (14),
  `test_discard_after_report.py` (7) — 105 container-free; `test_bundle_postgres.py` (19, heavy).
* `docs/program/W54-BUNDLE-01.md` — this report.

## 4. Checks run (worktree, on `0100a93` with a clean tree unless noted)

| Command | Result |
|---|---|
| `git diff --check f1c24b8..HEAD` | clean |
| `.venv/bin/python -m compileall -q src/auditmanager/norms tests/integration/norms/bundle` | exit 0 |
| `bash -n infra/deploy/receive-bundle.sh`; `shellcheck -x infra/deploy/receive-bundle.sh infra/deploy/push-bundle.sh infra/deploy/lib/forced-command.sh` (0.9.0) | OK; no findings |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/bundle -k "not postgres"` | **105 passed**, 19 deselected |
| `… pytest -q tests/integration/composition/test_bundle_transport_refusals.py tests/integration/composition/test_stand_copy_refusals.py tests/integration/composition/test_norms_worker_image_contract.py` | **324 passed, 1 skipped** (STAND-COPY's window case) |
| `… pytest -q tests/integration/norms -k "not postgres" --ignore=…/custody/test_two_phase_custody.py --deselect …::test_every_relevance_anchor_resolves_to_the_exact_real_corpus` | **447 passed, 1 skipped**, 58 deselected |
| `… pytest -q tests/contract --ignore=test_cp00_candidate.py --ignore=test_cp00_final_state.py --ignore=test_validate_bootstrap.py` | **558 passed**, 50 subtests (ALR-05 included; on the dirty tree only `test_alpha_acceptance_command.py` failed, as SEAL recorded) |
| `pytest --collect-only tests/integration/norms/bundle` | 124 collected |
| SQL syntax: every `text()` of `export.py`/`stand.py`, the fingerprint's settings and generator and one generated statement, parsed by pglast (scratch venv); a broken statement is refused | 15/15 parse (syntax only) |
| ruff 0.17.0 (scratch venv) over `norms/bundle`, the tests, `norms/public.py` | all checks passed |
| Mutation: 17 mutations (discard `rm`, the import-exit condition, marker, expiry, fingerprint compare, one SQL setting, open state, build absent, rows digest, both discard-allowance clauses, drop-sums compare, crops index, binding digest, duplicate slot, vector digest, row shape), each applied, the light suite run, the file restored | **17/17 red** (two survivors of the first pass closed by two added cases) |

## 5. Contracts

No `contracts/**`, migration, API, domain or event change; `0018`/`0019` were sufficient.
New file formats (repository-internal): `auditmanager-norm-bundle/1` (`manifest.json`, schema in
`manifest.py`'s docstring; `min_migration_head` `0018_norm_custody`; `db_growth_bytes` with its
method), `auditmanager-bundle-rows/1` (`rows/`), `auditmanager-bundle-build/1` (`build/`). Objects
`objects/<2 hex>/<sha256>.pdf`; slots: anchor `pdf` = `source_document_ref`, anchor `crop` = the
block's `blk_…`. CLI exit statuses: 0 done/match, 1 report mismatch, 2 refused
(`bundle: REFUSED [<reason>]`), 75 not finished. `norms.public` gains the bundle surface.

## 6. Risks and known limitations

* **Integrator step needed — the object store.** ALR-05 lets `norms` reach the S3 adapter only via
  `auditmanager.storage.public`, which does not export `S3BlobStore`/`S3StorageSettings`, and the
  file is outside this grant. Until it does, `import` refuses `blob_store_unavailable` (tested);
  `export`, `verify`, `report`, `requeue` work. The heavy tests inject the store directly.
* **No database ran.** 19 heavy cases are unexecuted; the SQL is syntax-checked only. The
  fingerprint's percent-escaping through SQLAlchemy/psycopg was checked offline (`%%` → `%`).
* **Free space** (§3.5 step 1) is not measurable from the container; `capacity` and `receive`'s
  `staging-has-room` hold that rule. The manifest's `object_bytes` and `db_growth_bytes` feed it.
* `db_growth_bytes` is proportional relation size plus an *estimated* 1 536 B per custody slot.
* Export holds one snapshot's rows in memory (as SNAPSHOT noted, a few hundred MB); vectors stream.
  Hardlinking makes the drop's inodes read-only (`chmod a-w`), as the plan intends.
* `corpus_source.py`'s docstring ("the only module … that touches a filesystem") was already untrue
  (the embedder's checkpoints) and is more so now; that file is outside this grant. README updated.
* `manifest_blob_held_outside_custody` blocks an import whose PDF equals a client upload byte for
  byte — an owner decision if it ever occurs.
* `AGENTS.md` §8 asks a full gate for `infra/**` and `conftest.py` changes; under `R-102` that is the
  wave's single final gate.

## 7. Instructions for the integrator

1. **Add to `src/auditmanager/storage/public.py`** (one line each in the import and `__all__`):
   `from auditmanager.storage.s3 import S3BlobStore` and
   `from auditmanager.storage.settings import S3StorageSettings` — or rule another seam. Then
   `test_import_refuses_loudly_while_the_storage_surface_lacks_the_adapter` still passes (it removes
   the attribute itself).
2. Merge before STAND-COPY's later edits per plan §5; shared paths in §6 order:
   `DEPLOYMENT_RUNBOOK.md` (§11 only), `norms/{public}.py` export lines, `norms/README.md`,
   `receive-bundle.sh` (`verb_report` only).
3. **Heavy steps — owner window only**, one at a time, after `free` ≥ 6 GiB available and `df` ≥
   increment (≪ 1 GB) + 3 GiB. Lane stack on PostgreSQL `57170`, S3 `60770/60771`, lane `.env`:

   ```sh
   cd .local/worktrees/w54-bundle            # or the merged tree
   set -a; . ./.env; set +a
   .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/bundle/test_bundle_postgres.py
   .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/bundle
   ```

   Expected: 19 passed, then 124 passed. Each run creates and drops two throwaway databases
   (`w54_bundle_promotion_*`, `w54_bundle_stand_*`) and one bucket per test. Stop the stack by its
   own compose project; kill nothing by pattern.
4. Operator step (4) of `W54-CORPUS-OPERATE-01`: `… bundle export …` (README, runbook), then
   `… bundle verify <dir>`, then `push-bundle.sh`.

## 8. Containment

* `git diff --name-only f1c24b8..HEAD` on the commit adding this report lists exactly §3's 25 paths:
  `norms/bundle/**`, the export lines, `norms/README.md`, `tests/integration/norms/bundle/**`,
  `DEPLOYMENT_RUNBOOK.md` (import and report), `receive-bundle.sh` (the `report` verb lines,
  self-granted per the brief), this report. `git status --porcelain -uall` prints nothing.
* Not touched: `contracts/**`, `db/migrations/**`, `storage/**`, `lib/forced-command.sh`,
  `test_bundle_transport_refusals.py`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`,
  `CURRENT_STATE.md`, lock files, refs, tags, the stand, `.local/norms/corpus/**` (only its
  `MANIFEST.json`/`crops_index.json` headers were read once to learn the layout; nothing written).
* No container, push, merge, tag, stash, worktree creation or kill.
