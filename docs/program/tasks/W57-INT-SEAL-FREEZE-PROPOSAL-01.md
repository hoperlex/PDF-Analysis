# Task W57-INT-SEAL-FREEZE-PROPOSAL-01 — prepare the W57a/W57b seal boundary

task_id: W57-INT-SEAL-FREEZE-PROPOSAL-01

## Outcome

A read-only exact-dev proposal names the ordered contract and migration owners
that can eventually persist W57a citations and expose a guarded W57b XLSX
operation. It identifies prerequisites and a missing W57b route grant without
authorizing either seal or changing product behavior.

## Depends on

- `W56A-INT-SEAL-01` — completed recorded-only 0022/API seal integration.
- `W57A-INT-CITATION-PREP-01` — completed pure quote/value grounding.
- `W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01` — completed unactivated run/source preflight.

The W56a code close, W57a map owner review, W57a/b rule/freeze/seal and W54
qualified corpus are open prerequisites for later work, not `depends_on` here.

## Frozen inputs

- base commit and published `origin/dev`: `08055ca094a9c3e4676a5907a0b3020f0bee4fb8`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  domain identifiers SHA-256 `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.
- migration head `0022_findings_v2`; no head movement in this task.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W57 citation storage and the XLSX operation are absent, while the
  existing W57b package trusts caller-supplied citation and authorization inputs.

### P-01 — published base

- captured_at: 2026-10-16
- command: `git rev-parse origin/dev`
- captured_output:
  ```text
  08055ca094a9c3e4676a5907a0b3020f0bee4fb8
  ```
- interpretation: this proposal has one exact dev base; a later dispatch must
  remeasure it rather than reuse the proposal's SHA blindly.

### P-02 — current migration head

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only HEAD db/migrations/versions | rg '002[234]_'`
- captured_output:
  ```text
  db/migrations/versions/20261015_0022_findings_v2.py
  ```
- interpretation: no 0023/0024 migration exists on the base.

### P-03 — guarded XLSX operation absent

- captured_at: 2026-10-16
- command: `rg -n '"exportRunXlsx"|"exportRunCsv"' contracts/api/v1/openapi.json src/auditmanager/api/security.py`
- captured_output:
  ```text
  src/auditmanager/api/security.py:356:        "exportRunCsv": _EXPERT,
  contracts/api/v1/openapi.json:1297:        "operationId": "exportRunCsv",
  ```
- interpretation: an XLSX route/role cannot be treated as already sealed.

### P-04 — W57 seal tasks have not been dispatched

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only HEAD docs/program/tasks/W57A-RULE-01.md docs/program/tasks/W57A-FREEZE-01.md docs/program/tasks/W57A-SEAL-01.md docs/program/tasks/W57B-RULE-01.md docs/program/tasks/W57B-FREEZE-01.md docs/program/tasks/W57B-SEAL-01.md`
- captured_output: empty (exit 0).
- interpretation: this document is a proposal, not a replacement for the rule,
  freeze or sole-owner task files required before contract/migration edits.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W57-INT-SEAL-FREEZE-PROPOSAL-01.md`
- `docs/program/W57-INT-SEAL-FREEZE-PROPOSAL-01.md`

## Forbidden hotspots

All product code and tests, `contracts/**`, `db/migrations/**`,
`src/auditmanager/bootstrap/**`, provider lock, root dependencies/locks,
global styles, `CURRENT_STATE.md`, W56/W59 files, corpus, stand, tags and
remote refs.

## Non-goals

No actual W57 rule/freeze/grant, migration slot reservation, normative
publication, role/API operation, persisted citation, runtime activation,
spreadsheet acceptance, full gate, release or beta verdict.

## Deliverables

One exact-base proposal, this formal task and an explicit unresolved-dependency
and sole-owner matrix.

## Required tests

- direct `governance_findings` on this task — empty;
- recompute the frozen hashes and verify HEAD is the stated dev base — match;
- `git diff --check` and exact allowed-path comparison — pass;
- no code tests or `make gate`: this task changes documentation only.

## Integration contract

The integrator may use the proposal to author later, separately frozen
`W57A-RULE/FREEZE/SEAL` and `W57B-RULE/FREEZE/SEAL` tasks. Every actual grant
must name the then-current dev SHA, complete predecessors, one owner for its
new migration head and shared contract, a fresh `pin_sweep.py` inventory, and
the R-135 focused-check cadence. The proposal cannot grant those hotspots.

## Failure/idempotency/security cases

If W56a code close or another migration has not landed, the old plan's W57
dependency/slot cannot be asserted. Do not synthesize a verified empty XLSX
citation mapping from migration 0022, infer a role from package input, or
expose a route whose served OpenAPI and role register disagree.

## Rollback / feature flag

Revert the two documentation files. No runtime behavior, data or feature flag
changes.

## Handoff

- changed files/checks/limits: see the proposal report;
- contracts: none;
- next: integration owner re-freezes from the live dev ref and dispatches
  the two serial sole-owner seals only when their prerequisites are met.
