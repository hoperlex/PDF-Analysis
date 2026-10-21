# Task W57B-INT-REFERENCE-RESOLUTION-PREP-01 — pure normative reference resolution

task_id: W57B-INT-REFERENCE-RESOLUTION-PREP-01

## Outcome

Pure W57b functions mirror SQL designation tokens, extract cited designation
spans from readable text pages and assign the five §B3.3 outcomes against a
caller-supplied pinned catalogue. Tests cover major families, amendments,
edition precedence, unread pages and Unicode/homoglyph input.

## Depends on

- `W55A-SEARCH-01` — completed migration `0020` and generated designation tokens.

## Frozen inputs

- base commit and `origin/dev`: `960da9e1b7cfc5eda75fc3a1d52714bb66be8176`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §B3.2–B3.3.
- migration `db/migrations/versions/20261012_0020_norms_search.py` token function; current head `0022_findings_v2`.
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W57 §B3.2–B3.3 requires family parsing and five outcomes; no references module exists on the frozen base.

### P-01 — frozen base and absent references package

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/norms/references tests/integration/norms/references`
- captured_output:
  ```text
  960da9e1b7cfc5eda75fc3a1d52714bb66be8176
  960da9e1b7cfc5eda75fc3a1d52714bb66be8176
  ```
- interpretation: additive pure code can be prepared before the W57b seal and runtime stage.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/references/**`
- `tests/integration/norms/references/**`
- `docs/program/tasks/W57B-INT-REFERENCE-RESOLUTION-PREP-01.md`
- `docs/program/W57B-INT-REFERENCE-RESOLUTION-PREP-01.md`

## Forbidden hotspots

Existing search/retrieval modules, contracts, migrations, provider lock,
runtime, findings, public API, composition, root dependencies, global styles,
corpus, stand, `CURRENT_STATE.md`, tags and remote refs.

## Non-goals

No stage activation, source PDF/OCR, snapshot DB read, verified custody,
published observation, severity, API/contract seal or beta acceptance.

## Deliverables

New pure references package, family vocabulary, focused tests and task report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/references` — pass;
- compilation, direct governance, whitespace and exact allowed-path proof — pass;
- no full `make gate` under R-135.

## Integration contract

The W57b stage supplies text-bearing pages and the catalogue bound to the run's
pinned verified set. It must pass the run's exact snapshot id and reject a
mismatched catalogue. It can use returned newer-edition groups to create one
rule-made observation each, with up to ten occurrence spans and no proposed
severity; the other four outcomes belong only in the report. The stage owns
provider mode, rule_id, publication and partial failure handling.

## Failure/idempotency/security cases

Duplicate catalogue identities, token mismatch, unlisted unparsed slugs and
snapshot mismatch are refused. Amendments cannot enter base edition sorting.
Unread pages are reported, never treated as evidence of absence. Identical
inputs give identical results; no source norm text enters Git.

## Rollback / feature flag

Revert the additive package before runtime wiring; no data rollback or flag.
