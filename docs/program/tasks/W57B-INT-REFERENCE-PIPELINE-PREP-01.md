# Task W57B-INT-REFERENCE-PIPELINE-PREP-01 — pure W57b reference pipeline

task_id: W57B-INT-REFERENCE-PIPELINE-PREP-01

## Outcome

One pure call validates supplied canonical catalogue bytes against independently
supplied pinned facts, extracts references from numbered PDF text pages,
resolves all five outcomes, and returns the report with only grounded
newer-edition candidates. An inconsistent page source is refused.

## Depends on

- `W57B-INT-REFERENCE-RESOLUTION-PREP-01` — completed extraction and five-outcome resolver.
- `W57B-INT-REFERENCE-OBSERVATION-PREP-01` — completed PDF-text evidence planner.
- `W57B-INT-CATALOGUE-QUERY-PREP-01` — completed canonical byte adapter.

## Frozen inputs

- base commit `e4cf264bc71375f85625d9ab3ad110316815d046`;
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §§B3.1–B3.4;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- existing `CatalogueExpectation`, `ReferencePage`, `ReferenceReport`, `NewerEditionCandidate` pure shapes;
- migration head `0022_findings_v2`; no verified-set/custody read is available here.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the four owned files are absent on the exact base; the catalogue, resolver and observation planner already exist.

### P-01 — exact base and additive paths

- captured_at: 2026-10-15
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/norms/references/pipeline.py tests/integration/norms/references/test_reference_pipeline.py docs/program/tasks/W57B-INT-REFERENCE-PIPELINE-PREP-01.md docs/program/W57B-INT-REFERENCE-PIPELINE-PREP-01.md | wc -l && sha256sum docs/program/dispatch/W57-PLAN.md docs/program/dispatch/CODE-FIRST-TO-BETA.md`
- captured_output:
  ```text
  e4cf264bc71375f85625d9ab3ad110316815d046
  0
  587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1  docs/program/dispatch/W57-PLAN.md
  5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c  docs/program/dispatch/CODE-FIRST-TO-BETA.md
  ```
- interpretation: this task can add a pure bridge on the frozen development base; the output does not prove runtime custody or a reviewed corpus.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/references/pipeline.py`
- `tests/integration/norms/references/test_reference_pipeline.py`
- `docs/program/tasks/W57B-INT-REFERENCE-PIPELINE-PREP-01.md`
- `docs/program/W57B-INT-REFERENCE-PIPELINE-PREP-01.md`

## Forbidden hotspots

Existing reference modules, contracts, migrations, catalogue custody,
runtime/stage registry, API, findings publication, composition root, root
dependencies, global styles, corpus, `CURRENT_STATE.md`, tags and remote refs.

## Non-goals

No verified-set admission, snapshot/custody authentication, PDF parsing,
database write, rule publication, severity, API/UI, paid provider call or beta
acceptance. The local unreviewed slug candidate is not a runtime allowlist.

## Deliverables

Additive pure pipeline, focused outcome and refusal tests, task report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/references/test_reference_pipeline.py tests/integration/norms/references/test_catalogue_query.py tests/integration/norms/references/test_reference_resolution.py tests/integration/norms/references/test_observation_plan.py` — pass;
- compilation, direct task governance, `git diff --check` and exact owned-path proof — pass;
- no full `make gate` under R-135.

## Integration contract

The future deterministic stage supplies one immutable tuple of `ReferencePage`
objects derived from its prepared PDF text layer, with ordered page numbers,
unique labels and contiguous global character starts. It obtains canonical
catalogue bytes through confirmed custody and supplies separately verified
snapshot facts and a reviewed unparsed-slug tuple. This pipeline returns a
`ReferencePipelineResult` with all five report outcomes and only `NEWER`
publication candidates. The stage owns provenance, persistence and report
publication; this function authenticates none of the caller's sources.

## Failure/idempotency/security cases

Wrong catalogue digest/snapshot/listing, duplicate labels, invalid page order,
noncontiguous offsets and unread or invalid text fail closed. Equal inputs
produce equal report and evidence. The function performs no I/O and does not
alter raw comparison evidence.

## Rollback / feature flag

Revert the additive files before runtime wiring; no data rollback or flag.
