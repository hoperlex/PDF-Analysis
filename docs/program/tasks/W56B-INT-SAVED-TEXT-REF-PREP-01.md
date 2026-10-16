# Task W56B-INT-SAVED-TEXT-REF-PREP-01 — select a run-scoped TEXT reference

task_id: W56B-INT-SAVED-TEXT-REF-PREP-01

## Outcome

An unserved, pure W56b check validates a supplied successful
`source_preparation` StageResult envelope for one Run and selects its one
`prepared.text_layer` reference. It then binds supplied bytes to that exact
reference through the existing W56b source-byte/partition check. The future
calling service can use the selector to know which Blob to read under a
current Attempt; this task does no DB/Blob read itself.

## Depends on

- `W56B-INT-TEXT-BYTES-PREP-01` — completed supplied-byte verifier and window preflight.

## Frozen inputs

- base commit: `4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1`
- base ref at dispatch: `origin/dev`, code-first candidate 44;
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

- premise: the current W56b supplied-byte verifier consumes an `ArtifactRef`
  but cannot select it from the saved stage. A same-context geometry seam
  already validates a supplied run-scoped StageResult; W56b text can add a
  separate selector without editing any W54/W57 or shared hotspot.

### P-01 — adopted code-first boundary

- captured_at: 2026-10-16
- command: `sed -n '140,143p' docs/program/dispatch/CODE-FIRST-TO-BETA.md`
- captured_output:
  ```text
- W56b требует ещё не утверждённых границ vision, region и бюджета. До
  решения можно реализовать нейтральные storage/evidence primitives и
  recorded harness, но не закреплять выдуманный модельный контракт.
- Выделенного `W56B-PLAN.md` и task-планов W58–W63 на `origin/dev` пока
  ```
- interpretation: this is evidence plumbing only, with no provider/effect rule.

### P-02 — exact base paths

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only 4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1 src/auditmanager/analysis/text/source_bytes.py src/auditmanager/analysis/text/saved_window_custody.py tests/integration/analysis_text/test_saved_window_custody.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/source_bytes.py
  ```
- interpretation: this task adds a text-specific stage/reference seam and test;
  the completed source-byte module remains untouched.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/saved_window_custody.py`
- `tests/integration/analysis_text/test_saved_window_custody.py`
- `docs/program/tasks/W56B-INT-SAVED-TEXT-REF-PREP-01.md`
- `docs/program/W56B-INT-SAVED-TEXT-REF-PREP-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, W54/W57 paths, existing W56b modules,
`runs/**`, `jobs/**`, storage adapters, provider/rate adapters, root
dependency/lock files, composition root, global styles, API/UI, stage
registry, `CURRENT_STATE.md`, remote refs and tags.

## Non-goals

No assertion that the supplied wrapper actually came from DB, no current
Attempt check, Blob read, request/model/budget/effect policy, response
semantics, finding/citation publication, route, contract, migration,
runtime stage activation or beta acceptance.

## Deliverables

One additive W56b analysis/text module, focused offline tests and paired
report. No existing production module is changed.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis_text/test_saved_window_custody.py tests/integration/analysis_text/test_source_bytes.py tests/integration/analysis_text/test_window_cohort.py` — pass;
- Python compilation, direct task governance, frozen SHA-256 readback,
  `git diff --check` and exact four-path inspection — pass;
- no Docker/PostgreSQL/S3/proxy/full gate.

## Integration contract

A future W56b calling service holds the current Attempt authority, fetches
the Run and exactly one successful `source_preparation` StageResult by that
Run ID, and attaches the query's Run ID to `RunScopedTextStage`. It calls
`select_run_text_layer_ref`, bounded-reads that exact Blob with expected
SHA/size, calls `check_run_text_window_input`, then rechecks Attempt, Run and
stage row before any effect. This pure seam refuses foreign/duplicate/extra
references and does not itself attest DB provenance or authority. The
document-text character ceiling is determined separately by approved policy.

## Failure/idempotency/security cases

Wrong Run/stage/version/status, malformed/duplicate/foreign roles and Blob
IDs, missing required references and changed supplied bytes refuse. An
oversized page keeps the existing preflight error. Stable inputs return
identical immutable values without I/O.

## Rollback / feature flag

Remove the additive module/test before wiring; no data rollback or runtime
flag is needed because no served caller exists.

## Handoff

- changed files/checks/limits: paired report;
- contracts: none;
- next: the calling-service owner must implement authoritative Run/StageResult
  reads, Attempt fencing and bounded Blob read before W56b stage activation.
