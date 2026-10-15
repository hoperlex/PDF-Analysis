# Task W57A-INT-RETRIEVAL-RANGE-BOUND-FIX-01 — bound target expansion

task_id: W57A-INT-RETRIEVAL-RANGE-BOUND-FIX-01

## Outcome

The pure W57a selector refuses a target or window ordinal span larger than the
available paragraph count before expanding it. A focused test proves that
malformed huge input fails with `RankingRefused` without allocating its range.

## Depends on

- `W57A-INT-RETRIEVAL-RANK-PREP-01` — complete at `e3ea05dc5fab8bc53304e80cf8741b470d8d52cf`.
- `W57A-INT-TARGET-RESOLUTION-PREP-01` — complete at `0bcef49dc4e0dd0899a2d6bfc099c3f9d0e7cf9f`.

## Frozen inputs

- base commit and `origin/dev`: `bc61b67a79b2665bceb84822cb89475c84932532`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §A3.2.
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

- premise: target/window ranges are expanded before checking their endpoints against the supplied paragraph set.

### P-01 — exact base and expansion sites

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && rg -n 'range\(' src/auditmanager/norms/retrieval/ranking.py`
- captured_output:
  ```text
  bc61b67a79b2665bceb84822cb89475c84932532
  bc61b67a79b2665bceb84822cb89475c84932532
  115:            for ordinal in range(span.ordinal_first, span.ordinal_last + 1)
  120:            for ordinal in range(window.paragraph_ordinal_first, window.paragraph_ordinal_last + 1)
  138:        for ordinal in range(target.ordinal_first, target.ordinal_last + 1)
  142:        for ordinal in range(window.paragraph_ordinal_first, window.paragraph_ordinal_last + 1)
  ```
- interpretation: fail closed on counts before the materialization step.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/ranking.py`
- `tests/integration/norms/retrieval/test_ranking.py`
- `docs/program/tasks/W57A-INT-RETRIEVAL-RANGE-BOUND-FIX-01.md`
- `docs/program/W57A-INT-RETRIEVAL-RANGE-BOUND-FIX-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, other retrieval files, runtime,
root dependencies, composition root, global styles, corpus, stand, tags and
`origin/main`.

## Non-goals

No ranking rule change for valid inputs, corpus import, custody, active v3,
full gate or beta acceptance.

## Deliverables

Early range-count refusal, focused regression test, report and development
ref read-back.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_ranking.py tests/integration/norms/retrieval/test_targets.py` — pass;
- Python compilation, direct task governance, staged whitespace and exact
  allowed-path checks — pass;
- no `make gate` under R-135.

## Integration contract

The future builder still supplies complete canonical paragraphs. This guard
rejects an impossible span before allocating its ordinals; all previously
valid ranked output remains byte-identical. No persistence path changes.

## Failure/idempotency/security cases

A span longer than available rows refuses in bounded time. Repeated valid
inputs preserve deterministic output; no I/O or new source text is introduced.

## Rollback / feature flag

Revert this guard with its pure selector before runtime wiring; no data
rollback or feature flag.
