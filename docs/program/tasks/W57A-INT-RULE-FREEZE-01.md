# Task W57A-INT-RULE-FREEZE-01 — prepare the W57a citation/custody seal

task_id: W57A-INT-RULE-FREEZE-01

## Outcome

The integrator has an exact-`dev` decision and freeze record for the future
sole-owner `0023_norm_citations` seal. It names the citation completeness rule,
shared hotspots, checks and open evidence without granting a code lane or
claiming that a qualified retrieval set exists.

## Depends on

- `CFB-INT-DEV-PUBLISH-17` — completed; exact published base `b9f1c149f004851de89a2fcc615618068e794bde`.
- `W57-INT-SEAL-FREEZE-PROPOSAL-01` — completed sequencing proposal.
- `W57A-INT-CITATION-PREP-01` — completed pure quote/value grounding.

`W56A-INT-CLOSE`, W54 qualified corpus/DB-S3 publication, reviewed W57a map,
verified retrieval set and W57a runtime are pending. They are gates for their
respective later tasks, not completed `depends_on` for this docs-only task.

## Frozen inputs

- base commit and read-back `origin/dev`: `b9f1c149f004851de89a2fcc615618068e794bde`;
- API: 47 paths / 54 operations / 124 schemas; `contracts/api/v1/openapi.json`
  SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalogue: 25 codes; `contracts/domain/v1/error-codes.json`
  SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- domain identifiers SHA-256 `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- analysis stage registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- `P02_LOCK.json` SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`;
- code-first plan SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- migration head `0022_findings_v2`; proposed next slot `0023_norm_citations`, conditional on no intervening head;
- `R-135`: focused code/contract tests and isolated forward migration checks
  during development; one full beta gate after all planned code.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The later `W57A-SEAL-01` is proposed as the *only* writer of the migration,
contract, generated API and enumerated sets. Its own task must declare each
enumerator owner and totality query before dispatch.

## Captured premise evidence

- premise: this exact `dev` has the W56a persistence base but no W57a citation
  relation, `0023` migration or sealed norm-verification operation.

### P-01 — exact published development base

- captured_at: 2026-10-16
- command: `git rev-parse HEAD origin/dev`
- captured_output:
  ```text
  b9f1c149f004851de89a2fcc615618068e794bde
  b9f1c149f004851de89a2fcc615618068e794bde
  ```
- interpretation: local branch point and tracked dev ref match; this is not
  deployed-state evidence and the ref must be re-read before code dispatch.

### P-02 — migration and operation absence

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only HEAD db/migrations/versions | rg '002[234]_'`
- captured_output:
  ```text
  db/migrations/versions/20261015_0022_findings_v2.py
  ```
- interpretation: `0023` and `0024` do not exist in this tree; 0023 can be
  allocated only after a fresh head check.

### P-03 — contract size and error vocabulary

- captured_at: 2026-10-16
- command: `python3 -c "import json; p=json.load(open('contracts/api/v1/openapi.json')); e=json.load(open('contracts/domain/v1/error-codes.json')); print(len(p['paths']),sum(v.lower() in {'get','post','put','patch','delete','options','head','trace'} for item in p['paths'].values() for v in item),len(p['components']['schemas']),len(e['codes']))"`
- captured_output:
  ```text
  47 54 124 25
  ```
- interpretation: the four numbers are checkout pins, not permission to
  update the API or error vocabulary in this task.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W57A-INT-RULE-FREEZE-01.md`
- `docs/program/W57A-INT-RULE-FREEZE-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, runtime/API/UI/test source, composition
root, root dependency/lock files, provider lock, global styles,
`OWNER_RULINGS_2026-09-17.md`, `CURRENT_STATE.md`, normative corpus, live
DB/S3, Git refs and tags.

## Non-goals

No new owner ruling number, executable `W57A-SEAL-01` grant, map approval,
credentialed repair, verified set, active CITE stage, XLSX route, stand act,
full gate, release or beta verdict.

## Deliverables

This task and a report with an exact-base RULE/FREEZE decision ledger, fresh
`pin_sweep` digest and owner/disposition matrix, concrete citation completeness
semantics and focused acceptance requirements for the subsequent seal.

## Required tests

- `python3 tools/plan/pin_sweep.py reseal-surface migration table error-code route`:
  complete inventory captured in the report; re-run from the later code base;
- direct `governance_findings` on this task and the program governance suite:
  empty/pass;
- frozen SHA-256 and migration-head read-back: match;
- `git diff --check` and exact two-path proof: pass;
- no services or full `make gate` for this docs-only task under R-135.

## Integration contract

The report is an input to new `W57A-RULE-01`/`W57A-FREEZE-01` and the sole
`W57A-SEAL-01` task. The later integrator re-reads `origin/dev`, resolves
pending W56a code close and W54 corpus facts, assigns one shared-hotspot owner,
copies the exact necessary grants into that owner's task, runs `pin_sweep
--check`, then dispatches it. This task itself publishes nothing.

## Failure/idempotency/security cases

An absent citation row or an empty caller-supplied mapping is never proof of
verified zero citations. Failed grounding withholds the complete observation.
Cross-run, cross-snapshot, cross-set and cross-paragraph bindings refuse.
Repeated documentary checks are read-only and deterministic.

## Rollback / feature flag

Revert these two docs. No runtime, schema, data or feature flag changes.

## Handoff

- changed files: this task and `docs/program/W57A-INT-RULE-FREEZE-01.md`;
- commands/results and limits: recorded in the report;
- contracts: none changed;
- integration: keep the sole-owner code task conditional on its fresh base and
  completed prerequisites.
