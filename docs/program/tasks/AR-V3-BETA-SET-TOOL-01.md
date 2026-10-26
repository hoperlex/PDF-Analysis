# Task AR-V3-BETA-SET-TOOL-01 — operator command that promotes one reviewed retrieval set

task_id: AR-V3-BETA-SET-TOOL-01
status: completed in development candidate

## Outcome

An operator can promote ONE reviewed retrieval set, and its catalogue, into durable custody with a command, in two deliberately separate steps that keep the two-person check the promotion library already encodes. `plan` is read-only: it prepares the candidate inside one `REPEATABLE READ READ ONLY` transaction and prints `set_sha256`, `catalogue_sha256` and the comparison verdict so an independent reviewer can compare them with their own computation; it writes nothing to the database and never opens the object store. `promote` runs only when the bundle carries `expected_set_sha256` and `expected_catalogue_sha256` equal to the freshly prepared candidate: it admits both artifacts (the R-76 admissions outbox, one transaction), runs the existing custody dispatcher, then finalizes (both saved Blobs re-read, the immutable set row and both bindings inserted in one transaction). Re-running the same command with the same `set_id` is an exact replay (`replayed: true`), never a duplicate. Exit 0 verified or replayed, 2 refused with no side effect, 3 uncertain with the `set_id` and the exact next command.

## Depends on

- `AR-SET-PROMOTION-01` — completed promotion library (`prepare_promotion`, `admit_matched`, `finalize_matched`, `select_verified_retrieval_set`) over migration 0023.
- `AR-BETA-LOCAL-CUSTODY-01` — completed local import of the repaired snapshot with confirmed source custody.
- `W54-CUSTODY-01` — completed custody admission, dispatcher and binding publication.

## Frozen inputs

- domain contract: sealed; no reseal in this task.
- API contract: `1.4.0`, 91 paths / 103 operations / 298 schemas, 27 error codes; unchanged.
- analysis/comparison/event contract: unchanged; v3 runtime remains unserved.
- migration head: `0032_ar_v3_run_group`; the task reuses the existing `0023_norm_citations` set and custody tables and adds nothing.
- base commit: `354a9092c48a5d5f37fe8fe3de60af4b4dff7c88` on `integration/ar-close-1026`.
- governing inputs: `docs/program/AR-SET-PROMOTION-01.md`, `docs/program/AR-BETA-LOCAL-CUSTODY-01.md`, `R-135` code-first cadence.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the promotion library has no caller outside tests, so no `nrs_` set can be created outside a test, and the dispatcher takes any due admission.

### P-01 — no source caller of the promotion functions at the base

- captured_at: 2026-10-26
- command: `git grep -n "prepare_promotion\|finalize_matched" 354a9092c48a5d5f37fe8fe3de60af4b4dff7c88 -- src scripts | grep -v "norms/retrieval/promotion.py"`
- captured_output:
  ```text
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/norms/public.py:161:    finalize_matched,
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/norms/public.py:162:    prepare_promotion,
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/norms/public.py:316:    "finalize_matched",
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/norms/public.py:331:    "prepare_promotion",
  ```
- interpretation: the only other occurrences are the import and `__all__` lines of the public facade, no call site. The brief's expectation of "no src caller" holds.

### P-02 — only tests call the library

- captured_at: 2026-10-26
- command: `git grep -l "prepare_promotion\|finalize_matched\|admit_matched\|select_verified_retrieval_set" 354a9092c48a5d5f37fe8fe3de60af4b4dff7c88 -- tests`
- captured_output:
  ```text
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:tests/integration/norms/custody/test_retrieval_set_promotion.py
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:tests/integration/norms/retrieval/test_promotion.py
  ```
- interpretation: the two named tests are the only callers; the working call sequence this command reproduces is theirs.

### P-03 — the dispatcher claims any due admission

- captured_at: 2026-10-26
- command: `grep -n "FOR UPDATE SKIP LOCKED" src/auditmanager/norms/custody/repository.py`
- captured_output:
  ```text
  78:    "ORDER BY available_at, norm_custody_admission_id LIMIT 1 FOR UPDATE SKIP LOCKED"
  ```
- interpretation: the claim query has no role or target scope, so `CustodyDispatcher.dispatch()` would also take (and fail or reject) another operator's pending admission. The command therefore refuses while any admission outside this set is pending (`foreign_pending_admissions`) and its source never serves a foreign admission. A scoped dispatcher is a library change this task may not make.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/promote_cli.py`
- `src/auditmanager/norms/__main__.py`
- `tests/integration/norms/retrieval/test_promote_cli.py`
- `tests/integration/norms/custody/test_promote_cli_db.py`
- `docs/program/tasks/AR-V3-BETA-SET-TOOL-01.md`
- `docs/program/AR-V3-BETA-SET-TOOL-01.md`

Temporary lane files, ignored by Git and removed or left untracked at hand-back: `.env` and the `.venv` symlink in this lane's worktree only.

## Lane resources

- foundation_instance: `auditmanager-ar-set-tool`
- postgres_port: `58610`
- s3_api_port: `62110`
- s3_console_port: `62111`
- postgres_db: `auditmanager_ar_set_tool`
- s3_bucket: `auditmanager-ar-set-tool`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, root dependency and lock files.
- `src/auditmanager/bootstrap/**`, `src/auditmanager/runs/**`, `web/**`, global styles.
- The rest of `src/auditmanager/norms/**` (read-only here: `promotion.py`, `custody/**`, readers and builders), and `.env` or `.env.example` content committed to Git.
- `origin/dev`, `origin/main`, tags and the deployment stand.

## Non-goals

- No reviewed map, query vector, original-checklist decision or `nrs_` set is authored, and no real normative set is created: this is the tool, not its use.
- No `record_rejection` call: a mismatched expectation writes no rejected row, so the `set_id` stays free for the corrected digests.
- No custody `requeue`, `report` or `reconcile` command (the runbook uses the public library functions), no multi-set batch, no stand import, Run pin, v3 activation or model call.
- No change to the promotion library, the dispatcher or `norms/__main__.py` (the repair runner, which is not the place for this command).

## Deliverables

- `src/auditmanager/norms/retrieval/promote_cli.py` with `python -m auditmanager.norms.retrieval.promote_cli {new-id,plan,promote}`: strict bundle loader, `PromotionRunner` port with a database/S3 implementation built from `DATABASE_URL` and `S3_*`, typed exit statuses.
- Offline tests with a fake runner and DB-backed tests against real PostgreSQL 0023 custody and S3, each new refusal shown failing under a quoted mutation.
- This task file and `docs/program/AR-V3-BETA-SET-TOOL-01.md` with the exact operator runbook.

## Verification

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_promote_cli.py` — offline, 61 tests.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/custody/test_promote_cli_db.py` — 11 tests on the lane's PostgreSQL and S3.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval tests/integration/norms/custody -k "promotion or promote"` on the lane's stack.
- The governance check of this file prints `[]`; `python -m compileall` and `git diff --check` pass. Full `make gate` is deferred by `R-135`.

## Integration contract

The command is an unserved operator tool. It imports only the norms context, `shared.db`, `shared.identity` and `storage.public`; it adds no route, contract, migration or composition-root entry. `plan` is safe to run at any time. `promote` writes through the library only (`admit_matched`, the existing `CustodyDispatcher`, `finalize_matched`); it runs no SQL of its own except the read-only custody state counts. `set_id` is supplied by the operator and must be reused on every retry. Exit status 2 means nothing was written by this invocation; 3 means an admission or dispatch state may exist and the same command, run again, converges or refuses with a reason; any other status is an unclassified fault before the admission transaction committed. The six `nrs_` sets of the AR v3 beta pack need six reviewed maps with six distinct map digests (0023 unique verified identity) and six invocations.

## Failure/idempotency/security cases

- Unknown or duplicate keys, floats, a non-unit vector, a vector that does not hash to its provenance digest, oversize files, symlinks, FIFOs and extra directory entries refuse before any database access.
- A differing expected digest, a stale or foreign pending admission, a reused `set_id` with other evidence, a verified identity held by another set and a manifest mismatch refuse before the first admission (exit 2).
- An interrupted process, a failed or poisoned dispatch step, an unavailable Blob and a finalize refusal after admission exit 3 and are resumed by the same command; a poisoned admission additionally needs custody `requeue`.
- No secret is printed: storage refusals are key-free by their type, database errors print only the exception class, the bundle holds no credential.

## Rollback / feature flag

Forward-revert the new command and its tests. No data, migration or contract is involved; sets already promoted are immutable 0023 rows and stay as evidence. The lane's PostgreSQL and S3 volumes are disposable test data and are not part of the revert.

## Handoff

- changed files: see `docs/program/AR-V3-BETA-SET-TOOL-01.md`
- commands/results: see `docs/program/AR-V3-BETA-SET-TOOL-01.md`
- known limits: no real set has been promoted; the dispatcher is global (mitigated by a pre-admission check); the reviewer's independence is procedural
- integration notes: no push in this lane; run the DB tests again on the integrator's database lane
