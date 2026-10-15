# Task W57A-INT-TARGET-RESOLUTION-PREP-01 — pure norm target spans

task_id: W57A-INT-TARGET-RESOLUTION-PREP-01

## Outcome

A pure resolver turns an owner-specified clause, table caption or explicit
paragraph range into reliable contiguous `npar_` spans. It lists excluded
unreliable paragraphs and refuses ambiguous or absent anchors. Focused tests
cover the W57a §A3.1 boundaries and markdown caption forms.

## Depends on

- `W57A-CORPUS-SOURCE-PREP-01` — completed local inventory with no promoted-map claim.
- `W57A-INT-RETRIEVAL-RANK-PREP-01` — complete at `e3ea05dc5fab8bc53304e80cf8741b470d8d52cf`;
  consumes reviewed contiguous target spans.

## Frozen inputs

- base commit and `origin/dev`: `e3ea05dc5fab8bc53304e80cf8741b470d8d52cf`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §A3.1.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.
- migration head `0022_findings_v2`; no head movement.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W57 specifies clause/table/range anchors but there is no pure resolver on this base.

### P-01 — exact base and absent resolver

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/norms/retrieval/targets.py tests/integration/norms/retrieval/test_targets.py`
- captured_output:
  ```text
  e3ea05dc5fab8bc53304e80cf8741b470d8d52cf
  e3ea05dc5fab8bc53304e80cf8741b470d8d52cf
  ```
- interpretation: additive resolution code can precede the promotion database and owner review.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/targets.py`
- `tests/integration/norms/retrieval/test_targets.py`
- `docs/program/tasks/W57A-INT-TARGET-RESOLUTION-PREP-01.md`
- `docs/program/W57A-INT-TARGET-RESOLUTION-PREP-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing segmentation/ranking
modules, active profile, runtime executor, `norms/public.py`, root
dependencies, composition root, global styles, corpus source, stand, tags
and `origin/main`.

## Non-goals

No edition selection, legal-status claim, clause applicability judgment,
promotion database read, owner map review, verified set, active v3, model
call, full gate or beta acceptance.

## Deliverables

Pure target resolver, focused tests, report and exact development ref read-back.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_targets.py` — pass;
- Python compilation, direct task governance, `git diff --check`, exact
  allowed-path proof — pass;
- no `make gate` under R-135.

## Integration contract

The W57A-MAP owner reads a qualified promoted snapshot and binds the exact
document edition first. It passes ordered canonical paragraphs to this
resolver, reviews its selected text and excluded unreliable list, then records
the resulting document-bound `npar_` ranges in the map. Ranking must consume
only those reviewed spans; it may not resolve editions on its own.

## Failure/idempotency/security cases

Missing/duplicate ordinals or paragraph identities, ambiguous captions or
clauses, missing explicit endpoints and an empty reliable result fail closed.
Repeated inputs return identical spans without I/O. No source norm text,
credentials or model output enters Git.

## Rollback / feature flag

Revert the additive module before runtime wiring; no data rollback or flag.
