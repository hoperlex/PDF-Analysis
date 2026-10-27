# Task CMP-INGEST-01 — plain-PDF comparison upload operations (ADR-0025 decisions 9, 10, 11, 16)

## Outcome
An expert declares a batch of plain PDFs for comparison, sends them in 16 MiB parts, completes each file against its
declared SHA-256 and size, reads the grouping proposal the stamp reader made (designation, order, stage and section,
for the expert to confirm), confirms a set, and gets one document with one `comparison_pdf` version per file; the
expert then re-orders the versions of that document in append-only revisions. A comparison-only version never starts a
section analysis (`analysis_input_invalid`, reason `comparison_only_version`) and never becomes `current_version_uid`
of a document that has a portal version. Eight sealed operations of contract `1.9.0` are served instead of stubbed.

## Depends on
- CMP-SEAL-C0 (merged): contract `1.9.0`, migration `0038_comparison_foundation`, the five upload tables,
  `document_version.upload_kind`
- CMP-STORAGE-PARTS-01 (merged at `bddf340e`): `begin_multipart`, `upload_part`, `complete_multipart(before_publish)`,
  `abort_multipart_sweep`
- CMP-ADR-01 (ADR-0025 decisions 9, 10, 11, 16 and the 2026-10-27 addendum, item 3)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` unchanged (no new error code; the reasons are the ones registered by the
  seal: `comparison_files_limit`, `comparison_sets_limit`, `comparison_batch_bytes_limit`,
  `comparison_batch_pages_limit`, `comparison_project_bytes_limit`, `comparison_part_number`, `comparison_part_size`,
  `comparison_set_members`, `comparison_upload_active`, `comparison_upload_state`, `comparison_set_state`,
  `comparison_version_order_stale`, `comparison_only_version`)
- API contract: `contracts/api/v1/openapi.json` `1.9.0`, 115 paths / 130 operations / 351 schemas, 27 error codes
- analysis/comparison/event contract: ADR-0025 decisions 9, 10, 11, 16 and the addendum of 2026-10-27 item 3
- migration head: `0038_comparison_foundation` (not touched)
- base commit: `bddf340e` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the base is the seal's tree with CMP-STORAGE-PARTS-01 merged: contract `1.9.0`, 115 / 130 / 351, head
  `0038_comparison_foundation`, the two comparison adapters still sealed stubs; the lane re-reads it before any edit and
  STOPs if it differs

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `git show HEAD:contracts/api/v1/openapi.json | python3 -c "import json,sys;d=json.load(sys.stdin);print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; git grep -n "^revision: str" HEAD -- db/migrations/versions/20261028_0038_comparison_foundation.py | cut -d: -f3-; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.9.0 115 paths 130 operations 351 schemas 27 error codes
  revision: str = "0038_comparison_foundation"
  bddf340e5807beff18faff0154b7280ab700dbc4
  ```
- interpretation: equal to the premise (contract `1.9.0`, 115 / 130 / 351, head `0038_comparison_foundation`), so the
  lane did not STOP. The base holds CMP-STORAGE-PARTS-01 (`bddf340e`), so the multipart API this lane builds on exists

### P-02 — the sealed adapters and the enumerators the lane unseals
- captured_at: 2026-10-28
- command: `grep -n "class ComparisonUploadAdapter\|class ComparisonVersionOrderAdapter\|comparison_uploads=\|comparison_version_orders=" src/auditmanager/bootstrap/adapters.py src/auditmanager/bootstrap/composition.py; grep -n "SEALED_NOT_YET_WRITTEN = " scripts/recovery/grant_classification.py`
- captured_output:
  ```text
  src/auditmanager/bootstrap/adapters.py:5263:class ComparisonUploadAdapter:
  src/auditmanager/bootstrap/adapters.py:5330:class ComparisonVersionOrderAdapter:
  src/auditmanager/bootstrap/composition.py:431:        comparison_uploads=ComparisonUploadAdapter(),
  src/auditmanager/bootstrap/composition.py:432:        comparison_version_orders=ComparisonVersionOrderAdapter(),
  scripts/recovery/grant_classification.py:168:SEALED_NOT_YET_WRITTEN = frozenset((
  ```
- interpretation: both adapters are stubs with no constructor arguments; wiring them needs the session factory and the
  blob store, so the two composition lines change (the only composition hunk, listed below)

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/ingest/comparison_pdf/**`
- `src/auditmanager/documents/**`
- `src/auditmanager/runs/commands.py`
- `tests/unit/ingest/comparison_pdf/**`
- `tests/integration/ingest/comparison_pdf/**`
- `docs/program/tasks/CMP-INGEST-01.md`
- `docs/program/CMP-INGEST-01.md`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/routers/comparison_uploads.py`
- `src/auditmanager/api/routers/comparison_version_orders.py`
- `scripts/recovery/grant_classification.py`
- `tests/integration/composition/test_router_answers.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_comparison_stub_operations.py`

The last eight are the wiring hunks of `docs/program/dispatch/CMP-WAVE-C0.md` section 1 rule 4 (the adapters, the ports,
the two router files, the two enumerators, the stub register and `SEALED_NOT_YET_WRITTEN`) plus the one composition
hunk the constructor arguments need. Each hunk is kept minimal; the integrator resolves overlaps in the merge order of
section 3.

## Lane resources
- foundation_instance: `auditmanager-cmp-ingest-01`
- postgres_port: `57760`
- s3_api_port: `61760`
- s3_console_port: `61761`
- postgres_db: `auditmanager_cmp_ingest_01`
- s3_bucket: `auditmanager-cmp-ingest-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependency and lock files
- `src/auditmanager/ingest/envelope.py`, `pdf_reader.py`, `bundle_archive.py` (the portal-bundle envelope is unchanged;
  the comparison policy lives in `ingest/comparison_pdf/` and starts the same reader program with its own limits)
- `src/auditmanager/storage/**` (CMP-STORAGE-PARTS-01), `src/auditmanager/comparison/**` (the other lanes' wiring),
  `src/auditmanager/runs/v3_group.py`
- every other lane's paths of `docs/program/dispatch/CMP-WAVE-C0.md` section 2

## Non-goals
- the batch operations (`listComparisonUploads`, exclude, retry, pause, resume, cancel) and the work kinds over them:
  CMP-INGEST-02
- the page profile reads: CMP-PROFILE-01; the ZIP reader: CMP-INGEST-ZIP-01
- no contract, migration or dependency change; no new error code

## Deliverables
1. `src/auditmanager/ingest/comparison_pdf/`: the decision-9 limits as typed refusals, the comparison envelope policy,
   the stamp reader (a ceilinged child), the pure proposal rules, the repository and the use cases for the eight
   operations
2. `documents`: `upload_kind` written and read, the comparison manifest role, the current-version rule of decision 11
3. `runs/commands.py`: the `comparison_only_version` refusal for `startRun` and `reauditRun`
4. wiring: the two adapters, the ports, the two routers, the register hunks, `SEALED_NOT_YET_WRITTEN`
5. tests in the two allowed directories, every guard shown failing under a quoted mutation
6. the report `docs/program/CMP-INGEST-01.md` with the API CMP-INGEST-02 builds on

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/ingest/comparison_pdf tests/integration/ingest/comparison_pdf` on the lane's own PostgreSQL and MinIO
- expected: all green
- command: `git diff --check`; `pytest -q tests/contract` minus the three `D-220` files; the register files of
  `tests/integration/composition` that the wiring touches
- expected: clean / green

## Integration contract
CMP-INGEST-02 builds on `ComparisonUploadRepository` and the service functions named in the report: the batch row, the
set rows and their states are written by this lane up to `needs_confirmation` / `ready` / `admitting` / `done`; the
lane never writes `excluded`, `paused`, `cancelled`, `completed` or a retry of a failed set (INGEST-02's). The
reading and proposal functions (`read_file`, `form_proposal`) are importable so a work handler can call them.

## Failure/idempotency/security cases
- a declared batch over a decision-9 limit is refused before any row exists
- a part for a file with no token, after completion, for a failed or cancelled batch, with a number the size does not
  need or a size that is not the part size is refused before the store is asked
- a completed file whose bytes differ from the declaration is refused, marked failed, leaves no published blob
- a PDF outside the comparison envelope (encrypted, over the page or element limit, unreadable) marks the file failed
  with its reason and never becomes a version
- every keyed write replays its recorded outcome under the same key and refuses a different payload
- confirmation by an administrator without `expert` is refused (ADR decision 16); the order never changes
  `version_ordinal`

## Rollback / feature flag
The module flag (`comparison/modules.py`) gates the screens; the operations are additive. Reverting the merge restores
the sealed stubs; no migration is involved.

## Handoff
- changed files: `src/auditmanager/ingest/comparison_pdf/**` (new: `limits`, `names`, `envelope`, `child`, `stamp_reader`,
  `stamp`, `reading`, `proposal`, `repository`, `service`, `orders`, `views`, `public`), `src/auditmanager/documents/`
  (`README.md`, `__init__`, `models`, `public`, `repository`), `src/auditmanager/runs/commands.py`, the wiring hunks
  (`src/auditmanager/bootstrap/{adapters,composition}.py`, `scripts/recovery/grant_classification.py`,
  `tests/integration/composition/{test_router_answers,test_an_absent_parent_is_not_an_empty_page,test_comparison_stub_operations}.py`),
  `tests/unit/ingest/comparison_pdf/` (3 files), `tests/integration/ingest/comparison_pdf/` (10 files and a conftest), this
  file and `docs/program/CMP-INGEST-01.md`
- commands/results: unit 114 passed; integration 148 passed (262 together); `tests/contract` minus the three `D-220` files
  1307 passed, 19283 subtests; `tests/integration/composition` 1909 passed, 3 skipped; portal-path ingest and documents 780
  passed and 1 failed that is red on the base too; runs subset 214 passed; recovery and journey guards 116 passed;
  `git diff --check` clean; 52 mutations shown red and restored (report section 5)
- known limits: report section 6 (the reading is inside the completion request; a content-refused file leaves its published
  blob; a wrong declaration blocks the batch until INGEST-02's cancel; unregistered reason strings; the group start refuses by
  manifest role; one pre-existing red in `tests/integration/documents`)
- integration notes: report sections 3 and 7. The API INGEST-02 builds on is `auditmanager.ingest.comparison_pdf.public`
