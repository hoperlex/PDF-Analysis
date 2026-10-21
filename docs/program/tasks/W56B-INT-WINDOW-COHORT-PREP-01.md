# Task W56B-INT-WINDOW-COHORT-PREP-01 — bind a complete TEXT reply cohort

task_id: W56B-INT-WINDOW-COHORT-PREP-01

## Outcome

A pure, unserved W56b check requires exactly one ordered supplied reply for
every saved TEXT window, including a reply with no quote claims. It resolves
each claim only on that reply's window page and retains document-global Unicode
offsets or the existing explicit unresolved reason. Missing, duplicate,
reordered, foreign-page and forged-window inputs refuse the whole cohort.

## Depends on

- `W56B-INT-CHUNK-PREFLIGHT-PREP-01` — completed page partition.
- `W56B-INT-WINDOW-ANCHOR-PREP-01` — completed saved-window quote boundary.

## Frozen inputs

- base commit: `f0b12ea705a9ccb476b5b69a5797de7d3731f543`
- base ref at dispatch: `origin/dev`, code-first candidate 40;
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

- premise: W56b permits a neutral evidence primitive before its vision,
  region and budget rulings. The exact base already has window partition and
  per-quote binding, but no cohort check.

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
- interpretation: this task may check supplied evidence inputs, but may not
  choose the model, request budget or response contract.

### P-02 — exact source paths

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only f0b12ea705a9ccb476b5b69a5797de7d3731f543 src/auditmanager/analysis/text/chunk_preflight.py src/auditmanager/analysis/text/window_anchor.py src/auditmanager/analysis/text/window_cohort.py tests/integration/analysis_text/test_window_cohort.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/chunk_preflight.py
  src/auditmanager/analysis/text/window_anchor.py
  ```
- interpretation: the cohort module and test are additive; the existing
  window validator can be extracted from `window_anchor.py` without changing
  its quote behavior.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/window_anchor.py`
- `src/auditmanager/analysis/text/window_cohort.py`
- `tests/integration/analysis_text/test_window_cohort.py`
- `docs/program/tasks/W56B-INT-WINDOW-COHORT-PREP-01.md`
- `docs/program/W56B-INT-WINDOW-COHORT-PREP-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, stage registry, provider/rate adapters,
root dependency/lock files, composition root, global styles, API/UI,
`runs/executor.py`, W57a/W58 modules, `CURRENT_STATE.md`, remote refs and tags.

## Non-goals

No model/response-schema choice, prompt rendering, request ceiling, paid call,
effect journal, persisted Run/Attempt/Blob read, cross-window contradiction or
finding merge, citation/finding publication, route, contract, migration,
runtime stage activation or beta acceptance.

## Deliverables

One additive pure cohort module, a reusable validation extraction in the
existing W56b window anchor, focused tests and paired report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis_text/test_window_cohort.py tests/integration/analysis_text/test_window_anchor.py tests/integration/analysis_text/test_chunk_preflight.py` — pass;
- Python compilation, direct task governance, frozen SHA-256 readback,
  `git diff --check` and exact five-path inspection — pass;
- no Docker/PostgreSQL/S3/proxy/full gate for this isolated pure task.

## Integration contract

The future W56b caller supplies one checksum-verified saved `TextLayer`, its
complete partition and **already authenticated** reply claims from the
current Run/Attempt's effect journal. The binder rechecks the whole window
plan, demands one ordered reply per window, and resolves each literal quote
against the source page. An empty reply is distinct from an absent reply.
The result preserves unresolved claims; it does not certify provider origin or
authorize publication. The caller must establish those separately.

## Failure/idempotency/security cases

Missing/extra/duplicate/reordered replies, malformed claims, a cited page in
another window and a changed/partial source plan refuse. Identical inputs
return equal immutable values without I/O. An absent literal quote remains
unresolved, not silently omitted.

## Rollback / feature flag

Remove the additive cohort module/test and revert the validator extraction
before wiring; no data rollback or flag is needed because no served caller exists.

## Handoff

- changed files/checks/limits: paired report;
- contracts: none;
- next: integrate only as an unserved evidence primitive, then freeze W56b
  provider, budget, effect journal, response and cross-window semantics.
