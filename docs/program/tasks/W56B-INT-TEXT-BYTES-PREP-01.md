# Task W56B-INT-TEXT-BYTES-PREP-01 — check supplied TEXT bytes before partition

task_id: W56B-INT-TEXT-BYTES-PREP-01

## Outcome

A pure, unserved W56b preflight verifies a supplied `prepared.text_layer`
Blob payload against its `ArtifactRef`, the frozen version page count and
artifact shape. It then returns the original text layer and complete page
windows or refuses the whole input before any model call. A character ceiling
is supplied by a future, separately approved budget calculation.

## Depends on

- `W56B-INT-CHUNK-PREFLIGHT-PREP-01` — completed page partition.

## Frozen inputs

- base commit: `6f1307412c94de45e67ffdeba71506dc5a0aa8fb`
- base ref at dispatch: `origin/dev`, code-first candidate 41;
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

- premise: code-first grants neutral W56b input/evidence primitives while
  model, vision, region and budget rules remain unapproved. The exact base has
  page partition but no profile-independent supplied-byte verifier for it.

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
- interpretation: this task checks supplied bytes and source boundaries; it
  does not define a request, provider profile or cost limit.

### P-02 — exact source paths

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only 6f1307412c94de45e67ffdeba71506dc5a0aa8fb src/auditmanager/analysis/text/chunk_preflight.py src/auditmanager/analysis/text/source_bytes.py tests/integration/analysis_text/test_source_bytes.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/chunk_preflight.py
  ```
- interpretation: the supplied-byte module/test are additive. Existing AR v2
  recorded-input checks are profile-specific and are not changed or imported.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/source_bytes.py`
- `tests/integration/analysis_text/test_source_bytes.py`
- `docs/program/tasks/W56B-INT-TEXT-BYTES-PREP-01.md`
- `docs/program/W56B-INT-TEXT-BYTES-PREP-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, W54 paths, existing analysis producers
and consumers, provider/rate adapters, root dependency/lock files,
composition root, global styles, API/UI, `runs/executor.py`, stage registry,
`CURRENT_STATE.md`, remote refs and tags.

## Non-goals

No claim that a supplied reference came from a saved StageResult or current
Attempt; no DB/Blob read, model/response contract, prompt, price, provider,
ceiling derivation, effect journal, window response, finding/citation
publication, route, migration, runtime stage or beta acceptance.

## Deliverables

One additive pure source-byte module, focused offline tests and paired report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis_text/test_source_bytes.py tests/integration/analysis_text/test_chunk_preflight.py tests/integration/analysis_text/test_window_cohort.py` — pass;
- Python compilation, direct task governance, frozen SHA-256 readback,
  `git diff --check` and exact four-path inspection — pass;
- no Docker/PostgreSQL/S3/proxy/full gate for this pure task.

## Integration contract

The future W56b caller must obtain the exact text-layer reference from a
successful run-scoped `source_preparation` StageResult, read its Blob under
the current Attempt and limit the byte count before this function. Pass
the frozen version UID/page count and a separately approved positive
**document-text** character ceiling. This function checks the supplied bytes,
canonical JSON, role/version/shape, text-layer offsets and complete partition.
It returns no authority to call a model or publish a finding. A caller must
also use the W56b reply cohort check on authenticated responses.

## Failure/idempotency/security cases

Wrong role/media/digest/size, noncanonical JSON, foreign version, malformed
page coordinates, page count mismatch and blank/oversized text refuse. The
same inputs return equal immutable values without I/O. No silent truncation,
OCR merge or fallback occurs.

## Rollback / feature flag

Remove this additive module/test before wiring; no data rollback or runtime
flag is needed because no served caller exists.

## Handoff

- changed files/checks/limits: paired report;
- contracts: none;
- next: integrate as an unserved W56b input primitive, then require the
  W56b budget/effects/provider freeze and real saved-input acceptance.
