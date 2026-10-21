# Task W56A-INT-SEAL-01 — integrate the recorded-only seal in development

## Outcome

`origin/dev` contains the exact `W56A-SEAL-01` commit and a truthful current
state entry. It remains a development candidate, with no v2 activation.

## Depends on

- `W56A-DEV-FREEZE-01` — complete at `56978669`;
- `W56A-SEAL-01` — complete at `bcd5ad26`.

## Frozen inputs and contracts

- `origin/dev` and integration base `56978669f6a618ac75f91dc803b27369e3b6cebe`;
- seal SHA `bcd5ad26dce64c2e90162f5ed097032e5b180d47`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- domain catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- stage registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head `0022_findings_v2`; `P02_LOCK.json` remains at
  `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable;
- enumerator_owner: `W56A-SEAL-01`;
- totality_query: `git diff --name-only bcd5ad26...HEAD`.

The source SEAL commit owns the enumerators; this integration changes none.

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/tasks/W56A-INT-SEAL-01.md at `e61fc457`
- addendum_path: docs/program/PROGRAM-GOVERNANCE-REPAIR-01.md

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths and publication authority

- `docs/program/CURRENT_STATE.md` (live facts and historical wording only);
- this task file and `docs/program/W56A-INT-SEAL-01.md`;
- fast-forward `origin/dev` from the exact frozen base to the checked integration
  commit. This task has **no** `origin/main` or tag authority.

## Forbidden hotspots

`contracts/**`, migrations, runtime code, generated client, root dependencies,
`P02_LOCK.json`, `VERSION`, global styles, historical reports, stand state and
`origin/main`.

## Non-goals

No gateway probe, paid call, v2 activation, live/manual acceptance or full
local gate. No claim that the development candidate is beta-ready.

## Deliverables and checks

- fast-forward the SEAL commit into this integration line;
- update `CURRENT_STATE.md` to 0022 / 47 paths / 54 operations / 124 schemas /
  25 API codes while preserving the W55b historical record;
- run the two formerly deferred prose guards, the narrow contract consistency
  checks, `git diff --check`, exact allowed-path proof and clean-tree check;
- re-read `origin/dev` immediately before push and prove it is the frozen base;
  push only the tested integration SHA by fast-forward.

## Integration contract, rollback and handoff

`W56A-GENERATOR-PREP-01` consumes the exact published development SHA and only
its synthetic paths. If the remote ref moves, stop and rebase/check a new exact
candidate. Before any dependent work, this integration commit can be reverted;
afterward use a forward correction. Record changed files, checks, contract
digests, risks, forbidden-hotspot proof and the pushed SHA in the report.
