# Contract task W0-DOM-01 — domain IDs, states and errors draft.1

## Outcome

Publish a reviewable `1.0.0-draft.1` domain-contract candidate in which every
identifier prefix is unique, every state transition is closed and every externally
visible failure has a stable typed code. The candidate must support four documented
evidence walks and must not encode legacy paths, deletion or overwrite semantics.

## Problem

Independent consumers need one precise meaning for opaque identities, durable state
transitions and typed errors before implementation. The bootstrap `draft.0` is
incomplete and must reflect accepted behavioral gaps without copying legacy storage
or deletion semantics.

## Owners / consumers

- provider/contract owner: planned agent `/root/w0_domain_contract`
- frozen-boundary governor: primary agent `/root`
- consumers: analysis, jobs, findings, API and independent QA tasks after freeze
- product/domain approval authority: repository owner/user

## Depends on

- Completed `W0-BHV-01`, accepted at
  `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`.

## Frozen inputs

- base commit: `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`
- current domain contract: `1.0.0-draft.0`
- accepted capability inventory and greenfield Bible/ADR-0007/0010/0012 semantics
- `W0-ARC-01` decisions are parallel candidates, not frozen inputs; mismatch blocks
  integration and returns to the integrator
- API/analysis/comparison/event drafts: read-only
- migration head: none

## Allowed paths

- `contracts/domain/v1/**`

No other contract family or path is writable.

## Forbidden hotspots

- `contracts/analysis/**`, API/events/comparison contracts
- architecture/program docs, fixtures/tests, source/runtime code
- root dependencies/locks, migrations, composition root, global styles and legacy

## Non-goals

- No production implementation, database migration or persistence design.
- No changes to another contract family or to the bootstrap validator.
- No tenant, IdP, retention, TTL or legal-hold values invented without owner input.
- No analysis-stage, result-package, comparison or event-envelope semantics.
- No path/filename identity and no legacy overwrite/delete behavior copied as target
  behavior.
- No contract freeze by the task author; freeze remains the integrator's slot.

## Proposed semantics

- Opaque IDs never encode path/display/business attributes.
- `Finding` differs from `FindingObservation`; `AuditRun`, `Job`, `Attempt` differ.
- Expert correction/revocation allocates a new `decision_id`; history is not deleted.
- Retry/current-attempt authority is explicit; stale/superseded attempt cannot
  publish.
- Imports, blobs, runs, jobs and attempts have closed state machines with explicit
  retry, partial, terminal and conflict semantics.
- Commands are idempotent by key; key reuse with a different payload is conflict.
- Errors cover validation, state conflict, stale authority, required norm/dependency
  unavailable, artifact integrity and explicit partial/terminal failure.
- No tenant/retention or stage/result semantics are guessed in this contract.

## Deliverables

- Updated `identifiers.json`, `state-machines.json`, `error-codes.json` and README,
  all declaring candidate version `1.0.0-draft.1`.
- Prefixes remain unique and all transitions reference declared states.
- Error envelope retains stable safe `error_code`, message and correlation identity.
- README evidence for all four success/retry/conflict/terminal walks below, including
  the source inventory rows and any unresolved owner decision.

## Examples / evidence walks

- provider timeout → retry → new/current Attempt → late stale result rejected
- finding rerun → new Observation → expert correction as a new decision event
- idempotent repeat vs same-key/different-payload conflict
- missing authoritative norm/dependency → explicit failure/partial policy

## Compatibility

- backward compatible: no; meaning/required semantics may tighten
- version bump: `1.0.0-draft.0` → `1.0.0-draft.1`
- safe because no frozen production consumer exists; after freeze, change requires
  formal freeze-break/version procedure

## Required tests

- Command: `python3 -m json.tool contracts/domain/v1/identifiers.json >/dev/null`.
  Expected: exit `0`.
- Command: `python3 -m json.tool contracts/domain/v1/state-machines.json >/dev/null`.
  Expected: exit `0`.
- Command: `python3 -m json.tool contracts/domain/v1/error-codes.json >/dev/null`.
  Expected: exit `0`.
- Command: `PYTHONPATH=/tmp/pdf-analysis-validator-deps python3 scripts/validate_bootstrap.py`.
  Expected: exit `0`, a standalone `PASS`, unique prefixes, declared transition
  targets and valid terminal states.
- Command: `git diff --check -- contracts/domain/v1`.
  Expected: exit `0` and no output.
- Independent consumer review covers all four evidence walks above and every
  terminal/retry path. Expected: no path/display identity, destructive decision
  history, undeclared transition or silent fallback.

## Integration contract

After acceptance/freeze, consumers use these exact ID/state/error meanings. A
fencing/execution token is an authority capability, not an entity ID or path. No
production schema/implementation is authorized by this task.

## Failure / idempotency / security

- Unknown transitions and stale authority fail closed.
- Error details remain safe and never expose secret/path/payload content.
- Same command key and semantic payload returns the same aggregate/outcome; changed
  payload conflicts and creates no duplicate decision/version/run.
- Architecture mismatch or unapproved `PD-01`/`PD-03` blocks integration.

## Rollback / feature flag

Contract-only draft; no feature flag. Before freeze, revert the task commit. After
freeze, stop consumers and follow freeze-break/versioning procedure.

## Handoff

- changed files and final candidate version/commit recorded by the integrator after
  acceptance
- commands/results, provider/consumer review evidence and all four evidence walks
- new/changed contracts: domain `1.0.0-draft.1` candidate only
- compatibility, known limits and unresolved owner decisions
- integration notes for analysis/jobs/findings/API consumers
- proof that no migration/runtime/legacy or other forbidden hotspot changed
