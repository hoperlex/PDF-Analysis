# Task CMP-MATRIX-01 — the effective matrix of a document set: algorithmic build over the page profiles, manual edits with a base revision and undo, the AI-link read, staleness, orphaned edits, a work kind for the preparation

## Outcome
The six operations `getComparisonMatrix`, `prepareComparisonMatrix`, `listComparisonMatrixEdits`,
`applyComparisonMatrixEdits`, `undoComparisonMatrixEdit` and `listComparisonAiLinks` are served by
`ComparisonMatrixAdapter` (it replaces the sealed stub of `CMP-SEAL-C1`). The algorithmic matrix is built from the page
profiles of the ordered versions of one document: max-weight assignment between adjacent versions over the page score,
the thresholds 0.55 / 0.35 / 0.20 and the match rules `v1.2` of the original (resolve, package, direct, permit, page
number, group), table-sheet groups, duplicates, splits with parts coverage, bridges across a version where the sheet is
missing, absent and unmatched cells with their candidates. Manual edits (`link`, `unlink`, `mark_absent`) are applied as
one batch against a base revision (`comparison_matrix_stale` on a moved base) and the last applied edit is undone
(`comparison_edit_none` when there is none); the migrated `0035` approvals read as manual edits. The effective matrix is
a read model (algorithm, then accepted AI links, then manual edits; a manual edit wins; an AI-shaped cell is marked);
staleness is decided by the stored `profile_signature` with stale reasons; an edit whose cells no longer exist is kept
and shown as orphaned. A `comparison_work` kind (`matrix_build`) builds the matrix after the missing page profiles were
enqueued through the profile queue's enqueue function. One read function gives `CMP-SERIES-01` the sheet pairs of each
adjacent transition from the effective matrix.

## Depends on
- CMP-SEAL-C1 (merged): contract `1.10.0`, migration `0039_comparison_core` (the tables `comparison_matrix`,
  `comparison_matrix_edit`, `comparison_ai_link`), the six sealed stubs, the migrated `0035` edits
- CMP-PROFILE-01 (merged): `PageProfileReader`, `PageProfileData` (words, vector lines, stamp, 36 dpi ink mask, scan flag)
- CMP-PROFILE-QUEUE-01 (merged): `enqueue_version_page_profiles`, `page_profile_dedupe_key`
- CMP-WORK-01 (merged): `HANDLER_FACTORIES`, `WorkHandler`, `Outcome`, `ComparisonWorkRepository.enqueue`
- CMP-INGEST-01 (merged): `ComparisonUploadRepository.latest_order`, `require_expert`, the command receipts

## Frozen inputs
- domain contract: `contracts/domain/v1/**` unchanged
- API contract: `contracts/api/v1/openapi.json` `1.10.0`, 131 paths / 148 operations / 432 schemas, 27 error codes (unchanged)
- ADR-0025 decisions 3, 5, 7 (and its addendum), 8, 9, 10, 13, 14, 15, 16, 18, 20, 23; plan sections 1.1, 3.2 (`R3-09`,
  `R3-10`), 4.0 and 4 wave C1; the original at commit `23f379fd` (`lineage.py`, `resolve.py`, `settings.py`, `parts.py`,
  `document_matching.py`), cited in the report by file and line
- migration head: `0039_comparison_core` (not touched)
- base commit: `d11c13fd` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `tests/integration/composition/test_router_answers.py` (`SEALED_STUB_GETS`), `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` (`SEALED_STUB_ADDRESSED`, `SEALED_STUB_COLLECTIONS`, `EXPECTED_ADDRESSED`), `tests/integration/composition/test_comparison_core_stub_operations.py` (`WIRED`), `scripts/recovery/grant_classification.py` (`SEALED_NOT_YET_WRITTEN`), `tests/unit/comparison/work/test_composition_unit.py` (the shipped handler kinds)
- enumerator_owner: CMP-MATRIX-01 for its six operations, its three tables and its work kind only; the other lanes of wave C1 remove their own rows in the merge order MATRIX, ENGINE, VIEWER, SERIES, OVERVIEW, VC-UI-01
- totality_query: `grep -n "ComparisonMatrix\|comparison_matrix\|comparison_ai_link" tests/integration/composition/*.py scripts/recovery/grant_classification.py tests/unit/comparison/work/test_composition_unit.py` lists every row this lane removes, adds or extends

## Captured premise evidence
- premise: the base is the merge of CMP-SEAL-C1 and the wave brief on `integration/compare-modules` (`d11c13fd`): contract `1.10.0`, 131 paths / 148 operations / 432 schemas, 27 error codes, `VERSION` `0.9.0`, head `0039_comparison_core`; the lane printed them before any edit and would have STOPPED if they differed

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `.venv/bin/python -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; cat VERSION; grep -n '^revision: str' db/migrations/versions/20261028_0039_comparison_core.py; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.10.0 131 paths 148 operations 432 schemas 27 error codes
  0.9.0
  79:revision: str = "0039_comparison_core"
  d11c13fd01f431bb081ad9f984fc6a3dc615b39e
  ```
- interpretation: equal to the premise of the wave brief (`1.10.0`, 131 / 148 / 432, head `0039_comparison_core`), so the lane did not STOP

### P-02 — the original's source is not at the path the brief names
- captured_at: 2026-10-28
- command: `ls /root/projects/PDF-proverka; curl -sS -o /dev/null -w '%{http_code}' https://raw.githubusercontent.com/SU10KAZ/PDF-proverka/23f379fd2d5aeb7e7bddb735650e7393c68d4e42/backend/app/services/version_comparison/lineage.py`
- captured_output:
  ```text
  ls: cannot access '/root/projects/PDF-proverka': No such file or directory
  200
  ```
- interpretation: the local clone the brief names does not exist on this host. The lane reads the same commit `23f379fd` as raw files from GitHub into the session scratchpad, outside the repository, as data (the method of `CMP-ORIGINAL-READ-01`), and cites file and line of those copies; nothing of the original is committed

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/matrix/**`
- `tests/unit/comparison/matrix/**`
- `tests/integration/comparison/matrix/**`
- `docs/program/CMP-MATRIX-01.md`
- `docs/program/tasks/CMP-MATRIX-01.md`
- wiring hunks for the six operations and the three tables only (wave C0 brief section 1 rule 4): `src/auditmanager/bootstrap/adapters.py` (the body of `ComparisonMatrixAdapter` and its imports), `src/auditmanager/bootstrap/composition.py` (the one constructor line of that adapter and its imports), `src/auditmanager/api/routers/ports.py` (rows of the matrix port, if any), `src/auditmanager/comparison/public.py` (appends of this lane's names, `HANDLER_FACTORIES` included), `tests/integration/composition/test_router_answers.py`, `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`, `tests/integration/composition/test_comparison_core_stub_operations.py`, `scripts/recovery/grant_classification.py`, `tests/unit/comparison/work/test_composition_unit.py` (its pin of the shipped kinds, extended by this lane's kind only)

## Lane resources
- foundation_instance: `auditmanager-cmp-matrix-01`
- postgres_port: `57840`
- s3_api_port: `61840`
- s3_console_port: `61841`
- postgres_db: `auditmanager_cmp_matrix_01`
- s3_bucket: `auditmanager-cmp-matrix-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`
- `src/auditmanager/comparison/work/**`, `src/auditmanager/comparison/profile/**`, `src/auditmanager/comparison/profile_queue/**`, `src/auditmanager/ingest/**`, `src/auditmanager/storage/**`, `src/auditmanager/jobs/**`, `src/auditmanager/workers/**`: the lane uses their public names and changes none
- `web/**`, global styles, `infra/**`, `Makefile`
- the files of the other C1 lanes (`comparison/engine/**`, `comparison/tiles/**`, `comparison/series/**`, `comparison/overview/**`) and every wiring row that is not this lane's

## Non-goals
- the AI pair check and the writing of `comparison_ai_link` (wave C2): the table is read only and empty until then
- the per-sheet comparison, the series and its post-phases, the transition verdict (`CMP-ENGINE-01`, `CMP-SERIES-01`); the lane gives them the sheet pairs of each adjacent transition and the split relation, nothing else
- the matrix screen, drag and drop, the «рядом» window (`CMP-VC-UI-01`)
- a contract field, a migration or a new dependency (a missing field STOPs to the wave's FIX slot)
- the original's SHX hidden-text stamp reading and release-stamp zones (the page profile carries no such text)

## Deliverables
- `src/auditmanager/comparison/matrix/**`: the assignment, page features and scoring, the rule set `v1.2`, the build, the edits, the effective-matrix read model, the repository, the service, the work kind, the series read function
- the `ComparisonMatrixAdapter` body, its one constructor line, the appends to `comparison/public.py`, the removed stub rows, the added `WIRED` rows and the table rows removed from `SEALED_NOT_YET_WRITTEN`
- unit tests (container-free, on the profiles of the synthetic corpus built through the real children) and integration tests (own PostgreSQL and MinIO), the mutation proofs
- the report `docs/program/CMP-MATRIX-01.md`

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/comparison/matrix tests/integration/comparison/matrix tests/integration/composition`
- expected: all pass; after the last code commit the whole `tests/unit` and `tests/contract` minus the three `D-220` files also pass

## Integration contract
The integrator can rely on: the six operations are served; `auditmanager.comparison.public.HANDLER_FACTORIES` holds a second
factory whose handler has the kind `matrix_build` (payload `{"document_uid": "doc_..."}`, dedupe key
`matrix_build:<document_uid>`, module `versions`); `prepareComparisonMatrix` enqueues `page_profile` items for the versions
that lack profiles and then one `matrix_build`; the build waits for live profile items by yielding and fails with a typed
reason when profiles are missing and nothing builds them; `comparison_matrix` is append-only and one input set is built
once; `comparison_matrix_edit` is written only by `applyComparisonMatrixEdits` and `undoComparisonMatrixEdit` (and by
migration `0039`); `comparison_ai_link` is read only. `CMP-SERIES-01` reads the sheet pairs of each adjacent transition
through the function the report names.

## Failure/idempotency/security cases
- `applyComparisonMatrixEdits` and `undoComparisonMatrixEdit` against a moved base revision (a newer build or a newer edit): `409 conflict` `comparison_matrix_stale`, nothing written
- undo with no applied edit: `409 conflict` `comparison_edit_none`; a batch over 500 edits and an edit the database or the model cannot accept: `422 validation_failed` `comparison_edits_limit` / `comparison_edit_invalid`
- a batch is applied together or not at all; the same key and payload replays the recorded outcome, the same key with another payload is `idempotency_key_reuse`
- an administrator without the expert role is refused in the transaction that acts (ADR-0025 decision 16), a reader cannot write
- an edit whose cells no longer exist is kept and listed as orphaned, never applied silently and never dropped
- a manual edit wins over an accepted AI link and over the algorithm; an AI link applies only while the cell it answered is still unmatched or doubtful
- the same profiles, order and edits give byte-identical matrix JSON; a page is identified by its version and profile identity, never by a number, name or label alone

## Rollback / feature flag
The comparison module flag (`comparison/modules.py`) governs the worker: with `AUDITMANAGER_COMPARISON_MODULES=none` (the
default) the build item stays `queued`. The six operations answer from the stored rows whatever the flag. Rollback is not
merging the lane (the sealed stubs answer `503 dependency_unavailable`).

## Handoff
- changed files: to be filled in the last commit
- commands/results: to be filled in the last commit
- known limits: to be filled in the last commit
- integration notes: to be filled in the last commit
