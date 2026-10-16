# Task W56B-INT-RUN-TEXT-READ-01 — read saved TEXT under current Attempt

task_id: W56B-INT-RUN-TEXT-READ-01

## Outcome

An unserved read-only W56b service obtains one saved `prepared.text_layer`
from the exact Run's successful source stage, reads that Blob under an explicit
input-byte ceiling, checks complete TEXT windows and rechecks current Attempt,
Run, Version and StageResult before returning. No model or provider call occurs.

## Depends on

- `W56B-INT-SAVED-TEXT-REF-PREP-01` — completed pure run-scoped stage/ref and
  supplied-byte window check at `cf4a9a967c68d7c7ee892a934ef8ed8f7d3d5b3a`.

## Frozen inputs

- base commit: `cf4a9a967c68d7c7ee892a934ef8ed8f7d3d5b3a`
- base: local completed W56b task candidate; parent dev at grant was
  `4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1`;
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

- premise: the pure W56b stage selector and byte checker exist at the exact
  base; the analogous IMAGE service demonstrates existing Run/Attempt/Blob
  ports, but no TEXT read service exists. The integrator granted this exact
  path set and owns the one public export hotspot for this lane.

### P-01 — exact service and public paths

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only cf4a9a967c68d7c7ee892a934ef8ed8f7d3d5b3a src/auditmanager/analysis/public.py src/auditmanager/runs/geometry_crop_input.py src/auditmanager/runs/text_window_input.py tests/integration/runs/test_text_window_input.py`
- captured_output:
  ```text
  src/auditmanager/analysis/public.py
  src/auditmanager/runs/geometry_crop_input.py
  ```
- interpretation: the TEXT service/test are additive; `analysis/public.py`
  requires a narrow export addition to avoid deep imports across contexts.

### P-02 — adopted W56b code-first boundary

- captured_at: 2026-10-16
- command: `sed -n '140,143p' docs/program/dispatch/CODE-FIRST-TO-BETA.md`
- captured_output:
  ```text
- W56b требует ещё не утверждённых границ vision, region и бюджета. До
  решения можно реализовать нейтральные storage/evidence primitives и
  recorded harness, но не закреплять выдуманный модельный контракт.
- Выделенного `W56B-PLAN.md` и task-планов W58–W63 на `origin/dev` пока
  ```
- interpretation: this task only reads checked source bytes and applies an
  externally supplied character ceiling; it chooses no model or cost policy.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none
- integration grant: direct integrator message on 2026-10-16 for exactly the
  named paths and narrow public exports; W57a remains inside `ar_v3`.

## Allowed paths

- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/text_window_input.py`
- `tests/integration/runs/test_text_window_input.py`
- `docs/program/tasks/W56B-INT-RUN-TEXT-READ-01.md`
- `docs/program/W56B-INT-RUN-TEXT-READ-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, W54/W57 paths, other W56b modules,
`runs/repository.py`, `jobs/**`, storage and documents adapters, provider/rate
adapters, root dependency/lock files, composition root, global styles,
API/UI, stage registry, `CURRENT_STATE.md`, remote refs and tags.

## Non-goals

No provider call, model/request/response choice, price or character-ceiling
derivation, journal/effect reservation, served route, finding/citation write,
contract, migration, runtime stage activation, full beta gate or release.

## Deliverables

One additive runs read service and fake-port tests, narrow exports of the
completed W56b pure types/functions in `analysis/public.py`, paired report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_text_window_input.py tests/integration/analysis_text/test_saved_window_custody.py tests/integration/analysis_text/test_source_bytes.py` — pass;
- Python compilation, direct task governance, frozen SHA-256 readback,
  `git diff --check` and exact five-path inspection — pass;
- no Docker/PostgreSQL/S3/proxy/full gate.

## Integration contract

The caller supplies its SQLAlchemy transaction, current `AttemptAuthority`,
BlobStore and **explicit positive** `max_input_bytes` and
`max_chunk_characters`. The service calls `JobRepository.require_current`
before reads; loads the exact running Run, frozen Version and exactly one
successful saved `source_preparation` row; selects the W56b checked ref;
refuses an oversized Blob before open; streams the full object with the ref's
SHA/size and a byte ceiling; checks the bytes and all windows; then repeats
Attempt, Run, Version and StageResult reads and refuses any changed value.
Locks are held by the caller's transaction during object read. Returning
checked windows does not reserve authority for a later model effect.

## Failure/idempotency/security cases

Stale Attempt, changed/non-running/foreign Run or Version, absent/duplicate/
changed stage row, invalid stage refs, invalid ceilings, absent/corrupt/large
Blob and invalid/oversized text refuse with no partial result. Stable inputs
return equal values, perform no write and disclose no path, key or credential.

## Rollback / feature flag

Remove the additive service/test and exports before wiring; no data rollback
or runtime flag is needed because no served caller exists.

## Handoff

- changed files/checks/limits: paired report;
- contracts: none;
- next: W56b stage/effect owner must obtain approved provider and budget
  policy, reacquire current authority and journal each later call.
