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
- Completed `W0-DEP-01`, accepted at
  `ab1cfdab0ec5c413b188a44ff82a99586ecd7994`.
- Completed `W0-QA-02`, accepted at
  `6c82004b35f49463c8e7fc8602fbced2f374167e`.

## Frozen inputs

- base commit: `6c82004b35f49463c8e7fc8602fbced2f374167e`
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
- Draft 2020-12 `identifiers.schema.json`, `state-machines.schema.json` and
  `error-codes.schema.json` validate those three catalogs; each schema rejects
  unknown properties and requires the contract/version plus its complete payload.
- Draft 2020-12 `error-envelope.schema.json` validates the externally visible error
  envelope. Its `error_code` enum is exactly equal to the keys of
  `error-codes.json`; `message` and `correlation_id` are required safe strings,
  `retryable` is boolean, and undeclared fields fail closed.
- `examples/error-envelope.example.json` validates, while
  `examples/error-envelope.unknown-code.invalid.json` is rejected specifically
  because its code is absent from the catalog.
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
- Command: `.venv/bootstrap/bin/python -c "import glob,json; from pathlib import Path; from jsonschema import Draft202012Validator as V; root=Path('contracts/domain/v1'); [V.check_schema(json.loads(Path(p).read_text())) for p in glob.glob(str(root/'*.schema.json'))]; pairs=[('identifiers.schema.json','identifiers.json'),('state-machines.schema.json','state-machines.json'),('error-codes.schema.json','error-codes.json'),('error-envelope.schema.json','examples/error-envelope.example.json')]; [V(json.loads((root/s).read_text())).validate(json.loads((root/i).read_text())) for s,i in pairs]"`.
  Expected: exit `0`; every domain schema passes the Draft 2020-12 metaschema and
  every catalog/valid example validates against its owned schema.
- Command: `.venv/bootstrap/bin/python -c "import json; from pathlib import Path; from jsonschema import Draft202012Validator as V; root=Path('contracts/domain/v1'); catalog=json.loads((root/'error-codes.json').read_text()); schema=json.loads((root/'error-envelope.schema.json').read_text()); assert set(schema['properties']['error_code']['enum'])==set(catalog['codes']); invalid=json.loads((root/'examples/error-envelope.unknown-code.invalid.json').read_text()); errors=list(V(schema).iter_errors(invalid)); assert errors and any(list(e.path)==['error_code'] for e in errors)"`.
  Expected: exit `0`; envelope codes are neither missing from nor invented beyond
  the catalog, and an unknown externally visible code is rejected.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0`, a standalone `PASS`, unique prefixes, declared transition
  targets, valid terminal states and a structurally valid error catalog.
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
- new/changed contracts: schema-backed domain `1.0.0-draft.1` candidate only
- compatibility, known limits and unresolved owner decisions
- integration notes for analysis/jobs/findings/API consumers
- proof that no migration/runtime/legacy or other forbidden hotspot changed
