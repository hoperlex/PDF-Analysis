# Task W57A-INT-RETRIEVAL-RANK-PREP-01 — deterministic prompt-part selection

task_id: W57A-INT-RETRIEVAL-RANK-PREP-01

## Outcome

A pure W57a selector ranks mapped-document windows by float32 exact inner
product with a stable tie-break, resolves only reliable paragraphs, and
reduces a deterministic prompt part within its exact 22,000-character cap.
Focused tests prove replay, refusals and the declared reduction order.

## Depends on

- `W57A-CORPUS-SOURCE-PREP-01` — completed source inventory; it explicitly
  distinguishes local source files from reviewed `ns_`/`npar_` identities.
- `W57A-INT-CITATION-PREP-01` — complete at `1bf6014a9477b7c42958fbf2162024bbfe89d5ab`;
  establishes the norm quote/value version strings stored by the future set.

## Frozen inputs

- base commit and `origin/dev`: `1bf6014a9477b7c42958fbf2162024bbfe89d5ab`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §A3.2.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.
- migration head `0022_findings_v2`; no head movement.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W57 §A3.2 specifies exact ranking and reduction but the retrieval module is absent on the frozen base.

### P-01 — base and absent retrieval path

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/norms/retrieval`
- captured_output:
  ```text
  1bf6014a9477b7c42958fbf2162024bbfe89d5ab
  1bf6014a9477b7c42958fbf2162024bbfe89d5ab
  ```
- interpretation: additive pure code can be prepared without the DB/custody builder slot.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/__init__.py`
- `src/auditmanager/norms/retrieval/ranking.py`
- `tests/integration/norms/retrieval/test_ranking.py`
- `docs/program/tasks/W57A-INT-RETRIEVAL-RANK-PREP-01.md`
- `docs/program/W57A-INT-RETRIEVAL-RANK-PREP-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing norms embedding/storage
modules, active profile, runtime executor, `norms/public.py`, root dependencies,
composition root, global styles, corpus source, stand, tags and `origin/main`.

## Non-goals

No real map resolution, promoted corpus read, verified set row or custody
admission, catalogue, active AR v3, provider call, full gate or beta acceptance.

## Deliverables

Pure ranking and prompt selection module, focused tests, report and exact
development ref read-back.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_ranking.py` — pass;
- Python compilation, direct task governance, `git diff --check`, exact
  allowed-path proof — pass;
- no `make gate` under R-135.

## Integration contract

The future W57A-RETRIEVAL builder supplies reviewed target spans, qualified
snapshot paragraphs and complete float32 vectors. It consumes the exact
rendered prompt part and selected rows, binds them to the reviewed map and
qualified `ns_`, and performs custody publication. It must verify this
selector's version and never substitute an unreviewed document or vector.

## Failure/idempotency/security cases

Malformed or non-finite vectors, duplicate identities, >50,000 windows,
missing/unreliable paragraphs, non-NFC text and an unreducible cap are refused.
Repeated identical inputs give byte-identical output. No source norm text,
credentials or model output enters Git.

## Rollback / feature flag

Revert the additive module before runtime wiring; no data rollback or flag.
