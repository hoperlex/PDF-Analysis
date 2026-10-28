# Task CMP-ENGINE-01 — the per-sheet comparison engine: a ceilinged child, the eight channels, the content-keyed result and its mask

## Outcome
Page A (older) and page B (newer) of one project are compared by the engine of «Сравнение версий» and the result is
stored once: the registration of B onto A, the eight channels (`geometry`, `color`, `text`, `text_coverage`, `zones`,
`annotations`, `warnings`, `spec_positions`) with their states, the region classes (`text`, `text_moved`, `graphic_added`,
`graphic_removed`, `graphic_changed`, `color_change`, `light_fill`, `line_style`, `block_moved`, `shifted`), the eight layers
of `ComparisonLayer`, the text changes with their numbers, the block alignment (`aligned_blocks`), the status (`same`,
`same_zones_changed`, `different`, `needs_review`) and the forcing reasons, as the original has them. The computation runs in a
child process under the ceilings of ADR-0025 decision 8 (768 MiB of address space, 300 s CPU, 600 s wall): an overrun or any
end without a result is `needs_review` with reason `RENDER_FAILED` for that pair only, never «Совпадает». The result is keyed
by content (`comparison_sheet_pair_result`, `UNIQUE (project_uid, content_key)`, `ALGO_VERSION` in the key), the bit-packed
mask is written once before its row and only for a pair that is not `same`. Two entry points (a function and the `pair_result`
work kind with its enqueue helper) are exported for `CMP-SERIES-01`. The engine is measured, numbers only, on the real set.

## Depends on
- CMP-SEAL-C1 (merged on `integration/compare-modules`): the table `comparison_sheet_pair_result`, the schemas of the result
  members, contract `1.10.0`, migration `0039_comparison_core`
- CMP-PROFILE-01 (merged): `PageProfileReader`, `PageProfileData`, `registration_dpi`, `SubprocessChildRunner`, `ChildLimits`
- CMP-WORK-01 and CMP-PROFILE-QUEUE-01 (merged): `HANDLER_FACTORIES`, `WorkHandler`, `ComparisonWorkRepository.enqueue`
- CMP-FIXTURES-01 (merged): `fixtures/comparison` with its answer keys

## Frozen inputs
- domain contract: `contracts/domain/v1/**` unchanged
- API contract: `contracts/api/v1/openapi.json` `1.10.0`, 131 paths / 148 operations / 432 schemas (unchanged; no operation is implemented by this lane)
- analysis/comparison/event contract: ADR-0025 decisions 5, 7 and its addendum, 8, 9, 10, 15, 16, 18, 20, 23 and both addenda; the wave brief `docs/program/dispatch/CMP-WAVE-C1.md` section 4 (pair evidence interface v1: mask format 1, the result `jsonb`, the entry points)
- migration head: `0039_comparison_core` (not touched)
- base commit: `d11c13fd` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `scripts/recovery/grant_classification.py` (`SEALED_NOT_YET_WRITTEN`) and `src/auditmanager/comparison/public.py` (`HANDLER_FACTORIES`)
- enumerator_owner: CMP-ENGINE-01 for its own name in each (`comparison_sheet_pair_result`; the `pair_result` factory), in the merge order MATRIX, ENGINE, VIEWER
- totality_query: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/integration/recovery/test_grant_classification.py tests/unit/comparison/work`

## Captured premise evidence
- premise: the base is `d11c13fd` on `integration/compare-modules`: contract `1.10.0`, 131 paths / 148 operations / 432 schemas, `VERSION` `0.9.0`, head `0039_comparison_core`; the original's local clone `/root/projects/PDF-proverka` is absent (the owner is re-cloning it, `D-252`), so its source at commit `23f379fd` is read from the public repository's raw files into a scratch directory

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `.venv/bin/python -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas')"; cat VERSION; grep -n '^revision: str' db/migrations/versions/20261028_0039_comparison_core.py; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.10.0 131 paths 148 operations 432 schemas
  0.9.0
  79:revision: str = "0039_comparison_core"
  d11c13fd01f431bb081ad9f984fc6a3dc615b39e
  ```
- interpretation: equal to the premise of the wave brief (`1.10.0`, 131 / 148 / 432, head `0039_comparison_core`), so the lane did not STOP

### P-02 — the original's source is not on this host, and the pinned commit is reachable
- captured_at: 2026-10-28
- command: `ls -d /root/projects/PDF-proverka; GIT_TERMINAL_PROMPT=0 git ls-remote https://github.com/SU10KAZ/PDF-proverka.git HEAD`
- captured_output:
  ```text
  ls: cannot access '/root/projects/PDF-proverka': No such file or directory
  23f379fd2d5aeb7e7bddb735650e7393c68d4e42	HEAD
  ```
- interpretation: the clone the brief names does not exist, and `23f379fd` is the head of the public repository. The lane read `backend/app/services/version_comparison/{settings,status,engine,registration,textdiff,service,separation,blocks,block_alignment,pdfio,stamp,profile,jobs,parts}.py` at exactly that commit, over HTTPS, into a scratch directory outside the repository; the report cites those files and lines. Nothing from the repository is copied into the tree except numbers and rules, each with its citation.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/engine/**`
- `tests/unit/comparison/engine/**`
- `tests/integration/comparison/engine/**`
- `tools/measure/comparison_engine.py`
- `docs/program/CMP-ENGINE-01.md`
- `docs/program/tasks/CMP-ENGINE-01.md`
- `src/auditmanager/comparison/public.py`
- `scripts/recovery/grant_classification.py`
- `tests/unit/comparison/work/test_composition_unit.py`

## Lane resources
- foundation_instance: `auditmanager-cmp-engine-01`
- postgres_port: `57850`
- s3_api_port: `61850`
- s3_console_port: `61851`
- postgres_db: `auditmanager_cmp_engine_01`
- s3_bucket: `auditmanager-cmp-engine-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`
- `src/auditmanager/bootstrap/**` (`adapters.py`, `composition.py`), `src/auditmanager/api/**` (`ports.py`, routers), the stub registers of `tests/integration/composition/**`
- `src/auditmanager/comparison/work/**` (CMP-WORK-01), `src/auditmanager/comparison/profile/**` (CMP-PROFILE-01) and `src/auditmanager/comparison/profile_queue/**`: the engine uses their names and changes none of them
- `src/auditmanager/workers/**`, `src/auditmanager/jobs/**`, `src/auditmanager/storage/**`, `src/auditmanager/ingest/**`, `src/auditmanager/executors/**`
- `web/**`, global styles

## Non-goals
- any API operation; `comparison_sheet_pair`, `comparison_transition`, `comparison_series` (CMP-SERIES-01 writes them); the tiles of a pair and the viewer (CMP-VIEWER-01); the matrix (CMP-MATRIX-01)
- the permit reconciliation and the parts coverage of a transition (CMP-SERIES-01 post-phases); the AI layers
- the stream-level separation of overlay objects of the original (`separation.py`) and the specification positions (`spec_positions` stays `not_applicable` or `unchecked`, never `checked` by guess; `CMP-VC-SPEC-01`)
- a new dependency, a new table, a new column or a new error code
- the full comparison with the original's statuses on the real set (CMP-MEASURE-01 does it)

## Deliverables
- `src/auditmanager/comparison/engine/**`: `mask_codec.py` (second commit), the child program and its modules, the parent-side service (key, cache, validation, blob-before-row), the `pair_result` handler and its enqueue helper, the exports
- appends to `src/auditmanager/comparison/public.py` (the entry point, the handler factory in `HANDLER_FACTORIES`, the enqueue helper, the codec names) and the removal of `comparison_sheet_pair_result` from `SEALED_NOT_YET_WRITTEN`
- `tools/measure/comparison_engine.py` (numbers only)
- unit tests (container-free) and integration tests (own PostgreSQL and MinIO), mutation proofs for the ADR-0025 safety rules
- the report `docs/program/CMP-ENGINE-01.md`

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/comparison/engine tests/integration/comparison/engine tests/integration/recovery/test_grant_classification.py`
- expected: all pass; after the last code commit `tests/unit` and `tests/contract` (minus the three `D-220` files) still pass

## Integration contract
The integrator and the later lanes can rely on: `auditmanager.comparison.public` exports `compare_sheet_pair(...)` (for a project and two page profiles, either of which may be absent, the result identity: from the cache when the content key exists, otherwise computed in the ceilinged child and written, blob first and then the row), the work kind `pair_result` (payload `{"page_a": "cpr_...", "page_b": "cpr_...", "reasons": [...], "part": ...}`; dedupe key a function of the project and the two profile identities only) with `enqueue_pair_result(...)`, and `encode_mask` / `decode_mask` / `MASK_FORMAT` of `engine/mask_codec.py` (format 1 of the wave brief section 4). The result row holds the status, the reasons, the eight channels and the versioned `result` `jsonb` of the brief; a `same` result holds no mask and no blob; a row never names a blob that was not written. `CMP-SERIES-01` chooses which entry point to use; the engine writes no `comparison_sheet_pair`.

## Failure/idempotency/security cases
- the child overruns its address space, its CPU or its wall clock, or ends by a signal: the pair is `needs_review` with `RENDER_FAILED` and is stored (the cache is keyed by content, so the result is reused until `ALGO_VERSION` changes); the next pair is unaffected
- a profile that is not `ready` (a page that ended without a result, or a page over the pixel cap) gives `needs_review` with `RENDER_FAILED` or `PAGE_TOO_LARGE`, never `same`
- the same pair requested twice, or by two workers at once, writes one row (`UNIQUE (project_uid, content_key)`, `ON CONFLICT DO NOTHING`, the loser reads the winner); the blob is content-addressed, so a loser publishes the same id
- a changed byte of either page changes the key; another project does not share the row; a changed link reason, split part, parameter or `ALGO_VERSION` changes the key
- the blob is `available` before the row names it; a crash between the two leaves an unreferenced blob that a re-run references, never a row that names a missing blob
- a mask decoder refuses a wrong magic, format or layer count, a size over 40 Mpx and a body whose length after a bounded decompression differs from the header's
- a page, profile or path is never an identity of a result; a project that does not own the page profiles is refused (`not_found`)

## Rollback / feature flag
The module flag `AUDITMANAGER_COMPARISON_MODULES` (default `none`) governs the worker: with it off a `pair_result` item stays `queued` and nothing runs. The engine is called only by `CMP-SERIES-01`, which is not merged. Rollback is not merging the lane.

## Handoff
- changed files: `git diff --name-only d11c13fd..HEAD` -- `src/auditmanager/comparison/engine/**` (the codec, the worker's side `service.py` / `key.py` / `repository.py` / `validate.py` / `inputs.py` / `limits.py` / `runner.py` / `handler.py` / `enqueue.py`, and the child under `child/`), `src/auditmanager/comparison/public.py` (appends: the engine's imports, `pair_result_handler` in `HANDLER_FACTORIES`, the new names in `__all__`), `scripts/recovery/grant_classification.py` (`comparison_sheet_pair_result` out of `SEALED_NOT_YET_WRITTEN`), `tools/measure/comparison_engine.py`, `tests/unit/comparison/engine/**` (13 files, 255 tests), `tests/integration/comparison/engine/**` (a conftest and 4 files, 23 tests), this file and `docs/program/CMP-ENGINE-01.md`; no file of the closed kind-set test (`tests/unit/comparison/work/test_composition_unit.py`) needed an edit
- commands/results: the report's section 8 (engine unit 255 and integration 23 passed, the grant classification 35, the three together 313; the whole `tests/unit` 4582 passed and 76 skipped; `tests/contract` minus the three `D-220` files 1310 passed) and section 7 (every mutation proof red then green); the real set in section 6: 59 pairs, 33 by child, none without a result, worst address space 568.6 MiB of 768, worst peak RSS 300.2 MiB, worst time 10.7 s, masks 6 233 092 bytes
- known limits: the report's section 9; the first are that the stream-level separation of overlays is not built (a warning set into the page content gives `PARTIAL_COVERAGE`), that the profile keeps `pdfplumber` lines only and its Merkle omits `/OCProperties`, and that five statements of the answer keys differ from the original's rules (section 5)
- integration notes: the report's section 10 (SERIES, VIEWER, MEASURE-01) and section 11 (the FIX slot); the shared-file hunks are `comparison/public.py` (imports, one factory line, names in `__all__`) and one name removed from `SEALED_NOT_YET_WRITTEN`; merge order MATRIX, ENGINE, VIEWER
