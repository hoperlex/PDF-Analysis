# Contract task W0-DOM-02 — remove the deprecated domain `version` mirror

> **Status: completed, independently accepted and integrated.**
> Integration commit: `478d32e90d1cbb2c691e0ac0b61b68dadcf0d397`.
> Domain candidate revision 5 remains unfrozen and unratified.

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

Full write, the substance of this task:

- `contracts/domain/v1/error-codes.json`
- `contracts/domain/v1/error-codes.schema.json`
- `contracts/domain/v1/README.md`

Single-value write, permitted **only** to advance `candidate_revision` and its `const`
pin, with every other byte unchanged:

- `contracts/domain/v1/identifiers.json`
- `contracts/domain/v1/identifiers.schema.json`
- `contracts/domain/v1/state-machines.json`
- `contracts/domain/v1/state-machines.schema.json`

The family holds `candidate_revision` as one value across all three catalogs, pinned
by `const` in all three schemas, so a round that advances it must touch six files. An
earlier draft of this task listed only the three full-write paths while also requiring
the advance — which made it unexecutable as written. Widening is deliberately
minimal: in the four single-value paths, a diff that changes anything other than that
one integer is a scope violation, and the gate below proves it.

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
- Command: `.venv/bootstrap/bin/python -c "import subprocess,re,json; base='a67ba31e7748c02974ae9ae93c7f30b6f141d417'; paths=['identifiers.json','identifiers.schema.json','state-machines.json','state-machines.schema.json']; bad=[]
def rev(d):
    if 'candidate_revision' in d: return d['candidate_revision']
    pr=d.get('properties')
    if isinstance(pr,dict) and isinstance(pr.get('candidate_revision'),dict): return pr['candidate_revision'].get('const')
    return None
for p in paths:
    rel='contracts/domain/v1/'+p
    out=subprocess.run(['git','diff','-U0',base,'--',rel],capture_output=True,text=True).stdout
    ch=[l for l in out.splitlines() if re.match(r'^[+-][^+-]',l)]
    if len(ch)!=2: bad.append((p,f'{len(ch)} changed lines, expected exactly 2')); continue
    o=[l for l in ch if l[0]=='-'][0][1:]; n=[l for l in ch if l[0]=='+'][0][1:]
    if re.sub(r'\d+','N',o)!=re.sub(r'\d+','N',n): bad.append((p,'changed line is not a numeric-only change')); continue
    old=json.loads(subprocess.run(['git','show',f'{base}:{rel}'],capture_output=True,text=True,check=True).stdout)
    new=json.loads(open(rel).read())
    if rev(new) is None or rev(new)==rev(old): bad.append((p,'revision not advanced'))
assert not bad, bad
print('single-value paths: exactly one changed line each, numeric only, revision advanced')"`.
  Expected: exit `0`. In each of the four single-value paths the diff against the
  commit this task started from consists of exactly one removed and one added line,
  those two lines are identical once every run of digits is normalised, and the
  revision value actually advanced.

  This is a byte-level check, matching the byte-level promise in Allowed paths. An
  earlier form compared parsed JSON, which would have accepted a reformat, a key
  reorder or a whitespace change while the task text promised bytes. It also read the
  revision from the document root only, so the two `*.schema.json` files — which hold
  it at `properties.candidate_revision.const` and have no root key — were reported as
  never advanced and the gate could not pass at all. Both defects are corrected here.
  Verified before being written down, in all three directions: a correct
  revision-only change passes; a foreign edit in one of these paths is rejected with
  `6 changed lines, expected exactly 2`; a revision rolled back in a schema pin is
  rejected with `revision not advanced`.
- Independent reviewer confirms the diff across all seven paths. In the three
  full-write paths it touches only the `version` key, its schema entry, the
  `deprecated_fields` block and the README prose, and the 20 error codes with their
  categories, statuses and `retryable` flags are byte-identical. In the four
  single-value paths it is one line each, the `candidate_revision` integer or its
  schema `const` pin, and nothing else.

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
be skippable. Before freeze, revert all seven declared paths **as one unit** — the
three full-write paths and the four single-value paths together. A partial revert is
not a rollback: restoring the catalog while leaving `candidate_revision` at the
advanced value, or the reverse, leaves the family declaring one revision in some files
and another in the rest, which is precisely the split the single value exists to
prevent. Reverting restores the mirror and is safe only while `W0-QA-03` keeps the key
optional. After freeze, stop consumers and follow the freeze-break procedure.

## Handoff

- changed files split by write mode: the three full-write paths, where only the
  `version` key, its schema entry, the `deprecated_fields` block and the README prose
  moved; and the four single-value paths, where the only change is `candidate_revision`
  in a catalog or its `const` pin in a schema, with the old and new values stated
- commands/results, including the schema-rejects-reintroduction probe
- new/changed contracts: domain error catalog only; `contract_version` value unchanged
- known limits: `U-04` remains open and unaffected by this task
- integration notes for `W0-EVT-01`, whose sweep this unblocks
- proof that no other contract family, validator, test, migration, runtime, legacy or
  forbidden hotspot changed
