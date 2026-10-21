# Task W56B-INT-WINDOW-ANCHOR-PREP-01 — bind a TEXT quote to its planned window

task_id: W56B-INT-WINDOW-ANCHOR-PREP-01

## Outcome

A pure W56b evidence check refuses an incomplete or forged saved TEXT window plan
and any quote claiming a page outside the response's assigned window. An exact
quote inside that window resolves through the existing page anchor rule to the
original document-global Unicode offsets. This primitive is unserved.

## Depends on

- `W56B-INT-CHUNK-PREFLIGHT-PREP-01` — completed saved TEXT partition.

## Frozen inputs

- base commit: `f0580e089867ba6a9380a48dfca19a23e47f6788`
- base ref at dispatch: `origin/dev`, candidate 37;
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

- premise: W56b includes chunked analysis but the provider, budget, effects and
  cross-window decisions await a dedicated freeze. A neutral input/evidence
  primitive may be implemented without making those decisions.

### P-01 — adopted code-first boundary

- captured_at: 2026-10-16
- command: `sed -n '140,144p' docs/program/dispatch/CODE-FIRST-TO-BETA.md`
- captured_output:
  ```text
- W56b требует ещё не утверждённых границ vision, region и бюджета. До
  решения можно реализовать нейтральные storage/evidence primitives и
  recorded harness, но не закреплять выдуманный модельный контракт.
- Выделенного `W56B-PLAN.md` и task-планов W58–W63 на `origin/dev` пока
  нет: roadmap прямо называет эти слои черновыми. Их freeze и grants
  ```
- interpretation: only the neutral evidence primitive is granted; this task
  does not set a request budget, model, effect policy or contradiction rule.

### P-02 — existing page anchor and chunk files at exact base

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only f0580e089867ba6a9380a48dfca19a23e47f6788 src/auditmanager/analysis/text/anchors.py src/auditmanager/analysis/text/chunk_preflight.py src/auditmanager/analysis/text/window_anchor.py`
- captured_output:
  ```text
src/auditmanager/analysis/text/anchors.py
src/auditmanager/analysis/text/chunk_preflight.py
  ```
- interpretation: the window binding is additive and can reuse the existing
  page quote rule without changing its publication vocabulary.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/window_anchor.py`
- `tests/integration/analysis_text/test_window_anchor.py`
- `docs/program/tasks/W56B-INT-WINDOW-ANCHOR-PREP-01.md`
- `docs/program/W56B-INT-WINDOW-ANCHOR-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing analysis modules, provider/rate adapters,
root dependency/lock files, composition root, global styles, API/UI,
`runs/executor.py`, `CURRENT_STATE.md`, remote refs and tags.

## Non-goals

No budget calculation, overlap, cross-window contradiction resolution, model
call, effect journal, saved Run/Attempt read, finding publication, new error
code, stage registration, provider/vision policy, DB/S3 access or beta claim.

## Deliverables

One additive pure module, focused offline tests and a paired report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis_text/test_window_anchor.py tests/integration/analysis_text/test_chunk_preflight.py` — pass;
- Python compilation, direct task governance, frozen SHA-256 readback,
  `git diff --check` and exact four-path inspection — pass;
- no Docker/PostgreSQL/S3/provider/full gate while W55b gate owns this host.

## Integration contract

The caller first obtains the checksum-verified saved `TextLayer`, partitions it
under an independently reviewed request ceiling, and binds the plan to one
current Run/Attempt. For each recorded window response, pass that complete
plan and its index. A proposed page outside the window or any changed/missing
window fails closed; an in-window quote uses the existing literal page resolver
and returns original global offsets or an existing ungrounded result. This
check neither authorizes a call nor publishes the resolved anchor.

## Failure/idempotency/security cases

Missing, duplicate, reordered, foreign, text-mutated or partial windows refuse
before quote resolution. An invalid index/page/quote refuses. Repeated inputs
return equal results without I/O or state changes. Exact quote matching retains
the existing no-renormalization rule.

## Rollback / feature flag

Remove the additive module/test before wiring; no data rollback or feature
flag is needed because no served caller exists.

## Handoff

- changed files/checks/limits: paired report;
- contracts: none;
- next: integrate only as an unserved evidence primitive, then freeze W56b
  budget, effects, cross-window semantics and real saved-input acceptance.
