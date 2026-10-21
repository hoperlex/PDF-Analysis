# Task W57B-INT-REFERENCE-OBSERVATION-PREP-01 — anchor newer-edition rule observations

task_id: W57B-INT-REFERENCE-OBSERVATION-PREP-01

## Outcome

The W57b pure resolver's `NEWER` results become typed, PDF-text-anchored
publication candidates. Other reference outcomes remain report-only.

## Depends on

- `W57B-INT-REFERENCE-RESOLUTION-PREP-01` — completed pure five-outcome resolver.
- `W57B-INT-CATALOGUE-SLUG-AUDIT-01` — completed parser coverage audit.

## Frozen inputs

- base commit and `origin/dev`: `eca8597b4b59a06371cfaf709df7bee8509a604f`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §B3.2–B3.4.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: The resolver returns page-local spans and five outcomes; W57b requires only newer-edition observations with grounded global offsets. The additive plan and test paths are absent.

### P-01 — exact base and absent plan

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/norms/references/observation_plan.py tests/integration/norms/references/test_observation_plan.py`
- captured_output:
  ```text
  eca8597b4b59a06371cfaf709df7bee8509a604f
  eca8597b4b59a06371cfaf709df7bee8509a604f
  ```
- interpretation: The pure bridge can be added without touching runtime stage or shared contracts.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/references/observation_plan.py`
- `tests/integration/norms/references/test_observation_plan.py`
- `docs/program/tasks/W57B-INT-REFERENCE-OBSERVATION-PREP-01.md`
- `docs/program/W57B-INT-REFERENCE-OBSERVATION-PREP-01.md`

## Forbidden hotspots

Existing reference resolver, findings publication, stage registry, contracts,
migrations, composition root, root dependencies/locks, global styles, corpus,
`CURRENT_STATE.md`, tags and remote refs.

## Non-goals

No stage wiring, database write, severity, normative applicability judgment,
verified set admission, live provider call or beta acceptance.

## Deliverables

Typed pure candidates with source spans, focused tests and a task report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/references/test_observation_plan.py tests/integration/norms/references/test_reference_resolution.py` — pass;
- compilation, direct governance, `git diff --check`, exact changed-path proof — pass;
- no full `make gate` under R-135.

## Integration contract

The future W57b deterministic stage supplies the resolver's report and the
same numbered PDF text pages with page-global starts. It receives one candidate
per `NEWER` reference, up to ten exact PDF-text evidence spans, the pinned
matched document ID and the fixed rule ID. It owns stage provenance, report
publication and finding persistence. The candidate has no proposed severity.

## Failure/idempotency/security cases

Unknown pages, missing text, invalid offsets, altered raw quotes, duplicate
page numbers/labels or malformed newer outcomes fail closed. Repeated inputs
produce identical candidates. No source corpus text enters Git.

## Rollback / feature flag

Revert the additive files before runtime wiring; no data rollback or flag.
