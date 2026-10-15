# Task W56A-INT-GENERATOR-01 — publish the synthetic corpus on dev

## Outcome

`origin/dev` contains the exact deterministic W56a synthetic corpus after
SEAL, and `CURRENT_STATE.md` distinguishes fixtures from measured quality.

## Depends on

- `W56A-INT-SEAL-01` — complete on `origin/dev` at `da355eda`;
- `W56A-GENERATOR-PREP-01` — complete at `b27b2c1c`.

## Frozen inputs and contracts

- exact `origin/dev` predecessor `da355edabcc1282ea3a05a713372bbb25560ccf7`;
- generator SHA `b27b2c1cb912812f2d7fab54c1cf2aa2bf1ddd21`;
- API/category contract SHA-256
  `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- corpus manifest SHA-256
  `95e07c2919d46a600cb9ffead41c883fd38d141699c6857a4700126d6dae6fb7`;
- migration head `0022_findings_v2`; `P02_LOCK.json` remains read-only at
  `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.

## Enumerator ownership

- enumerated_set_changed: no in this integration commit;
- enumerator_path: `fixtures/evaluation/ar_v2/expected_issues.json`;
- enumerator_owner: `W56A-GENERATOR-PREP-01`;
- totality_query: `.venv/bin/python tools/fixtures/seeded/generate.py --check`.

## Allowed paths and publication authority

- `docs/program/CURRENT_STATE.md`, this task file, and
  `docs/program/W56A-INT-GENERATOR-01.md`;
- fast-forward `origin/dev` from the frozen predecessor to the checked
  integration commit. No `origin/main` or tag authority.

## Forbidden hotspots

`contracts/**`, migrations, source/runtime code, existing fixtures,
`P02_LOCK.json`, `VERSION`, root dependency/lock files, global styles,
recordings, stand state and `origin/main`.

## Non-goals

No model call, recorded baseline, live/manual acceptance, full local gate,
feature activation or beta verdict.

## Deliverables and checks

- merge the generator commit by fast-forward and record the fixture count;
- run its exact `--check` and focused 41-test contract suite once on the
  integration tree, verify manifest/category pin and `git diff --check`;
- prove the integration-only diff touches exactly three allowed docs;
- confirm a clean tree and the actual remote `dev` predecessor immediately
  before a fast-forward push, then re-read the remote ref.

## Integration contract, rollback and handoff

The later HARNESS task consumes these corpus bytes and owns recordings,
matcher and measured baseline. The model pin remains blocked until two gateway
proofs. If the remote ref moves, stop and remeasure from its new SHA. Before
dependent work the generator can be reverted; afterward use a forward fix.
Report files, checks, contracts, limitations, ref and forbidden-hotspot proof.
