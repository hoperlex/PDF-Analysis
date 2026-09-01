# Contract task W0-DOM-02 — remove the deprecated domain `version` mirror

> **Status: ready for W0.3 assignment.**
> `W0-QA-03` is independently accepted and integrated at
> `23dddf99f833d12cd4cc22d11e224d4b278872bf`. The stage-one convergence commit is
> pinned below; no dependency placeholder remains.

## Outcome

Delete the deprecated bare `version` key and its `deprecated_fields` block from
`contracts/domain/v1/error-codes.json`, so the domain family declares its envelope
version once, under the canonical `contract_version` key, and owner decision `ID-01`
is actually finished rather than merely declared.

## Problem

`ID-01` fixed `contract_version` as the canonical machine-contract version key and
directed that bare `version` and `schema_version` be removed before freeze.

`W0-DOM-01` could not comply. `_validate_error_catalog` in
`scripts/validate_bootstrap.py` hard-requires `("contract", "version")` on
`contracts/domain/v1/error-codes.json`, the validator is frozen by `W0-QA-02`, and
`scripts/**` is outside the DOM lane's allowed paths — so removing the key would fail
a gate that lane was required to pass. The lane therefore kept `version` as a declared
deprecated compatibility mirror, pinned by the same `const` as `contract_version` so
the two cannot diverge, and recorded the removal gate.

`W0-QA-03` moves the validator to `contract_version`. This task is the contract-side
half that `W0-QA-03` unblocks, and it is deliberately separate: the validator and the
contract are different hotspots with different owners.

## Ownership

- provider/contract owner: the domain contract owner; single owner of
  `contracts/domain/v1/**` for the duration of this task
- frozen-boundary governor: primary agent `/root`
- independent reviewer: assigned by the integrator; must not author the reviewed
  contract
- product/domain approval authority: not required; `ID-01` is already recorded

## Depends on

- `W0-QA-03`, integrated at
  `23dddf99f833d12cd4cc22d11e224d4b278872bf`. Removing the key before
  the validator stops requiring it makes `scripts/validate_bootstrap.py` fail, which
  is a required gate of this very task.
- `W0-DOM-01`, integrated at
  `cf7740474b1786163f54d93b013a0d526ef989e0`, which introduces the mirror and the
  `deprecated_fields` block this task removes.

## Frozen inputs

- base commit: `a67ba31e7748c02974ae9ae93c7f30b6f141d417`, the stage-one convergence
  containing accepted `W0-QA-03` and `W0-ARC-02`
- domain contract candidate from `W0-DOM-01`, including its `deprecated_fields` block,
  its `const` pin tying `version` to `contract_version`, and its recorded removal gate
- owner decision `ID-01` as committed by the `W0-ARC-01` integration
- validator behavior as changed by `W0-QA-03`: reads `contract_version`, neither
  requires nor forbids the bare key
- migration head: none

## Allowed paths

- `contracts/domain/v1/error-codes.json`
- `contracts/domain/v1/error-codes.schema.json`
- `contracts/domain/v1/README.md`

No other path is writable. `scripts/**` in particular is not: the validator change
belongs to `W0-QA-03` and must already be integrated.

## Forbidden hotspots

- every other `contracts/**` file, including the rest of the domain family
- `scripts/validate_bootstrap.py` and `tests/**`
- fixtures, architecture and program documents
- root dependency/lock files, migrations, composition root, global styles
- every legacy repository file, ref and worktree entry

## Non-goals

- No change to any error code, category, HTTP status, `retryable` flag, envelope
  field or forbidden-detail-key list. This task removes one deprecated key and its
  supporting block, nothing else.
- No change to `contract_version` or its value. `candidate_revision` **is** advanced —
  see Compatibility below; a remediation round that leaves the revision untouched
  becomes indistinguishable from the round before it.
- No re-introduction of a compatibility alias, shim or coercion for the removed key.
- No contract freeze by the task author; freeze remains the integrator's slot.

## Deliverables

- `error-codes.json`: the bare `version` key and the `deprecated_fields` block that
  described it are gone. `contract` and `contract_version` remain, unchanged in value.
- `error-codes.schema.json`: both `version` and `deprecated_fields` are removed from
  the root `required` array and from root `properties`. This removes the `version`
  property's deprecated marker and `const` pin as well as the schema for the
  compatibility block. With root `additionalProperties: false` retained, the schema
  **forbids both removed keys**, so either one fails closed if reintroduced.
- `README.md`: the removal is recorded, `ID-01` is marked complete for the domain
  family, and the note explaining the transitional mirror is replaced rather than left
  describing a field that no longer exists.

## Compatibility

- backward compatible: no; a consumer reading `version` from this catalog must read
  `contract_version`
- version bump: none required — `contract_version` and its value do not change, and
  the mirror was declared deprecated with this removal as its stated gate. Advance
  `candidate_revision` so the review round is still distinguishable.
- safe before frozen consumers exist; after freeze this requires the formal
  freeze-break and version procedure

## Required tests

- Command: `.venv/bootstrap/bin/python -c "import json; from pathlib import Path; d=json.loads(Path('contracts/domain/v1/error-codes.json').read_text()); assert 'version' not in d and 'deprecated_fields' not in d; assert d['contract_version'] and isinstance(d['contract_version'],str)"`.
  Expected: exit `0`; the mirror and its supporting block are gone and the canonical
  key remains a non-empty string.
- Command: `.venv/bootstrap/bin/python -c "import copy,json; from pathlib import Path; from jsonschema import Draft202012Validator as V; root=Path('contracts/domain/v1'); s=json.loads((root/'error-codes.schema.json').read_text()); removed={'version','deprecated_fields'}; assert not removed & set(s['required']); assert not removed & set(s['properties']); V.check_schema(s); d=json.loads((root/'error-codes.json').read_text()); V(s).validate(d); probes={'version':'1.0.0-draft.1','deprecated_fields':{}}; assert all(list(V(s).iter_errors(dict(d,**{k:v}))) for k,v in probes.items())"`.
  Expected: exit `0`; both removed names are absent from the schema's `required` and
  `properties`, the catalog validates, and reintroducing either key is rejected.
- Command: `.venv/bootstrap/bin/python -c "import json,glob; bad=[p for p in glob.glob('contracts/domain/v1/*.json') for d in [json.load(open(p))] if isinstance(d,dict) and 'version' in d]; assert not bad, bad"`.
  Expected: exit `0`; no domain catalog declares a bare `version` key.
- Command: `.venv/bootstrap/bin/python -c "import json; from pathlib import Path; from jsonschema import Draft202012Validator as V; root=Path('contracts/domain/v1'); c=json.loads((root/'error-codes.json').read_text()); s=json.loads((root/'error-envelope.schema.json').read_text()); assert set(s['properties']['error_code']['enum'])==set(c['codes'])"`.
  Expected: exit `0`; the envelope enum still equals the catalog keys, proving no code
  was disturbed.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0` with a standalone `PASS`, now against a catalog with no bare
  `version` key.
- Command: `git diff --check -- contracts/domain/v1`.
  Expected: exit `0` and no output.
- Independent reviewer confirms the diff touches only the version key, its schema
  entry, the `deprecated_fields` block and the README paragraph — and that the 20
  error codes, their categories, statuses and `retryable` flags are byte-identical.

## Integration contract

After acceptance, consumers read the domain error-catalog version from
`contract_version` only. A catalog carrying `version` is invalid, not tolerated. This
completes `ID-01` for the domain family and unblocks the repository-wide sweep in
`W0-EVT-01`.

## Failure/idempotency/security cases

- A reintroduced `version` key fails closed at the schema, not silently.
- Re-running the task is a no-op once the key is absent; it cannot remove a second
  field or alter a code.
- No credential, payload or path content is added to the catalog or the README.
- The catalog remains free of any tenant, IdP, TTL, retention or legal-hold value:
  `U-04` is still open.

## Rollback / feature flag

Contract-only change; no bypass feature flag, because a contract-version gate must not
be skippable. Before freeze, revert this task's three paths — which restores the
mirror and is safe only while `W0-QA-03` keeps the key optional. After freeze, stop
consumers and follow the freeze-break procedure.

## Handoff

- changed files and confirmation that only the version key, its schema entry, the
  `deprecated_fields` block and the README paragraph moved
- commands/results, including the schema-rejects-reintroduction probe
- new/changed contracts: domain error catalog only; `contract_version` value unchanged
- known limits: `U-04` remains open and unaffected by this task
- integration notes for `W0-EVT-01`, whose sweep this unblocks
- proof that no other contract family, validator, test, migration, runtime, legacy or
  forbidden hotspot changed
