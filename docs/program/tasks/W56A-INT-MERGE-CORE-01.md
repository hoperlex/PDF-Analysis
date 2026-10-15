# Task W56A-INT-MERGE-CORE-01 — publish the independent merge core on dev

## Outcome

`origin/dev` contains the exact pure merge-core commit after SEAL and the
synthetic generator, without enabling the blocked W56a provider or v2 runtime.

## Depends on

- `W56A-INT-GENERATOR-01` — complete at `0d7d27bb`;
- `W56A-MERGE-CORE-PREP-01` — complete at `17aced7b`.

## Frozen inputs and contracts

- remote predecessor `0d7d27bb50ba35350b0287073e7e3f3f99978e5f`;
- merge-core SHA `17aced7b746bb0aadba8233313c5e002c33c39f2`;
- stage registry SHA-256
  `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head `0022_findings_v2`, model lock read-only.

## Enumerator ownership

- enumerated_set_changed: no;
- enumerator_path: `contracts/analysis/v1/stage-registry.json` (read-only);
- enumerator_owner: `W56A-SEAL-01`;
- totality_query: `tests/integration/findings/test_v2_merge_core.py`.

## Allowed paths and publication authority

- `docs/program/CURRENT_STATE.md`, this task and
  `docs/program/W56A-INT-MERGE-CORE-01.md`;
- fast-forward `origin/dev` from the frozen predecessor to the checked
  integration SHA. No `origin/main` or tag authority.

## Forbidden hotspots

`contracts/**`, migrations, runtime/executor wiring, provider selection,
root dependencies/locks, composition root, global styles, `P02_LOCK.json`,
`VERSION`, recordings, stand state and `origin/main`.

## Non-goals

No gateway probe, v2 activation, finding publication, manual acceptance,
full local gate or beta verdict.

## Deliverables and checks

- fast-forward the exact core commit; update current-state text to state it
  is unwired;
- rerun the 17 focused rule tests and compilation on the integration tree;
- `git diff --check`, three-file integration-only proof and clean tree;
- read remote `dev` immediately before and after normal fast-forward push.

## Integration contract and rollback

The later `W56A-MERGE-01` consumes this core after the grounding gate and owns
database/publication/runtime wiring. If the remote ref moves, stop and
recheck; before use this new module can be reverted, afterward correct
forward. Handoff records files, tests, contract pins, risks and the published
ref. Provider and beta remain blocked by the unproven two-gateway model pin.
