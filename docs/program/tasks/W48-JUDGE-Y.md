# Task W48-JUDGE-Y — audit architecture and durable evidence on the merged subject

## Outcome

An architecture/data-integrity report traces Stage-B changes and the audit blockers from durable
state to every caller, attacks command separation and historical evidence, and repairs nothing.

## Depends on

- `W48-PORTS` — completed at `81b1f2a`
- `W48-WEB` — completed at `996b546`
- `W48-LIVE` — completed at `300567a`
- `W48-GOV` — completed at `1843db5`

## Frozen inputs

- subject: `14caf886e78883ed771d81fbf463c98af727c938`
- Stage-A audit: A-01 and A-02 remain release blockers; A-03 remains architecture debt
- API: 17 paths / 20 operations / 61 schemas; error catalog: 22
- migration head: `0013_norm_embeddings`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: merged subject and frozen bytes

### P-01 — exact subject

- captured_at: 2026-10-02
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  14caf886e78883ed771d81fbf463c98af727c938
  ```
- interpretation: the architecture review addresses the same four-lane merge as Judge X.

### P-02 — merged focused checks

- captured_at: 2026-10-02
- command: `.venv/bin/python -m pytest tests/contract/test_alpha_acceptance_command.py tests/e2e/test_pc01_journey_conformance.py tests/contract/program/test_wave_governance.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/api_v1/test_doc_prose_facts.py -q`
- captured_output:
  ```text
  159 passed
  ```
- interpretation: this is the focused merged baseline, not the final whole-tree gate.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/reviews/W48-JUDGE-Y.md`

## Forbidden hotspots

- every other tracked path
- contracts, migrations, dependencies/locks, runtime sources and test instruments
- refs, tags, remote branches, host deployment state and secret stores

## Non-goals

- no repair or contract/migration design
- no reinterpretation of A-01/A-02 as closed
- no ref, deployment, tag or public-data mutation

## Deliverables

- port/adapter/router trace and hydration proof
- shared-screen harness census with focused exceptions
- DB/blob dual-write, attempt provenance and idempotency audit
- proof that `make gate` remains secret/network-free and acceptance cannot skip phases
- debt/history/frozen-byte reconciliation
- findings, untested questions, final verdict and restored report-only diff

## Required tests

- trace all `run_exists` / `finding_exists` implementations and callers
- search routers/components for forbidden direct SQL/S3/filesystem and deep imports
- inspect provider invocation against durable attempt creation and blob put against metadata commit
- compare contracts/migrations/locks/composition to the Stage-B frozen base
- mutate each new governance/acceptance completeness rule independently and restore it

## Integration contract

Report only. Cross-examination decides which findings are upheld and what smallest later path
grant would be required; this task grants none.

## Failure/idempotency/security cases

- absence of a durable attempt or reconciliation path remains a release blocker
- no silent fallback or in-memory-only job/attempt state may be called durable
- a historical correction is valid only through the addendum with source bytes unchanged

## Rollback / feature flag

Not applicable: report only.

## Handoff

- changed files: the one report
- commands/results: quoted with exit status
- known limits: explicit
- integration note: cross-examine with `W48-JUDGE-X` before repair
