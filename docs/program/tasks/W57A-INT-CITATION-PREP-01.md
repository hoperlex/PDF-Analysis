# Task W57A-INT-CITATION-PREP-01 — pure normative citation and value grounding

task_id: W57A-INT-CITATION-PREP-01

## Outcome

A pure, deterministic W57a helper grounds model norm quotes to NFC reliable
paragraphs, preserves raw offsets, performs the declared value comparison and
withholds an entire observation on the first failure. Focused tests cover the
specified boundary cases without a promoted corpus or model call.

## Depends on

- `W57A-CORPUS-SOURCE-PREP-01` — completed source inventory; its limits ensure
  this pure helper makes no claim about a promoted snapshot or legal status.

## Frozen inputs

- base commit and `origin/dev`: `d89e15967a1550e5ce5f435dfc8c8f2d87dbb766`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §A3.4.
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

- premise: W57 §A3.4 declares quote and value matching; this checkout has no pure implementation at the planned additive path.

### P-01 — exact base and absent module

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/norms/citation_prep.py tests/integration/norms/test_citation_prep.py`
- captured_output:
  ```text
  d89e15967a1550e5ce5f435dfc8c8f2d87dbb766
  d89e15967a1550e5ce5f435dfc8c8f2d87dbb766
  ```
- interpretation: an additive pure helper does not contend with the future CITE runtime hotspot.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/citation_prep.py`
- `tests/integration/norms/test_citation_prep.py`
- `docs/program/tasks/W57A-INT-CITATION-PREP-01.md`
- `docs/program/W57A-INT-CITATION-PREP-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, `findings/grounding.py`, runtime
executor, public API, persistence, root dependencies/locks, composition root,
global styles, corpus source, stand, tags and `origin/main`.

## Non-goals

No active AR v3 stage, profile, schema, API, DB write, normative truth claim,
legal-status judgment, corpus import, paid call, full local gate or beta acceptance.

## Deliverables

Pure quote normalisation/raw mapping, numeric tokenisation, citation/value
grounding, focused tests, report, and exact development ref read-back.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/test_citation_prep.py` — pass;
- Python compilation, direct task governance, `git diff --check` and exact
  allowed-path proof — pass;
- no `make gate` under R-135.

## Integration contract

The later W57A-CITE owner supplies the pinned set's labelled paragraphs and
all reliable paragraphs of their documents, plus already grounded document
evidence quotes. It calls the pure helper before merge or publication and
persists only successful raw spans. The returned first failure withholds the
whole observation. Runtime wiring and a gate-time measurement need their own
task. The helper does not replace W56a document-evidence grounding.

## Failure/idempotency/security cases

Unknown labels, short or absent quotes, multiple rebound locations, non-NFC
paragraphs, overlong raw spans and unmatched values fail closed. Duplicate
identities are refused. Repeated inputs return the same result without I/O.
No source norm text, credential or model output is committed.

## Rollback / feature flag

Revert the additive module before runtime wiring; no data rollback or flag.
