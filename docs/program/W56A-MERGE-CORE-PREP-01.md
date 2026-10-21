# W56A-MERGE-CORE-PREP-01 — pure grouping handoff

**Base:** published `origin/dev=0d7d27bb50ba35350b0287073e7e3f3f99978e5f`.
The module is deliberately unwired while `W56A-MODEL-PIN-01` remains blocked.

## Result and contract

`merge_grounded` accepts immutable ordinal/category/evidence records and emits
`findings.merged` version `1.0.0`: same-category connected components joined by
same-page half-open span overlap or equal NFC/case-folded/whitespace-collapsed
quote of at least 20 characters. Members and groups have deterministic order;
the canonical observation has the earliest page and start offset, then the
lowest ordinal. No evidence or input object is changed, and no finding UID is
allocated. The stage registry and API SHA-256 values remain
`bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`
and `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`.

## Changed files and checks

- New `src/auditmanager/analysis/stages/finding_merge.py`.
- New `tests/integration/findings/test_v2_merge_core.py`.
- New task and this report under `docs/program/`.
- Focused pytest: **17 passed**. It covers overlap/touching, quote threshold
  and normalisation, page/category boundaries, transitive and cross-evidence
  chains, canonical ties, permutation, empty input and malformed records.
- Python compilation and `git diff --check`: passed. No full local gate,
  provider call or database suite ran.

## Integrator handoff and limits

Merge only this bounded commit in a dedicated dev integration slot. Later
`W56A-MERGE-01` must adapt **already grounded** observations to these input
types, invoke the function after the gate, and own publication, canonical
finding identity, queries and run-plan status. The pure function does not
independently verify the text layer; the existing grounding gate retains that
responsibility. No new/changed contract, migration, provider lock, root lock,
composition root, global style, runtime executor or forbidden hotspot is in
this lane. `origin/main` and tags remain untouched.
