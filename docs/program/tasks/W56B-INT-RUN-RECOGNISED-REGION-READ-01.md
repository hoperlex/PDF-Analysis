# Task W56B-INT-RUN-RECOGNISED-REGION-READ-01 — read saved OCR region evidence

task_id: W56B-INT-RUN-RECOGNISED-REGION-READ-01

## Outcome

An unserved read-only service obtains the recognised-text and portal-block
artifacts from the exact Run's two successful saved stages, checks their Blob
bytes under one explicit ceiling, binds a supplied OCR quote to its saved
textless page and region, and rereads current Attempt and all saved inputs
before returning. No provider call or finding publication occurs.

## Depends on

- `W56B-INT-RECOGNISED-REGION-PREP-01` — completed pure OCR region binder.
- `W56B-INT-RUN-TEXT-READ-01` — completed run/Attempt-fenced source read pattern.
- `W56B-INT-RUN-CROP-READ-01` — completed run/Attempt-fenced geometry read pattern.

## Frozen inputs

- base commit: `95de4f6b4e10a8b60f57ae84ab66156917c7b96c`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- migration head: `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed pure binder needs checksum-verified same-run source
  and geometry documents and the Version's stored textless-page list; no
  run-scoped caller supplies those together at this base.

### P-01 — exact base paths

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only 95de4f6b4e10a8b60f57ae84ab66156917c7b96c src/auditmanager/analysis/recognised/region_candidate.py src/auditmanager/runs/recognised_region_input.py src/auditmanager/runs/text_window_input.py`
- captured_output:
  ```text
  src/auditmanager/analysis/recognised/region_candidate.py
  src/auditmanager/runs/text_window_input.py
  ```
- interpretation: pure binding and the analogous saved read exist; the new
  run-side service is additive.

### P-02 — adopted W56b boundary

- captured_at: 2026-10-16
- command: `sed -n '140,143p' docs/program/dispatch/CODE-FIRST-TO-BETA.md`
- captured_output:
  ```text
- W56b требует ещё не утверждённых границ vision, region и бюджета. До
  решения можно реализовать нейтральные storage/evidence primitives и
  recorded harness, но не закреплять выдуманный модельный контракт.
- Выделенного `W56B-PLAN.md` и task-планов W58–W63 на `origin/dev` пока
  ```
- interpretation: this task binds existing evidence only; it chooses no
  model, citation policy or cost budget.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none
- integration grant: direct integrator message on 2026-10-16 for these five
  paths and narrow `analysis/public.py` exports; local commit/handoff only.

## Allowed paths

- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/recognised_region_input.py`
- `tests/integration/runs/test_recognised_region_input.py`
- `docs/program/tasks/W56B-INT-RUN-RECOGNISED-REGION-READ-01.md`
- `docs/program/W56B-INT-RUN-RECOGNISED-REGION-READ-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, W54/W57/W58 paths, producer/binder
modules, `runs/repository.py`, jobs/storage/documents adapters, stage
registry, provider/rate adapters, composition root, API/UI, root
dependencies/lockfiles, global styles, `CURRENT_STATE.md`, remote refs/tags.

## Non-goals

No citation status or public schema choice, vision/model request, price or
provider budget, effect journal, served route, finding write, W58 debt code,
contract, migration, runtime activation, real DB/S3 acceptance or beta gate.

## Deliverables

One additive run-side read service, narrow export of the completed pure OCR
region binder, fake-port regressions and paired report.

## Required tests

- focused new and existing OCR region, TEXT and crop read suites — pass;
- Python compilation, direct task governance, frozen SHA-256 readback,
  whitespace and exact five-path proof — pass;
- no Docker/PostgreSQL/S3/proxy/full gate.

## Integration contract

The caller supplies its SQLAlchemy transaction, current `AttemptAuthority`,
BlobStore, and an explicit positive aggregate byte ceiling. The service
fences Attempt; reads the exact running Run, its frozen Version and exactly
one successful `source_preparation` and `page_geometry_extraction` row; checks
complete saved ref roles and an OCR-capable Version; refuses oversized total
input before storage; reads the exact two Blobs by saved SHA-256/size, checks
canonical role/version-bound JSON and calls the pure binder. It then fences
Attempt again and rereads Run, Version and both StageResults. Any change
refuses. A returned candidate is not an authorization for a later effect.

## Failure/idempotency/security cases

Stale Attempt, changed/nonrunning/foreign Run or Version, absent/duplicate/
changed stage, invalid or oversized refs, corrupt Blob, noncanonical document,
non-textless page, non-TEXT block, ambiguous OCR quote and invalid geometry
refuse with no partial candidate or silent fallback. Stable repeated reads
agree and make no write. Error details contain no Blob key or credential.

## Rollback / feature flag

Remove the additive service/test and public exports before wiring; no data
rollback or runtime flag is needed because no served caller exists.

## Handoff

- changed files/checks/limitations: paired report;
- contracts: none;
- next: W56b policy/effect owner must separately authorize citation status,
  provider dispatch and persisted publication.
