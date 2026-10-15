# Task W56A-INT-MERGE-INPUT-PREP-01 — bridge grounded AR v2 proposals to deterministic merge

task_id: W56A-INT-MERGE-INPUT-PREP-01

## Outcome

A pure adapter numbers only fully PDF-grounded AR v2 proposals in the merge
artifact, retaining the original parser ordinal for diagnostics. A test proves
that a proposal with one failed quote contributes no member to any merge group.

## Depends on

- `W56A-INT-PROPOSAL-GROUNDING-PREP-01` — complete at `206461aa`;
- `W56A-INT-MERGE-CORE-01` — complete before this base.

## Frozen inputs

- base commit: `8c994dafb64a800c0a3974d34f4717c87d16e4b5` (`origin/dev`);
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`; `R-133`–`R-136` and W56 plan §A3.3.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the grounding result and merge rule exist, but there is no adapter
  assigning dense artifact ordinals after rejected proposals are filtered.

### P-01 — exact base and missing adapter

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/merge_input.py`
- captured_output:
  ```text
  8c994dafb64a800c0a3974d34f4717c87d16e4b5
  8c994dafb64a800c0a3974d34f4717c87d16e4b5
  ```
- interpretation: an additive module can connect the two completed pure components.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/merge_input.py`
- `tests/integration/analysis/test_ar_v2_merge_input.py`
- `docs/program/tasks/W56A-INT-MERGE-INPUT-PREP-01.md`
- `docs/program/W56A-INT-MERGE-INPUT-PREP-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing parser/grounding/merge
modules, runtime executor, database publication, root dependencies/locks,
composition root, global styles, recordings, `VERSION`, production stand,
tags and `origin/main`.

## Non-goals

No provider call, active AR v2 stage, finding identity, expert decision,
new merge rule, whole-tree gate, corpus import or beta acceptance.

## Deliverables

Pure adapter, focused tests, task report and development ref read-back.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/test_ar_v2_merge_input.py tests/integration/analysis/test_ar_v2_proposal_grounding.py tests/integration/findings/test_v2_merge_core.py` — pass;
- Python compilation, direct task governance, `git diff --check` and exact
  allowed-path proof — pass;
- no `make gate` under R-135.

## Integration contract

A later AR v2 stage can call `prepare_merge` only after `ground_proposals`.
`source_proposal_ordinals[n]` maps dense merge observation ordinal `n` to the
parser-accepted proposal ordinal, while `artifact.groups` refers solely to
dense ordinals. Publication must persist diagnostics separately and must not
create findings from rejected proposals. Runtime wiring needs its own grant.

## Failure/idempotency/security cases

Duplicate/missing proposal ordinals, out-of-order accepted proposals and
incomplete accepted evidence fail closed. Repeated inputs return the same
artifact without I/O. Recognised-only text stays excluded by the preceding
grounding gate; no LLM output becomes an expert decision.

## Rollback / feature flag

Revert the additive module before runtime wiring; no data rollback or flag.

## Handoff

- changed files/checks/limits: report;
- contracts: none;
- next: AR v2 stage wiring after its recorded-only grant and MODEL-PIN for live calls.
