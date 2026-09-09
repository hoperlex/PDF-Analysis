# Task P2-ENG-01 — stage engine and the three deterministic preparation stages

> **Status: specified; not dispatchable.** Planned for P02.

## Outcome

`source_preparation`, `page_geometry_extraction` and `document_context_build` run from the
source blob and emit every registry-required output role as a checksum-verified artifact,
so `text_analysis` and the evidence gate have anchorable inputs.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated, and until owner decision `OD-04` fixes the page-crop policy:

  - `P2-DOM-01` — the P02 migration head and domain primitives
  - `P2-BHV-01` — the AR corpus and its expected-issues manifest

## Frozen inputs

- analysis contract: `stage-registry.json` per-stage required inputs and outputs, its
  status semantics and per-stage status policy, plus the stage-result and package schemas
- storage: the P01 BlobStore port
- migration head: the P02 head, read only
- base commit: the accepted `P2-DOM-01` integration commit

## Allowed paths

- `src/auditmanager/analysis/engine/**`, `src/auditmanager/analysis/ports/**`,
  `src/auditmanager/analysis/stages/**`
- `src/auditmanager/analysis/public.py`, `src/auditmanager/analysis/__init__.py`,
  `src/auditmanager/analysis/README.md`
- `tests/integration/analysis_engine/**`, `tests/contract/analysis_packages/**`
- `docs/navigation/incidents/p2-eng-01.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P2-ENG-01.md`
- `docs/navigation/entries/p2-eng-01.json`

## Forbidden hotspots

- `src/auditmanager/analysis/text/**`, owned by `P2-AI-01`
- `db/migrations/**`, root locks, the composition root and the `Makefile`
- `src/auditmanager/{documents,ingest,storage,runs,exports,findings,decisions,api}/**`,
  `contracts/**`, `fixtures/**`

## Non-goals

- No model call, prompt, visual detection or OCR.
- No block analysis, finding merge, finding review, finding correction or norm
  verification.
- No legacy stage alias resolution: the control plane passes canonical stage identity only.

## Deliverables

- an in-process stage-runner seam taking the stage inputs by `blob_id` and returning a
  `StageResult` conformant to `stage-result.schema.json`, which requires no attempt
  authority. The seam does not construct a `JobPackage` or a `ResultPackage`: those
  envelopes exist for remote dispatch, which PC-01 does not perform
- `source_preparation` producing the page inventory and the text layer with stable
  character offsets, both published as blobs
- `page_geometry_extraction` producing the block index with page, bounding box and
  text-span anchors, and the page-crop manifest under the policy fixed by `OD-04`
- `document_context_build` producing the document graph over stable block identities
- fail-closed status mapping: a missing required input or output is `failed` with a typed
  error, and `partial` and `skipped` are structurally impossible for these three stages
- a stage registry loader reading canonical stage identity and version from the contract
  and refusing an unknown stage

## Required tests

- Command: `make foundation`
  Expected: exit `0`.
- Command: `.venv/bin/pytest tests/contract/analysis_packages`
  Expected: exit `0`; every emitted `StageResult` validates against the standalone
  `stage-result` schema, and both a `succeeded` result carrying an error and a `failed`
  result missing an error are rejected. No `ResultPackage` and no `JobPackage` is emitted
  or validated: this task creates neither, so neither appears in its evidence.
- Command: `.venv/bin/pytest tests/integration/analysis_engine`
  Expected: exit `0` on the baseline fixture. The suite asserts that all three stages report
  `succeeded` with every required output role present as an artifact carrying a blob
  identity and checksum; that two runs over the same source produce byte-identical text
  layer and block index bytes; that every seeded quotation is locatable in the text layer at
  its declared page; that an unreadable source blob yields `failed` with
  `analysis_input_invalid` and no artifact; and that no artifact reference contains an
  object key, URL or credential.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

`P2-RUN-01` calls the stage runner and persists the returned stage results without reaching
inside a stage. `P2-AI-01` registers `text_analysis` on the same seam and receives the text
layer and document graph by blob identity. `P2-FND-01` resolves evidence anchors against the
text layer and block index only.

## Failure/idempotency/security cases

- Deterministic re-execution over identical inputs produces identical artifact checksums.
- `GJ-02-EO-11` and `GJ-02-EO-13`: stage identity and skippability come only from the
  versioned registry.
- The engine writes no canonical metadata row.

## Rollback / feature flag

Not applicable. The page-crop policy is a declared profile field with its own test, not a
runtime flag.

## Estimate

Effort P50 3.0 person-days, P80 5.5 person-days. Add 1.0 P50 and 2.0 P80 if `OD-04`
requires rendered crops rather than a declared empty manifest. Basis: three deterministic stages over a pinned extraction library. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- the artifact shapes for the text layer, block index and document graph
- the stage-runner signature
- the page-crop policy actually implemented and its owner-decision reference
