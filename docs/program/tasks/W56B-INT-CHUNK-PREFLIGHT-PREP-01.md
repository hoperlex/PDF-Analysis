# Task W56B-INT-CHUNK-PREFLIGHT-PREP-01 — partition saved TEXT without changing evidence coordinates

task_id: W56B-INT-CHUNK-PREFLIGHT-PREP-01

## Outcome

A pure, unserved W56b preflight returns a complete deterministic partition of
the saved text layer into whole-page windows below an explicit positive text
character ceiling. It refuses a page too large for that ceiling before any
model call or partial plan can be returned. Every window retains the saved
document-global Unicode offsets for later citation checks.

## Depends on

- `W55B-BUDGET-01` — completed one-call input budget and up-front refusal.

## Frozen inputs

- base commit: `77d39efedd4d5c74582a02dbf5ea86acb4b054f7`
- base ref at dispatch: `origin/dev`, candidate 33;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- migration head: `0023_norm_citations`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: G-11 places chunking in W56b, while the code-first route permits
  neutral input primitives before model/region/budget rulings. No W56b chunk
  module exists at the exact base.

### P-01 — planned W56b scope and unresolved inputs

- captured_at: 2026-10-16
- command: `sed -n '430,446p' docs/program/dispatch/W56-PLAN.md`
- captured_output:
  ```text
**In:** `block_analysis` over W55b's crops (one crop per call, as legacy); region evidence end to end (the
`Evidence` union, `finding_evidence` region columns, grounding, the CSV region columns, the crop-and-box
viewer, crop serving by run or evidence); recognised-text citations marked as such (H-7); chunked text
analysis lifting W55b's input budget (G-11); merge of block, chunk and text observations (the region-versus-
span link and the canonical choice across evidence kinds); **the critic** (`finding_review`, H-4, H-10) over
text and block findings, annotate-only, its failure semantics against FS-04 (`partial` unless the owner
amends it); **W53's resume rule and watchdog for multi-call stages** — completed effects reused, unknown ones
counted at their maximum (as W54's repair journal), the watchdog sized by the run's stage plan;
**«Настройки анализа»** — presets kept by an administrator, picked by an expert per run, recorded by the run
(A-8), with model choices constrained by the per-gateway identity pins, replacing
`AUDITMANAGER_ANALYSIS_PROFILE_ID`.

**Inputs before its plan:** the W54 vision probe (image acceptance, model, price per crop); the owner's
drawing-analysis budget (G-3); an owner poll on region granularity (whole block, model-proposed box,
text-layer words where present — 18 of 47 АР blocks have them), the vision ceiling mechanism and model,
cross-chunk contradictions (legacy's summary-sheet skeleton or a new consistency stage), the critic's
failure semantics, presets per stage and the setting's retirement, and the live-spend exception its
  ```
- interpretation: the partition is a neutral input primitive, not approval
  of a model, window size, cross-chunk policy or paid multi-call stage.

### P-02 — exact base has no chunk preflight

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only 77d39efedd4d5c74582a02dbf5ea86acb4b054f7 src/auditmanager/analysis/text/chunk_preflight.py tests/integration/analysis_text/test_chunk_preflight.py`
- captured_output:
  ```text
  ```
- interpretation: these two exact paths are additive; this does not prove
  runtime readiness.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/chunk_preflight.py`
- `tests/integration/analysis_text/test_chunk_preflight.py`
- `docs/program/tasks/W56B-INT-CHUNK-PREFLIGHT-PREP-01.md`
- `docs/program/W56B-INT-CHUNK-PREFLIGHT-PREP-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, existing analysis consumers/producers,
provider and pricing adapters, root dependency/lock files, composition root,
global styles, API/UI, runs/executor, `CURRENT_STATE.md`, remote refs and tags.

## Non-goals

No model or token-cost estimate, settled character ceiling, prompt rendering,
overlap, splitting within an oversized page, OCR inclusion, normative context,
cross-chunk consistency, stage registration, effect journal, resume, finding,
citation publication, external I/O, full gate or beta claim.

## Deliverables

One additive pure module, focused offline tests and paired report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis_text/test_chunk_preflight.py` — pass;
- Python compilation, direct task governance, frozen SHA-256 readback,
  `git diff --check` and exact four-path inspection — pass;
- no Docker/PostgreSQL/S3/provider/full gate while W55b release gate owns the host.

## Integration contract

The future W56b caller supplies a checksum-verified saved `TextLayer` and a
positive maximum **document text** character count per request after separately
reserving prompt, schema, normative context and output capacity. The preflight
checks the entire layer, returns ordered immutable windows of full pages and
global offsets, or refuses the whole plan. The caller must bind the saved
artifact to one current Run/Attempt and establish a reviewed cost/effect and
cross-window policy before any provider call. No window is a finding or a
publication authority.

## Failure/idempotency/security cases

Nonpositive/noninteger ceiling, malformed or forged text layer, all-blank
layer and any page above the ceiling refuse. Empty pages alongside text are
retained in a neighbouring window. No text is re-normalized or silently
truncated; identical input and ceiling produce equal tuples without I/O.

## Rollback / feature flag

Remove the additive module/test before wiring; no data rollback or feature
flag is needed because no served caller exists.

## Handoff

- changed files/checks/limits: paired report;
- contracts: none;
- next: integrate as an unserved primitive only, then freeze W56b provider,
  budget, effect journal, cross-chunk and citation rules before activation.
